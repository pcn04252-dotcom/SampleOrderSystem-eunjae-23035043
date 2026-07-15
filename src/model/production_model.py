import datetime as dt
import math
import sqlite3

from src.model import order_status, sample_model
from src.model.clock import Clock


def enqueue(
    conn: sqlite3.Connection,
    clock: Clock,
    order_id: str,
    sample_id: str,
    shortfall_quantity: int,
) -> None:
    sample = sample_model.get_sample(conn, sample_id)
    actual_production_quantity = math.ceil(shortfall_quantity / sample["yield_rate"])
    total_production_time = sample["avg_production_time"] * actual_production_quantity
    conn.execute(
        "INSERT INTO production_queue"
        " (order_id, sample_id, shortfall_quantity, actual_production_quantity,"
        "  total_production_time, status, queued_at, expected_completion_at)"
        " VALUES (?, ?, ?, ?, ?, 'WAITING', ?, NULL)",
        (
            order_id,
            sample_id,
            shortfall_quantity,
            actual_production_quantity,
            total_production_time,
            clock.now().isoformat(),
        ),
    )
    conn.commit()
    _start_next_if_idle(conn, clock)


def _start_next_if_idle(conn: sqlite3.Connection, clock: Clock) -> None:
    """생산 라인은 단일 라인이므로 RUNNING 작업이 없을 때만 다음 WAITING 작업(FIFO)을 시작한다."""
    running = conn.execute(
        "SELECT id FROM production_queue WHERE status = 'RUNNING'"
    ).fetchone()
    if running is not None:
        return
    next_job = conn.execute(
        "SELECT * FROM production_queue WHERE status = 'WAITING' ORDER BY id LIMIT 1"
    ).fetchone()
    if next_job is None:
        return
    expected_completion = clock.now() + dt.timedelta(
        minutes=next_job["total_production_time"]
    )
    conn.execute(
        "UPDATE production_queue SET status = 'RUNNING', expected_completion_at = ?"
        " WHERE id = ?",
        (expected_completion.isoformat(), next_job["id"]),
    )
    conn.commit()


def sync_queue(conn: sqlite3.Connection, clock: Clock) -> None:
    """RUNNING 작업의 완료 예정 시각이 지났으면 완료 처리 후 다음 대기 작업을 시작한다.

    메뉴 조회 시점마다 호출되는 lazy 방식 (백그라운드 스레드/타이머 없음).
    """
    running = conn.execute(
        "SELECT * FROM production_queue WHERE status = 'RUNNING'"
    ).fetchone()
    if running is not None:
        completion = dt.datetime.fromisoformat(running["expected_completion_at"])
        if clock.now() >= completion:
            _complete_job(conn, clock, running)
    _start_next_if_idle(conn, clock)


def _complete_job(conn: sqlite3.Connection, clock: Clock, job: sqlite3.Row) -> None:
    # 생산분을 재고에 더한 뒤, 이 주문이 필요로 했던 부족분만큼 다시 차감한다.
    # 남는 차액(실생산량 - 부족분)은 수율 보정으로 인한 잉여 재고로 남는다.
    sample_model.adjust_stock(conn, job["sample_id"], job["actual_production_quantity"])
    sample_model.adjust_stock(conn, job["sample_id"], -job["shortfall_quantity"])
    conn.execute("UPDATE production_queue SET status = 'DONE' WHERE id = ?", (job["id"],))
    order_status.set_status(conn, clock, job["order_id"], "CONFIRMED")
    conn.commit()


def get_running_job(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM production_queue WHERE status = 'RUNNING'"
    ).fetchone()


def list_waiting_jobs(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM production_queue WHERE status = 'WAITING' ORDER BY id"
    ).fetchall()


def count_waiting(conn: sqlite3.Connection) -> int:
    running = 1 if get_running_job(conn) else 0
    waiting = conn.execute(
        "SELECT COUNT(*) FROM production_queue WHERE status = 'WAITING'"
    ).fetchone()[0]
    return running + waiting


def progress_percent(job: sqlite3.Row, clock: Clock) -> float:
    if job["expected_completion_at"] is None:
        return 0.0
    completion = dt.datetime.fromisoformat(job["expected_completion_at"])
    start = completion - dt.timedelta(minutes=job["total_production_time"])
    total_seconds = (completion - start).total_seconds()
    if total_seconds <= 0:
        return 100.0
    elapsed = (clock.now() - start).total_seconds()
    return max(0.0, min(100.0, elapsed / total_seconds * 100))
