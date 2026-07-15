from src.model import sample_model
from src.model.db import get_connection


def test_get_connection_creates_parent_directory_and_file(tmp_path):
    """:memory:가 아닌 실제 파일 경로를 사용할 때 상위 폴더/DB 파일이 정상 생성되는지 확인."""
    db_path = tmp_path / "nested" / "app.db"
    assert not db_path.parent.exists()

    with get_connection(db_path) as conn:
        sample_model.create_sample(conn, "S-001", "품목", 0.5, 0.9, initial_stock=10)

    assert db_path.exists()


def test_data_persists_across_separate_connections_to_same_file(tmp_path):
    """앱 재시작(=connection을 새로 여는 것) 후에도 데이터가 유지되는지 확인 (PRD 영속성 요건)."""
    db_path = tmp_path / "app.db"

    with get_connection(db_path) as conn:
        sample_model.create_sample(conn, "S-001", "품목", 0.5, 0.9, initial_stock=42)

    with get_connection(db_path) as conn:
        sample = sample_model.get_sample(conn, "S-001")

    assert sample["current_stock"] == 42
