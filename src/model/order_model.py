import sqlite3

from src.model import order_status, production_model, sample_model
from src.model.clock import Clock


def _generate_order_id(conn: sqlite3.Connection, clock: Clock) -> str:
    date_str = clock.now().strftime("%Y%m%d")
    count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    return f"ORD-{date_str}-{count + 1:04d}"


def create_order(
    conn: sqlite3.Connection,
    clock: Clock,
    sample_id: str,
    customer_name: str,
    quantity: int,
) -> str:
    if quantity < 1:
        raise ValueError("주문 수량은 1 이상이어야 합니다.")
    order_id = _generate_order_id(conn, clock)
    now = clock.now().isoformat()
    conn.execute(
        "INSERT INTO orders"
        " (order_id, sample_id, customer_name, quantity, status, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, 'RESERVED', ?, ?)",
        (order_id, sample_id, customer_name, quantity, now, now),
    )
    conn.commit()
    return order_id


def get_order(conn: sqlite3.Connection, order_id: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()


def list_orders(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM orders ORDER BY created_at").fetchall()


def list_orders_by_status(conn: sqlite3.Connection, status: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM orders WHERE status = ? ORDER BY created_at", (status,)
    ).fetchall()


def count_orders_by_status(conn: sqlite3.Connection) -> dict:
    # REJECTED는 PRD 3.5절에 따라 모니터링 대상에서 제외한다.
    statuses = ["RESERVED", "CONFIRMED", "PRODUCING", "RELEASE"]
    return {
        status: conn.execute(
            "SELECT COUNT(*) FROM orders WHERE status = ?", (status,)
        ).fetchone()[0]
        for status in statuses
    }


def reject_order(conn: sqlite3.Connection, clock: Clock, order_id: str) -> None:
    order = get_order(conn, order_id)
    if order is None:
        raise KeyError(f"존재하지 않는 주문입니다: {order_id}")
    if order["status"] != "RESERVED":
        raise ValueError("RESERVED 상태의 주문만 거절할 수 있습니다.")
    order_status.set_status(conn, clock, order_id, "REJECTED")
    conn.commit()


def approve_order(conn: sqlite3.Connection, clock: Clock, order_id: str) -> str:
    """주문을 승인한다. 재고 충분 여부에 따라 CONFIRMED 또는 PRODUCING으로 전환하고,
    최종 상태 문자열을 반환한다."""
    order = get_order(conn, order_id)
    if order is None:
        raise KeyError(f"존재하지 않는 주문입니다: {order_id}")
    if order["status"] != "RESERVED":
        raise ValueError("RESERVED 상태의 주문만 승인할 수 있습니다.")

    sample = sample_model.get_sample(conn, order["sample_id"])
    quantity = order["quantity"]
    current_stock = sample["current_stock"]

    if current_stock >= quantity:
        sample_model.adjust_stock(conn, order["sample_id"], -quantity)
        order_status.set_status(conn, clock, order_id, "CONFIRMED")
        conn.commit()
        return "CONFIRMED"

    shortfall = quantity - current_stock
    if current_stock > 0:
        sample_model.adjust_stock(conn, order["sample_id"], -current_stock)
    production_model.enqueue(conn, clock, order_id, order["sample_id"], shortfall)
    order_status.set_status(conn, clock, order_id, "PRODUCING")
    conn.commit()
    return "PRODUCING"


def release_order(conn: sqlite3.Connection, clock: Clock, order_id: str) -> None:
    order = get_order(conn, order_id)
    if order is None:
        raise KeyError(f"존재하지 않는 주문입니다: {order_id}")
    if order["status"] != "CONFIRMED":
        raise ValueError("CONFIRMED 상태의 주문만 출고할 수 있습니다.")
    now = clock.now().isoformat()
    conn.execute(
        "UPDATE orders SET status = 'RELEASE', updated_at = ?, released_at = ?"
        " WHERE order_id = ?",
        (now, now, order_id),
    )
    conn.commit()
