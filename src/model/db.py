import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "app.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS samples (
    sample_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    avg_production_time REAL NOT NULL,
    yield_rate REAL NOT NULL,
    current_stock INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    sample_id TEXT NOT NULL REFERENCES samples(sample_id),
    customer_name TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    status TEXT NOT NULL
        CHECK (status IN ('RESERVED','REJECTED','PRODUCING','CONFIRMED','RELEASE')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    released_at TEXT
);

CREATE TABLE IF NOT EXISTS production_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL REFERENCES orders(order_id),
    sample_id TEXT NOT NULL REFERENCES samples(sample_id),
    shortfall_quantity INTEGER NOT NULL,
    actual_production_quantity INTEGER NOT NULL,
    total_production_time REAL NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('WAITING','RUNNING','DONE')),
    queued_at TEXT NOT NULL,
    expected_completion_at TEXT
);
"""


@contextmanager
def get_connection(db_path=DB_PATH):
    if str(db_path) != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(_SCHEMA)
        conn.commit()
        yield conn
    finally:
        conn.close()
