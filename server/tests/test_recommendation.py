import sqlite3

from app.recommendation import build_recommendations


def setup_db():
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE media (id TEXT PRIMARY KEY, title TEXT, creator TEXT, genres TEXT, rating REAL, media_type TEXT, source TEXT, tracker_source TEXT);
        CREATE TABLE user_library (user_id INTEGER, media_id TEXT, status TEXT, progress INTEGER, user_rating REAL, PRIMARY KEY(user_id, media_id));
        CREATE TABLE recommendation_feedback (id INTEGER PRIMARY KEY, user_id INTEGER, media_id TEXT, feedback TEXT, created_at TEXT);
        """
    )
    conn.executemany(
        "INSERT INTO media (id, title, creator, genres, rating, media_type, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("saga", "Saga", "Brian K. Vaughan", "science-fiction,space-opera", 4.8, "comic", "comicvine"),
            ("a", "A", "Brian K. Vaughan", "science-fiction", 4.1, "comic", "comicvine"),
            ("b", "B", "Other", "romance", 4.9, "manga", "anilist"),
            ("c", "C", "Other", "science-fiction", 4.0, "comic", "comicvine"),
        ],
    )
    conn.execute("INSERT INTO user_library (user_id, media_id, status, progress, user_rating) VALUES (1, 'saga', 'completed', 100, 5)")
    conn.commit()
    return conn


def test_recommendations_exclude_already_read_and_explain():
    conn = setup_db()
    recs = build_recommendations(conn, 1, 10)
    ids = [r.media_id for r in recs]
    assert "saga" not in ids
    assert "a" in ids
    assert any("Because you liked Saga" in r.reason for r in recs)


def test_recommendations_exclude_duplicate_library_titles_across_ids():
    conn = setup_db()
    conn.execute(
        "INSERT INTO media (id, title, creator, genres, rating) VALUES ('duplicate', '  saga  ', 'Other', 'science-fiction', 5.0)"
    )
    conn.commit()

    recs = build_recommendations(conn, 1, 10)

    assert "duplicate" not in [recommendation.media_id for recommendation in recs]


def test_recommendations_exclude_punctuation_variants_of_library_titles():
    conn = setup_db()
    conn.execute(
        "INSERT INTO media (id, title, creator, genres, rating) VALUES ('punctuated', 'Saga!', 'Other', 'science-fiction', 5.0)"
    )
    conn.commit()

    recs = build_recommendations(conn, 1, 10)

    assert "punctuated" not in [recommendation.media_id for recommendation in recs]


def test_recommendations_preserve_non_latin_library_title_identity():
    conn = setup_db()
    conn.execute(
        "INSERT INTO media (id, title, creator, genres, rating) VALUES ('nonlatin', '進撃の巨人', 'Other', 'science-fiction', 5.0)"
    )
    conn.execute(
        "INSERT INTO user_library (user_id, media_id, status, progress, user_rating) VALUES (1, 'nonlatin', 'completed', 100, 5.0)"
    )
    conn.execute(
        "INSERT INTO media (id, title, creator, genres, rating) VALUES ('nonlatin-duplicate', '進撃の巨人', 'Other', 'science-fiction', 5.0)"
    )
    conn.commit()

    recs = build_recommendations(conn, 1, 10)

    assert "nonlatin-duplicate" not in [recommendation.media_id for recommendation in recs]


def test_recommendations_respect_dismiss_feedback():
    conn = setup_db()
    conn.execute("INSERT INTO recommendation_feedback (user_id, media_id, feedback, created_at) VALUES (1, 'a', 'dismiss', 'x')")
    conn.commit()
    recs = build_recommendations(conn, 1, 10)
    assert all(r.media_id != "a" for r in recs)


def test_completed_unrated_items_seed_recommendations_and_normalize_genres():
    conn = setup_db()
    conn.execute("UPDATE user_library SET user_rating = NULL WHERE media_id = 'saga'")
    conn.execute("UPDATE media SET genres = 'Science-Fiction' WHERE id = 'a'")
    conn.commit()

    recs = build_recommendations(conn, 1, 10)

    assert "a" in [recommendation.media_id for recommendation in recs]


def test_planned_items_remain_eligible_but_progressed_items_do_not():
    conn = setup_db()
    conn.execute(
        "INSERT INTO media (id, title, creator, genres, rating) VALUES ('planned', 'Planned', 'Other', 'science-fiction', 5.0)"
    )
    conn.execute(
        "INSERT INTO user_library (user_id, media_id, status, progress, user_rating) VALUES (1, 'planned', 'planned', 0, NULL)"
    )
    conn.execute(
        "INSERT INTO media (id, title, creator, genres, rating) VALUES ('progressed', 'Progressed', 'Other', 'science-fiction', 5.0)"
    )
    conn.execute(
        "INSERT INTO user_library (user_id, media_id, status, progress, user_rating) VALUES (1, 'progressed', 'reading', 1, NULL)"
    )
    conn.commit()

    ids = [recommendation.media_id for recommendation in build_recommendations(conn, 1, 10)]

    assert "planned" in ids
    assert "progressed" not in ids


def test_late_dropped_items_create_a_negative_genre_signal():
    conn = setup_db()
    conn.execute(
        "INSERT INTO media (id, title, creator, genres, rating) VALUES ('d', 'D', 'Other', 'science-fiction', 5.0)"
    )
    conn.execute(
        "INSERT INTO user_library (user_id, media_id, status, progress, user_rating) VALUES (1, 'd', 'dropped', 80, NULL)"
    )
    conn.commit()

    recs = build_recommendations(conn, 1, 10)

    assert "d" not in [recommendation.media_id for recommendation in recs]
    assert "c" not in [recommendation.media_id for recommendation in recs]


def test_liked_feedback_boosts_matching_items():
    conn = setup_db()
    conn.execute("UPDATE media SET genres = 'romance' WHERE id = 'b'")
    conn.execute("UPDATE media SET genres = 'romance' WHERE id = 'c'")
    conn.execute(
        "INSERT INTO recommendation_feedback (user_id, media_id, feedback, created_at) VALUES (1, 'b', 'like', 'x')"
    )
    conn.commit()

    recs = build_recommendations(conn, 1, 10)

    assert recs[0].media_id == "b"


def test_recommendations_can_filter_candidates_by_media_type():
    conn = setup_db()

    recs = build_recommendations(conn, 1, 10, media_type="manga")

    assert [recommendation.media_id for recommendation in recs] == ["b"]
