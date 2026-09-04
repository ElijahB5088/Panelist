from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NormalizedMedia:
    id: str
    title: str
    creator: str
    genres: list[str]
    publisher: str | None = None
    description: str | None = None
    rating: float | None = None


@dataclass
class RecommendationResult:
    media_id: str
    score: float
    reason: str
