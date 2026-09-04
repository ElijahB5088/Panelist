from __future__ import annotations

import math
import sqlite3

from .models import RecommendationResult


def _split_csv(text: str | None) -> list[str]:
    if not text:
        return []
    return [p.strip() for p in text.split(",") if p.strip()]


def build_recommendations(conn: sqlite3.Connection, user_id: int, limit: int = 20) -> list[RecommendationResult]:
    liked = conn.execute(
        """
        SELECT m.title, m.creator, m.genres, ul.user_rating
        FROM user_library ul
        JOIN media m ON m.id = ul.media_id
        WHERE ul.user_id = ? AND COALESCE(ul.user_rating, 0) >= 4
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

    liked_genres: dict[str, float] = {}
    liked_creators: dict[str, float] = {}
    anchor_title = liked[0][0] if liked else "your favorites"

    for title, creator, genres, user_rating in liked:
        weight = float(user_rating or 4)
        liked_creators[creator] = liked_creators.get(creator, 0.0) + weight
        for g in _split_csv(genres):
            liked_genres[g] = liked_genres.get(g, 0.0) + weight

    candidates = conn.execute("SELECT id, title, creator, genres, rating FROM media").fetchall()
    scored: list[RecommendationResult] = []
    for mid, title, creator, genres, rating in candidates:
        if mid in already or mid in dismissed:
            continue
        genre_score = sum(liked_genres.get(g, 0.0) for g in _split_csv(genres))
        creator_score = liked_creators.get(creator, 0.0) * 1.5
        community = float(rating or 0.0)
        score = genre_score + creator_score + math.sqrt(max(community, 0.0))
        if score <= 0:
            continue
        overlap = sum(1 for g in _split_csv(genres) if g in liked_genres)
        if creator_score > 0:
            reason = f"Because you liked {anchor_title} and often read work by {creator}."
        elif overlap:
            reason = f"Matches your taste: shares {overlap} genres with titles you've rated highly."
        else:
            reason = f"Because you liked {anchor_title}."
        scored.append(RecommendationResult(media_id=mid, score=score, reason=reason))

    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:limit]
