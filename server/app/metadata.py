from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MetadataResult:
    source: str
    source_id: str
    title: str
    creator: str | None = None
    genres: list[str] | None = None
    publisher: str | None = None
    description: str | None = None
    rating: float | None = None
    release_date: str | None = None
    image_url: str | None = None
    source_url: str | None = None
    media_type: str | None = None


@dataclass
class MetadataGroup:
    group_id: str
    primary: MetadataResult
    variants: list[MetadataResult]