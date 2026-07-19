"""SQLite connection management and idempotent schema initialization.

The schema in ``schema.sql`` is applied on every connect via ``executescript``, which
is safe because it uses ``CREATE TABLE IF NOT EXISTS`` / ``CREATE INDEX IF NOT EXISTS``.
WAL mode and foreign-key enforcement are enabled per connection.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from .config import get_settings

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.sql"


def _load_schema() -> str:
    return SCHEMA_PATH.read_text(encoding="utf-8")


def connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Open a connection, ensure the parent directory exists, and apply the schema."""
    if db_path is None:
        db_path = get_settings().db_path

    if db_path != ":memory:":
        parent = Path(db_path).parent
        if str(parent) not in ("", "."):
            parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    # Enforce foreign keys for this connection (schema.sql re-asserts these too).
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(_load_schema())
    return conn


@contextmanager
def get_connection(db_path: Optional[str] = None) -> Iterator[sqlite3.Connection]:
    """Context-managed connection: commits on success, rolls back on error, always
    closes."""
    conn = connect(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
