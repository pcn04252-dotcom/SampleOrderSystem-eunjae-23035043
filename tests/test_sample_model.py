import pytest

from src.model import sample_model
from src.model.db import get_connection


def test_create_and_get_sample():
    with get_connection(":memory:") as conn:
        sample_model.create_sample(conn, "S-001", "실리콘 웨이퍼", 0.5, 0.9, initial_stock=100)
        sample = sample_model.get_sample(conn, "S-001")
    assert sample["name"] == "실리콘 웨이퍼"
    assert sample["current_stock"] == 100


def test_create_sample_rejects_invalid_yield_rate():
    with get_connection(":memory:") as conn:
        with pytest.raises(ValueError):
            sample_model.create_sample(conn, "S-001", "불량", 0.5, 0)


def test_create_sample_rejects_non_positive_production_time():
    with get_connection(":memory:") as conn:
        with pytest.raises(ValueError):
            sample_model.create_sample(conn, "S-001", "불량", 0, 0.9)


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
