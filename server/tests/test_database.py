from app import db
from app.config import settings


def test_fresh_database_applies_all_migrations_with_sqlite_hardening(tmp_path):
    previous_url = settings.database_url
    settings.database_url = f"sqlite:///{tmp_path / 'fresh.db'}"
    try:
        connection = db.get_conn()
        db.run_migrations(connection)

        latest = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
        foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        audit_table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_events'"
        ).fetchone()[0]

        assert latest == 7
        assert foreign_keys == 1
        assert journal_mode.lower() == "wal"
        assert audit_table == "audit_events"
    finally:
        connection.close()
        settings.database_url = previous_url
