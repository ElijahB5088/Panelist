import sqlite3

from app.recommendation_evaluation import (
    catalog_coverage,
    concentration,
    evaluate_user,
    precision_at_k,
    recall_at_k,
)


def test_ranking_metrics_are_bounded_and_deterministic():
    recommendations = ["a", "b", "c"]
    relevant = {"a", "c"}

    assert precision_at_k(recommendations, relevant, 2) == 0.5
    assert recall_at_k(recommendations, relevant, 2) == 0.5
    assert catalog_coverage([recommendations, ["c", "d"]], 4) == 1.0
    assert concentration(recommendations, lambda item: "creator-a" if item != "c" else "creator-b") == 2 / 3


def test_evaluate_user_reports_personalized_rank_metrics():
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE media (
            id TEXT PRIMARY KEY, title TEXT, creator TEXT, genres TEXT,
            rating REAL, media_type TEXT, source TEXT
        );
        CREATE TABLE user_library (
            user_id INTEGER, media_id TEXT, status TEXT, progress INTEGER,
            user_rating REAL, PRIMARY KEY(user_id, media_id)
        );
        CREATE TABLE recommendation_feedback (
            id INTEGER PRIMARY KEY, user_id INTEGER, media_id TEXT,
            feedback TEXT, created_at TEXT
        );
        """
    )
    conn.executemany(
        "INSERT INTO media VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("seed", "Seed", "Creator", "fantasy", 5.0, "comic", "test"),
            ("relevant", "Relevant", "Creator", "fantasy", 4.0, "comic", "test"),
            ("other", "Other", "Different", "romance", 5.0, "comic", "test"),
        ],
    )
    conn.execute(
        "INSERT INTO user_library VALUES (1, 'seed', 'completed', 100, 5.0)"
    )
    conn.commit()

    metrics = evaluate_user(conn, 1, {"relevant"}, k=1)

    assert metrics["k"] == 1
    assert metrics["recommended"] == 1
    assert metrics["precision_at_k"] == 1.0
    assert metrics["recall_at_k"] == 1.0
