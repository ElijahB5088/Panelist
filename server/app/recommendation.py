from __future__ import annotations

import math
import sqlite3

from .models import RecommendationResult


def _split_csv(text: str | None) -> list[str]:
    if not text:
        return []
    return [_normalize(p) for p in text.split(",") if p.strip()]


def _normalize(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def build_recommendations(conn: sqlite3.Connection, user_id: int, limit: int = 20) -> list[RecommendationResult]:
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
            "SELECT media_id FROM user_library WHERE user_id = ?",
            (user_id,),
        ).fetchall()
    }

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
    anchor_title = library[0][0] if library else "your favorites"

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
        target_creators[creator_key] = target_creators.get(creator_key, 0.0) + abs(weight)
        for g in _split_csv(genres):
            target_genres[g] = target_genres.get(g, 0.0) + abs(weight)

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
        positive_creators[_normalize(creator)] = positive_creators.get(_normalize(creator), 0.0) + 2.0
        for genre in _split_csv(genres):
            positive_genres[genre] = positive_genres.get(genre, 0.0) + 2.0

    candidates = conn.execute("SELECT id, title, creator, genres, rating FROM media").fetchall()
    scored: list[RecommendationResult] = []
    for mid, title, creator, genres, rating in candidates:
        if mid in already or mid in dismissed:
            continue
        normalized_creator = _normalize(creator)
        genre_score = sum(positive_genres.get(g, 0.0) for g in _split_csv(genres))
        avoid_genre_score = sum(avoid_genres.get(g, 0.0) for g in _split_csv(genres))
        creator_score = positive_creators.get(normalized_creator, 0.0) * 1.5
        avoid_creator_score = avoid_creators.get(normalized_creator, 0.0) * 1.5
        community = float(rating or 0.0)
        score = genre_score + creator_score - avoid_genre_score - avoid_creator_score + (0.35 * math.sqrt(max(community, 0.0)))
        if score <= 0:
            continue
        overlap = sum(1 for g in _split_csv(genres) if g in positive_genres)
        if creator_score > 0:
            reason = f"Because you liked {anchor_title} and often read work by {creator}."
        elif overlap:
            reason = f"Matches your taste: shares {overlap} genres with titles you've rated highly."
        else:
            reason = f"Because you liked {anchor_title}."
        scored.append(RecommendationResult(media_id=mid, score=score, reason=reason))

    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:limit]
