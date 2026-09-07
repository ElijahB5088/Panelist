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
    migrations_dir = Path(__file__).resolve().parents[1] / "migrations"
    conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)")
    applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
    for migration in sorted(migrations_dir.glob("*.sql")):
        version = int(migration.stem.split("_", 1)[0])
        if version in applied:
            continue
        conn.executescript(migration.read_text())
        conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
    conn.commit()
