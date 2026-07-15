import sqlite3


def create_sample(
    conn: sqlite3.Connection,
    sample_id: str,
    name: str,
    avg_production_time: float,
    yield_rate: float,
    initial_stock: int = 0,
) -> None:
    if avg_production_time <= 0:
        raise ValueError("평균 생산시간은 0보다 커야 합니다.")
    if not (0 < yield_rate <= 1):
        raise ValueError("수율은 0 초과 1 이하이어야 합니다.")
    conn.execute(
        "INSERT INTO samples"
        " (sample_id, name, avg_production_time, yield_rate, current_stock)"
        " VALUES (?, ?, ?, ?, ?)",
        (sample_id, name, avg_production_time, yield_rate, initial_stock),
    )
    conn.commit()


def get_sample(conn: sqlite3.Connection, sample_id: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM samples WHERE sample_id = ?", (sample_id,)
    ).fetchone()


def list_samples(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM samples ORDER BY sample_id").fetchall()


def search_samples(conn: sqlite3.Connection, keyword: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM samples WHERE name LIKE ? ORDER BY sample_id",
        (f"%{keyword}%",),
    ).fetchall()


def adjust_stock(conn: sqlite3.Connection, sample_id: str, delta: int) -> None:
    conn.execute(
        "UPDATE samples SET current_stock = current_stock + ? WHERE sample_id = ?",
        (delta, sample_id),
    )
    conn.commit()


def classify_stock_status(conn: sqlite3.Connection, sample_id: str) -> str:
    """PRD 3.5절 재고 상태 분류: 고갈(0) / 부족(미체결 수요 미달) / 여유(그 외).

    "주문대비"는 현재 RESERVED/PRODUCING 상태인(아직 출고되지 않은) 주문의
    수량 합계 대비 현재 재고로 정의한다.
    """
    sample = get_sample(conn, sample_id)
    if sample["current_stock"] == 0:
        return "고갈"
    pending_demand = conn.execute(
        "SELECT COALESCE(SUM(quantity), 0) FROM orders"
        " WHERE sample_id = ? AND status IN ('RESERVED', 'PRODUCING')",
        (sample_id,),
    ).fetchone()[0]
    if sample["current_stock"] < pending_demand:
        return "부족"
    return "여유"
