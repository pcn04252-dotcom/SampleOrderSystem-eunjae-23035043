import pytest

from src.model import order_model, production_model, sample_model
from src.model.clock import FakeClock
from src.model.db import get_connection


def _seed(conn, stock, yield_rate=1.0):
    sample_model.create_sample(
        conn, "S-001", "품목", avg_production_time=1.0, yield_rate=yield_rate, initial_stock=stock
    )


def test_create_order_sets_reserved_status():
    with get_connection(":memory:") as conn:
        _seed(conn, stock=100)
        clock = FakeClock()
        order_id = order_model.create_order(conn, clock, "S-001", "고객A", 10)
        order = order_model.get_order(conn, order_id)
    assert order["status"] == "RESERVED"


def test_create_order_rejects_non_positive_quantity():
    with get_connection(":memory:") as conn:
        _seed(conn, stock=100)
        clock = FakeClock()
        with pytest.raises(ValueError):
            order_model.create_order(conn, clock, "S-001", "고객A", 0)


def test_approve_order_with_sufficient_stock_confirms_immediately():
    with get_connection(":memory:") as conn:
        _seed(conn, stock=100)
        clock = FakeClock()
        order_id = order_model.create_order(conn, clock, "S-001", "고객A", 30)
        status = order_model.approve_order(conn, clock, order_id)
    assert status == "CONFIRMED"


def test_approve_order_deducts_stock_when_sufficient():
    with get_connection(":memory:") as conn:
        _seed(conn, stock=100)
        clock = FakeClock()
        order_id = order_model.create_order(conn, clock, "S-001", "고객A", 30)
        order_model.approve_order(conn, clock, order_id)
        sample = sample_model.get_sample(conn, "S-001")
    assert sample["current_stock"] == 70


def test_approve_order_with_insufficient_stock_enqueues_production():
    with get_connection(":memory:") as conn:
        _seed(conn, stock=5)
        clock = FakeClock()
        order_id = order_model.create_order(conn, clock, "S-001", "고객A", 20)
        status = order_model.approve_order(conn, clock, order_id)
        job = production_model.get_running_job(conn)
    assert status == "PRODUCING"
    assert job["shortfall_quantity"] == 15
    assert job["actual_production_quantity"] == 15  # yield_rate=1.0


def test_shortfall_production_uses_ceil_of_yield_rate():
    with get_connection(":memory:") as conn:
        _seed(conn, stock=30, yield_rate=0.92)
        clock = FakeClock()
        order_id = order_model.create_order(conn, clock, "S-001", "고객A", 200)
        order_model.approve_order(conn, clock, order_id)
        job = production_model.get_running_job(conn)
    assert job["shortfall_quantity"] == 170
    assert job["actual_production_quantity"] == 185  # ceil(170 / 0.92) = 184.78... -> 185


def test_approve_order_twice_raises_value_error():
    with get_connection(":memory:") as conn:
        _seed(conn, stock=100)
        clock = FakeClock()
        order_id = order_model.create_order(conn, clock, "S-001", "고객A", 10)
        order_model.approve_order(conn, clock, order_id)
        with pytest.raises(ValueError):
            order_model.approve_order(conn, clock, order_id)


def test_reject_order_sets_rejected_status():
    with get_connection(":memory:") as conn:
        _seed(conn, stock=100)
        clock = FakeClock()
        order_id = order_model.create_order(conn, clock, "S-001", "고객A", 10)
        order_model.reject_order(conn, clock, order_id)
        order = order_model.get_order(conn, order_id)
    assert order["status"] == "REJECTED"


def test_release_order_requires_confirmed_status():
    with get_connection(":memory:") as conn:
        _seed(conn, stock=100)
        clock = FakeClock()
        order_id = order_model.create_order(conn, clock, "S-001", "고객A", 10)
        with pytest.raises(ValueError):
            order_model.release_order(conn, clock, order_id)


def test_release_order_sets_release_status():
    with get_connection(":memory:") as conn:
        _seed(conn, stock=100)
        clock = FakeClock()
        order_id = order_model.create_order(conn, clock, "S-001", "고객A", 10)
        order_model.approve_order(conn, clock, order_id)
        order_model.release_order(conn, clock, order_id)
        order = order_model.get_order(conn, order_id)
    assert order["status"] == "RELEASE"


def test_count_orders_by_status_excludes_rejected():
    with get_connection(":memory:") as conn:
        _seed(conn, stock=100)
        clock = FakeClock()
        order_model.create_order(conn, clock, "S-001", "고객A", 10)
        second_id = order_model.create_order(conn, clock, "S-001", "고객B", 10)
        order_model.reject_order(conn, clock, second_id)
        counts = order_model.count_orders_by_status(conn)
    assert counts["RESERVED"] == 1
    assert "REJECTED" not in counts
