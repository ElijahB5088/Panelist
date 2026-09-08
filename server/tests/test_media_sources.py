import sqlite3
from pathlib import Path


def test_media_sources_migration_backfills_existing_source_links():
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE media (
          id TEXT PRIMARY KEY,
          source TEXT,
          source_id TEXT,
          source_url TEXT
        );
        """
    )
    conn.executemany(
        "INSERT INTO media (id, source, source_id, source_url) VALUES (?, ?, ?, ?)",
        [
            ("media-1", "mal", "42", "https://mal.example/42"),
            ("media-2", "mal", "42", "https://other.example/42"),
        ],
    )
    migration = Path(__file__).parents[1] / "migrations" / "008_media_sources.sql"
    conn.executescript(migration.read_text())

    assert conn.execute("SELECT media_id FROM media_sources WHERE source='mal' AND source_id='42'").fetchone()[0] == "media-1"
    assert conn.execute("SELECT COUNT(*) FROM media_source_conflicts").fetchone()[0] == 1


def test_media_sources_migration_enforces_one_canonical_media_per_external_identity():
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE media (id TEXT PRIMARY KEY);
        CREATE TABLE media_sources (
          media_id TEXT NOT NULL,
          source TEXT NOT NULL,
          source_id TEXT NOT NULL,
          source_url TEXT,
          PRIMARY KEY (source, source_id),
          FOREIGN KEY(media_id) REFERENCES media(id)
        );
        """
    )
    conn.execute("INSERT INTO media (id) VALUES ('media-1')")
    conn.execute("INSERT INTO media (id) VALUES ('media-2')")
    conn.execute(
        "INSERT INTO media_sources (media_id, source, source_id) VALUES (?, ?, ?)",
        ("media-1", "mal", "42"),
    )

    try:
        conn.execute(
            "INSERT INTO media_sources (media_id, source, source_id) VALUES (?, ?, ?)",
            ("media-2", "mal", "42"),
        )
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("duplicate external identities must be rejected")