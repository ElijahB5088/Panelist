from __future__ import annotations

import math
import sqlite3
from datetime import datetime, timezone

from .metadata_mapping import normalize_identity, normalize_media_type
from .models import RecommendationResult


def _split_csv(text: str | None) -> list[str]:
    if not text:
        return []
    return [_normalize(p) for p in text.split(",") if p.strip()]


def _normalize(value: str | None) -> str:
    normalized = " ".join((value or "").casefold().split())
    return "" if normalized in {"unknown", "n/a", "n a", "none", "null", "comic", "comics", "manga"} else normalized


def _add_affinity(target: dict[str, float], key: str, weight: float) -> None:
    if not key:
        return
    target[key] = min(target.get(key, 0.0) + weight, 6.0)


def _recency_factor(value: str | None, half_life_days: float = 180.0) -> float:
    if not value:
        return 1.0
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return 1.0
    age_days = max((datetime.now(timezone.utc) - timestamp).total_seconds() / 86400.0, 0.0)
    return 0.5 ** (age_days / half_life_days)


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
            """,
            (user_id,),
        ).fetchall()
    }


def _media_type(
    value: str | None,
    source: str | None = None,
    tracker_source: str | None = None,
    title: str | None = None,
) -> str | None:
    return normalize_media_type(value, source=source, tracker_source=tracker_source, title=title) or None


def build_recommendations(
    conn: sqlite3.Connection,
    user_id: int,
    limit: int = 20,
    media_type: str | None = None,
    mode: str = "balanced",
) -> list[RecommendationResult]:
    if mode not in {"balanced", "familiar", "discovery"}:
        raise ValueError("unsupported recommendation mode")
    library_columns = {row[1] for row in conn.execute("PRAGMA table_info(user_library)").fetchall()}
    media_columns = {row[1] for row in conn.execute("PRAGMA table_info(media)").fetchall()}
    added_at_column = "ul.added_at" if "added_at" in library_columns else "NULL"
    publisher_column = "m.publisher" if "publisher" in media_columns else "NULL"
    library = conn.execute(
        f"""
        SELECT m.title, m.creator, m.genres, {publisher_column}, ul.status,
               ul.progress, ul.user_rating, {added_at_column}
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
            """,
            (user_id,),
        ).fetchall()
    }
    already_titles = library_title_keys(conn, user_id)

    dismissed = {
        row[0]: row[1]
        for row in conn.execute(
            """
            SELECT media_id, MAX(created_at)
            FROM recommendation_feedback
            WHERE user_id = ? AND feedback = 'dismiss'
            GROUP BY media_id
            """,
            (user_id,),
        ).fetchall()
    }

    positive_genres: dict[str, float] = {}
    positive_creators: dict[str, float] = {}
    positive_publishers: dict[str, float] = {}
    avoid_genres: dict[str, float] = {}
    avoid_creators: dict[str, float] = {}
    positive_genre_sources: dict[str, tuple[float, str, str]] = {}
    positive_creator_sources: dict[str, tuple[float, str, str]] = {}

    for title, creator, genres, publisher, status, progress, user_rating, added_at in library:
        recency = _recency_factor(added_at)
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
        weight *= recency

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
        if weight > 0:
            _add_affinity(positive_publishers, _normalize(publisher), abs(weight) * 0.6)
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
        SELECT m.creator, m.genres, rf.created_at
        FROM recommendation_feedback rf
        JOIN media m ON m.id = rf.media_id
        WHERE rf.user_id = ? AND rf.feedback = 'like'
        """,
        (user_id,),
    ).fetchall()
    for creator, genres, created_at in liked_feedback:
        feedback_weight = 2.0 * _recency_factor(created_at, half_life_days=120.0)
        creator_key = _normalize(creator)
        _add_affinity(positive_creators, creator_key, feedback_weight)
        if creator_key and creator_key not in positive_creator_sources:
            positive_creator_sources[creator_key] = (feedback_weight, "a recommendation you liked", "you liked")
        for genre in _split_csv(genres):
            _add_affinity(positive_genres, genre, feedback_weight)
            if genre not in positive_genre_sources:
                positive_genre_sources[genre] = (feedback_weight, "a recommendation you liked", "you liked")

    optional_columns = [column for column in ("media_type", "source", "tracker_source") if column in media_columns]
    if "publisher" in media_columns:
        optional_columns.append("publisher")
    selected_columns = ["id", "title", "creator", "genres", "rating", *optional_columns]
    candidates = conn.execute(f"SELECT {', '.join(selected_columns)} FROM media").fetchall()
    scored: list[RecommendationResult] = []
    for candidate in candidates:
        mid, title, creator, genres, rating = candidate[:5]
        optional_values = dict(zip(optional_columns, candidate[5:]))
        candidate_type = optional_values.get("media_type")
        source = optional_values.get("source")
        tracker_source = optional_values.get("tracker_source")
        publisher = optional_values.get("publisher")
        if mid in already or _normalize_title(title) in already_titles:
            continue
        if mid in dismissed and _recency_factor(dismissed[mid], half_life_days=30.0) > 0.25:
            continue
        if media_type and _media_type(candidate_type, source, tracker_source, title) != media_type:
            continue
        normalized_creator = _normalize(creator)
        candidate_genres = _split_csv(genres)
        genre_score = min(sum(positive_genres.get(g, 0.0) for g in candidate_genres), 6.0)
        avoid_genre_score = min(sum(avoid_genres.get(g, 0.0) for g in candidate_genres), 6.0)
        creator_score = positive_creators.get(normalized_creator, 0.0) * 1.5 if normalized_creator else 0.0
        publisher_score = positive_publishers.get(_normalize(publisher), 0.0) if publisher else 0.0
        avoid_creator_score = avoid_creators.get(normalized_creator, 0.0) * 1.5 if normalized_creator else 0.0
        community = float(rating or 0.0)
        score = (
            genre_score
            + creator_score
            + publisher_score
            - avoid_genre_score
            - avoid_creator_score
            + (0.35 * math.sqrt(max(community, 0.0)))
        )
        has_personal_match = bool(genre_score or creator_score)
        if mode == "familiar" and not has_personal_match:
            continue
        if mode == "discovery" and has_personal_match:
            score *= 0.65
        if mode == "discovery" and normalized_creator in positive_creators:
            score *= 0.5
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
    selected = []
    creator_counts: dict[str, int] = {}
    genre_counts: dict[str, int] = {}
    for item in scored:
        row = conn.execute(
            "SELECT creator, genres FROM media WHERE id = ?",
            (item[0].media_id,),
        ).fetchone()
        creator_key = _normalize(row[0]) if row else ""
        genres = _split_csv(row[1]) if row else []
        if creator_counts.get(creator_key, 0) >= 3 and len(scored) > limit:
            continue
        if genres and all(genre_counts.get(genre, 0) >= 5 for genre in genres) and len(scored) > limit:
            continue
        selected.append(item[0])
        creator_counts[creator_key] = creator_counts.get(creator_key, 0) + 1
        for genre in genres:
            genre_counts[genre] = genre_counts.get(genre, 0) + 1
        if len(selected) >= limit:
            break
    return selected
