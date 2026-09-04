from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import settings


def _sqlite_path() -> str:
    prefix = "sqlite:///"
    if settings.database_url.startswith(prefix):
        return settings.database_url[len(prefix) :]
    return settings.database_url


def get_conn() -> sqlite3.Connection:
    db_path = _sqlite_path()
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def run_migrations(conn: sqlite3.Connection) -> None:
    migration = Path(__file__).resolve().parents[1] / "migrations" / "001_init.sql"
    conn.executescript(migration.read_text())
    conn.commit()
