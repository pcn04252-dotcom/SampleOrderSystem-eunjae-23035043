import sqlite3

from src.model.clock import Clock


def set_status(conn: sqlite3.Connection, clock: Clock, order_id: str, status: str) -> None:
    conn.execute(
        "UPDATE orders SET status = ?, updated_at = ? WHERE order_id = ?",
        (status, clock.now().isoformat(), order_id),
    )
