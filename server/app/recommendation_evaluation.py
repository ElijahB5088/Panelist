from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
import sqlite3

from .recommendation import build_recommendations


def precision_at_k(recommended: Sequence[str], relevant: set[str], k: int) -> float:
    if k <= 0:
        return 0.0
    selected = recommended[:k]
    return sum(item in relevant for item in selected) / len(selected) if selected else 0.0


def recall_at_k(recommended: Sequence[str], relevant: set[str], k: int) -> float:
    if not relevant or k <= 0:
        return 0.0
    return sum(item in relevant for item in recommended[:k]) / len(relevant)


def catalog_coverage(recommendation_lists: Iterable[Sequence[str]], catalog_size: int) -> float:
    if catalog_size <= 0:
        return 0.0
    unique_items = {item for recommendations in recommendation_lists for item in recommendations}
    return len(unique_items) / catalog_size


def concentration(
    recommended: Sequence[str],
    attribute_for: Callable[[str], str | None],
) -> float:
    if not recommended:
        return 0.0
    counts: dict[str, int] = {}
    for item in recommended:
        attribute = attribute_for(item) or "unknown"
        counts[attribute] = counts.get(attribute, 0) + 1
    return max(counts.values()) / len(recommended)


def evaluate_user(
    conn: sqlite3.Connection,
    user_id: int,
    relevant: set[str],
    *,
    k: int = 10,
    mode: str = "balanced",
) -> dict[str, float | int]:
    results = build_recommendations(conn, user_id, limit=k, mode=mode)
    ids = [result.media_id for result in results]
    return {
        "k": k,
        "recommended": len(ids),
        "precision_at_k": precision_at_k(ids, relevant, k),
        "recall_at_k": recall_at_k(ids, relevant, k),
    }
