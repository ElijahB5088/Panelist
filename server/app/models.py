from __future__ import annotations

from dataclasses import dataclass


@dataclass
class NormalizedMedia:
    id: str
    title: str
    creator: str | None
    genres: list[str]
    publisher: str | None = None
    description: str | None = None
    rating: float | None = None
    source: str | None = None
    source_id: str | None = None
    media_type: str | None = None
    image_url: str | None = None
    source_url: str | None = None


@dataclass
class RecommendationResult:
    media_id: str
    score: float
    reason: str
