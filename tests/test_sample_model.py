import sqlite3

import pytest

from src.model import order_model, sample_model
from src.model.clock import FakeClock
from src.model.db import get_connection


def test_create_and_get_sample():
    with get_connection(":memory:") as conn:
        sample_model.create_sample(conn, "S-001", "실리콘 웨이퍼", 0.5, 0.9, initial_stock=100)
        sample = sample_model.get_sample(conn, "S-001")
    assert sample["name"] == "실리콘 웨이퍼"
    assert sample["current_stock"] == 100


def test_create_sample_rejects_zero_yield_rate():
    with get_connection(":memory:") as conn:
        with pytest.raises(ValueError):
            sample_model.create_sample(conn, "S-001", "불량", 0.5, 0)


def test_create_sample_rejects_negative_yield_rate():
    """PRD 6장 항목4: 수율 음수 값 등록 방지."""
    with get_connection(":memory:") as conn:
        with pytest.raises(ValueError):
            sample_model.create_sample(conn, "S-001", "불량", 0.5, -0.1)


def test_create_sample_rejects_yield_rate_above_one():
    with get_connection(":memory:") as conn:
        with pytest.raises(ValueError):
            sample_model.create_sample(conn, "S-001", "불량", 0.5, 1.1)


def test_create_sample_rejects_non_positive_production_time():
    with get_connection(":memory:") as conn:
        with pytest.raises(ValueError):
            sample_model.create_sample(conn, "S-001", "불량", 0, 0.9)


def test_create_sample_duplicate_id_raises_integrity_error():
    """PRD 6장 항목2: 중복 시료 ID 등록 시 오류."""
    with get_connection(":memory:") as conn:
        sample_model.create_sample(conn, "S-001", "품목A", 0.5, 0.9)
        with pytest.raises(sqlite3.IntegrityError):
            sample_model.create_sample(conn, "S-001", "품목B", 0.3, 0.8)


def test_list_samples_returns_all_registered_samples():
    with get_connection(":memory:") as conn:
        sample_model.create_sample(conn, "S-001", "품목A", 0.5, 0.9)
        sample_model.create_sample(conn, "S-002", "품목B", 0.3, 0.8)
        samples = sample_model.list_samples(conn)
    assert [s["sample_id"] for s in samples] == ["S-001", "S-002"]


def test_search_samples_matches_partial_name():
    with get_connection(":memory:") as conn:
        sample_model.create_sample(conn, "S-001", "실리콘 웨이퍼-8인치", 0.5, 0.9)
        sample_model.create_sample(conn, "S-002", "GaN 에피택셜", 0.3, 0.8)
        results = sample_model.search_samples(conn, "웨이퍼")
    assert [r["sample_id"] for r in results] == ["S-001"]


def test_classify_stock_status_depletion():
    with get_connection(":memory:") as conn:
        sample_model.create_sample(conn, "S-001", "품목", 0.5, 0.9, initial_stock=0)
        status = sample_model.classify_stock_status(conn, "S-001")
    assert status == "고갈"


def test_classify_stock_status_sufficient_when_no_pending_orders():
    with get_connection(":memory:") as conn:
        sample_model.create_sample(conn, "S-001", "품목", 0.5, 0.9, initial_stock=50)
        status = sample_model.classify_stock_status(conn, "S-001")
    assert status == "여유"


def test_classify_stock_status_shortage_when_stock_below_pending_demand():
    """PRD §3.5: 재고는 0보다 크지만 미체결(RESERVED/PRODUCING) 주문 수요 합보다 적으면 '부족'."""
    with get_connection(":memory:") as conn:
        sample_model.create_sample(conn, "S-001", "품목", 0.5, 0.9, initial_stock=5)
        clock = FakeClock()
        order_model.create_order(conn, clock, "S-001", "고객A", 20)  # RESERVED, 수요 20 > 재고 5
        status = sample_model.classify_stock_status(conn, "S-001")
    assert status == "부족"
