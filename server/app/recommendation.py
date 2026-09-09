from __future__ import annotations

import math
import sqlite3

from .metadata_mapping import normalize_identity, normalize_media_type
from .models import RecommendationResult


def _split_csv(text: str | None) -> list[str]:
    if not text:
        return []
    return [_normalize(p) for p in text.split(",") if p.strip()]


def _normalize(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def _add_affinity(target: dict[str, float], key: str, weight: float) -> None:
    if not key:
        return
    target[key] = min(target.get(key, 0.0) + weight, 6.0)


def _normalize_title(value: str | None) -> str:
    return normalize_identity(value)


def library_title_keys(conn: sqlite3.Connection, user_id: int) -> set[str]:
    return {
        _normalize_title(row[0])
        for row in conn.execute(
            """
            SELECT m.title
            FROM user_library ul
            JOIN media m ON m.id = ul.media_id
            WHERE ul.user_id = ?
              AND (ul.status = 'completed' OR COALESCE(ul.progress, 0) > 0)
            """,
            (user_id,),
        ).fetchall()
    }


def _media_type(value: str | None, source: str | None = None, tracker_source: str | None = None) -> str | None:
    return normalize_media_type(value, source=source, tracker_source=tracker_source) or None


def build_recommendations(
    conn: sqlite3.Connection,
    user_id: int,
    limit: int = 20,
    media_type: str | None = None,
) -> list[RecommendationResult]:
    library = conn.execute(
        """
        SELECT m.title, m.creator, m.genres, ul.status, ul.progress, ul.user_rating
        FROM user_library ul
        JOIN media m ON m.id = ul.media_id
        WHERE ul.user_id = ?
        """,
        (user_id,),
    ).fetchall()

    already = {
        row[0]
        for row in conn.execute(
            """
            SELECT media_id
            FROM user_library
            WHERE user_id = ?
              AND (status = 'completed' OR COALESCE(progress, 0) > 0)
            """,
            (user_id,),
        ).fetchall()
    }
    already_titles = library_title_keys(conn, user_id)

    dismissed = {
        row[0]
        for row in conn.execute(
            "SELECT media_id FROM recommendation_feedback WHERE user_id = ? AND feedback = 'dismiss'",
            (user_id,),
        ).fetchall()
    }

    positive_genres: dict[str, float] = {}
    positive_creators: dict[str, float] = {}
    avoid_genres: dict[str, float] = {}
    avoid_creators: dict[str, float] = {}
    positive_genre_sources: dict[str, tuple[float, str, str]] = {}
    positive_creator_sources: dict[str, tuple[float, str, str]] = {}

    for title, creator, genres, status, progress, user_rating in library:
        rating = float(user_rating) if user_rating is not None else None
        if status == "dropped":
            weight = -3.0 if (progress or 0) >= 70 else -0.75
        elif rating is not None:
            weight = rating - 3.0
        elif status == "completed":
            weight = 1.5
        elif status == "plan-to-read":
            weight = 0.5
        elif status == "reading":
            weight = 0.35
        else:
            weight = 0.0

        if weight > 0:
            target_genres = positive_genres
            target_creators = positive_creators
        elif weight < 0:
            target_genres = avoid_genres
            target_creators = avoid_creators
        else:
            continue

        creator_key = _normalize(creator)
        _add_affinity(target_creators, creator_key, abs(weight))
        if weight > 0 and creator_key:
            source = positive_creator_sources.get(creator_key)
            if source is None or weight > source[0]:
                if user_rating is not None:
                    evidence = "you liked"
                elif status == "completed":
                    evidence = "you finished"
                elif status == "plan-to-read":
                    evidence = "you planned"
                else:
                    evidence = "you are reading"
                positive_creator_sources[creator_key] = (weight, title or "a favorite", evidence)
        for g in _split_csv(genres):
            _add_affinity(target_genres, g, abs(weight))
            if weight > 0:
                source = positive_genre_sources.get(g)
                if source is None or weight > source[0]:
                    if user_rating is not None:
                        evidence = "you liked"
                    elif status == "completed":
                        evidence = "you finished"
                    elif status == "plan-to-read":
                        evidence = "you planned"
                    else:
                        evidence = "you are reading"
                    positive_genre_sources[g] = (weight, title or "a favorite", evidence)

    liked_feedback = conn.execute(
        """
        SELECT m.creator, m.genres
        FROM recommendation_feedback rf
        JOIN media m ON m.id = rf.media_id
        WHERE rf.user_id = ? AND rf.feedback = 'like'
        """,
        (user_id,),
    ).fetchall()
    for creator, genres in liked_feedback:
        creator_key = _normalize(creator)
        _add_affinity(positive_creators, creator_key, 2.0)
        if creator_key and creator_key not in positive_creator_sources:
            positive_creator_sources[creator_key] = (2.0, "a recommendation you liked", "you liked")
        for genre in _split_csv(genres):
            _add_affinity(positive_genres, genre, 2.0)
            if genre not in positive_genre_sources:
                positive_genre_sources[genre] = (2.0, "a recommendation you liked", "you liked")

    media_columns = {row[1] for row in conn.execute("PRAGMA table_info(media)").fetchall()}
    optional_columns = [column for column in ("media_type", "source", "tracker_source") if column in media_columns]
    selected_columns = ["id", "title", "creator", "genres", "rating", *optional_columns]
    candidates = conn.execute(f"SELECT {', '.join(selected_columns)} FROM media").fetchall()
    scored: list[RecommendationResult] = []
    for candidate in candidates:
        mid, title, creator, genres, rating = candidate[:5]
        optional_values = dict(zip(optional_columns, candidate[5:]))
        candidate_type = optional_values.get("media_type")
        source = optional_values.get("source")
        tracker_source = optional_values.get("tracker_source")
        if mid in already or _normalize_title(title) in already_titles or mid in dismissed:
            continue
        if media_type and _media_type(candidate_type, source, tracker_source) != media_type:
            continue
        normalized_creator = _normalize(creator)
        candidate_genres = _split_csv(genres)
        genre_score = min(sum(positive_genres.get(g, 0.0) for g in candidate_genres), 6.0)
        avoid_genre_score = min(sum(avoid_genres.get(g, 0.0) for g in candidate_genres), 6.0)
        creator_score = positive_creators.get(normalized_creator, 0.0) * 1.5 if normalized_creator else 0.0
        avoid_creator_score = avoid_creators.get(normalized_creator, 0.0) * 1.5 if normalized_creator else 0.0
        community = float(rating or 0.0)
        score = genre_score + creator_score - avoid_genre_score - avoid_creator_score + (0.35 * math.sqrt(max(community, 0.0)))
        if score <= 0:
            continue
        matching_genres = [g for g in candidate_genres if g in positive_genres]
        if creator_score > 0:
            _, source_title, evidence = positive_creator_sources[normalized_creator]
            reason = f"Because {evidence} {source_title} and often read work by {creator}."
        elif matching_genres:
            _, source_title, evidence = positive_genre_sources[matching_genres[0]]
            reason = f"Because {evidence} {source_title}, which matched your interest in {matching_genres[0]}."
        else:
            reason = "Because it is highly rated by the community."
        scored.append((RecommendationResult(media_id=mid, score=score, reason=reason), _normalize_title(title), str(mid)))

    scored.sort(key=lambda item: (-item[0].score, item[1], item[2]))
    return [item[0] for item in scored[:limit]]
