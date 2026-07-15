import time

from src.model import order_model, production_model, sample_model
from src.model.clock import FakeClock, ScaledSystemClock
from src.model.db import get_connection


def _seed(conn, stock, avg_production_time=1.0, yield_rate=1.0):
    sample_model.create_sample(
        conn,
        "S-001",
        "테스트 시료",
        avg_production_time=avg_production_time,
        yield_rate=yield_rate,
        initial_stock=stock,
    )


def test_enqueue_and_fake_clock_completion_confirms_order():
    with get_connection(":memory:") as conn:
        _seed(conn, stock=0)
        clock = FakeClock()
        order_id = order_model.create_order(conn, clock, "S-001", "고객A", 10)
        order_model.approve_order(conn, clock, order_id)

        job = production_model.get_running_job(conn)
        assert job is not None

        clock.advance(minutes=job["total_production_time"])
        production_model.sync_queue(conn, clock)

        order = order_model.get_order(conn, order_id)
        sample = sample_model.get_sample(conn, "S-001")

    assert order["status"] == "CONFIRMED"
    assert sample["current_stock"] == 0  # 생산분(10) - 부족분(10) = 0


def test_completion_before_expected_time_does_not_confirm():
    with get_connection(":memory:") as conn:
        _seed(conn, stock=0)
        clock = FakeClock()
        order_id = order_model.create_order(conn, clock, "S-001", "고객A", 10)
        order_model.approve_order(conn, clock, order_id)

        clock.advance(seconds=1)  # 완료 예정 시각(1분 후)에 한참 못 미침
        production_model.sync_queue(conn, clock)
        order = order_model.get_order(conn, order_id)

    assert order["status"] == "PRODUCING"


def test_fifo_order_of_two_queued_jobs():
    with get_connection(":memory:") as conn:
        _seed(conn, stock=0)
        clock = FakeClock()
        order1 = order_model.create_order(conn, clock, "S-001", "고객A", 5)
        order2 = order_model.create_order(conn, clock, "S-001", "고객B", 5)
        order_model.approve_order(conn, clock, order1)
        order_model.approve_order(conn, clock, order2)

        running = production_model.get_running_job(conn)
        waiting = production_model.list_waiting_jobs(conn)
        assert running["order_id"] == order1
        assert [w["order_id"] for w in waiting] == [order2]

        clock.advance(minutes=running["total_production_time"])
        production_model.sync_queue(conn, clock)
        running_after = production_model.get_running_job(conn)

    assert running_after["order_id"] == order2


def test_scaled_system_clock_production_completes_in_real_time():
    """mocking 없이 실제 ScaledSystemClock으로 생산 완료 lazy 판정이 실제로 동작하는지 확인.

    total_production_time을 아주 작게(0.02분) 잡아 배율 1.0에서 실제 대기 시간이
    약 1.2초 정도로 짧게 끝나도록 구성했다.
    """
    with get_connection(":memory:") as conn:
        sample_model.create_sample(
            conn,
            "S-002",
            "빠른 테스트 시료",
            avg_production_time=0.02,
            yield_rate=1.0,
            initial_stock=0,
        )
        clock = ScaledSystemClock(scale_seconds_per_minute=1.0)
        order_id = order_model.create_order(conn, clock, "S-002", "고객A", 1)
        order_model.approve_order(conn, clock, order_id)

        job = production_model.get_running_job(conn)
        assert job is not None

        deadline = time.monotonic() + 5
        order = order_model.get_order(conn, order_id)
        while order["status"] != "CONFIRMED" and time.monotonic() < deadline:
            time.sleep(0.05)
            production_model.sync_queue(conn, clock)
            order = order_model.get_order(conn, order_id)

    assert order["status"] == "CONFIRMED", "제한 시간 내에 생산이 실제로 완료되지 않았습니다."
