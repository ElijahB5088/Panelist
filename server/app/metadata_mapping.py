from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .metadata import MetadataResult


MANGA_ORIGIN_CODES = frozenset({"CN", "JP", "KR"})


def has_manga_origin(result: MetadataResult) -> bool:
    return (result.country_of_origin or "").upper() in MANGA_ORIGIN_CODES


@dataclass(frozen=True)
class MetadataIdentity:
    title: str
    creator: str
    release_year: str
    media_type: str

    @property
    def key(self) -> str:
        return "|".join((self.title, self.creator, self.release_year, self.media_type))


@dataclass(frozen=True)
class MetadataMatch:
    identity: MetadataIdentity
    confidence: float
    reason: str


@dataclass(frozen=True)
class MetadataComparison:
    accepted: bool
    reason: str


def map_metadata(result: MetadataResult) -> MetadataMatch:
    identity = MetadataIdentity(
        title=normalize_identity(result.title),
        creator=normalize_identity(result.creator),
        release_year=normalize_year(result.release_date),
        media_type=normalize_media_type(result.media_type, source=result.source, title=result.title),
    )
    confidence, reason = _match_quality(identity)
    return MetadataMatch(identity=identity, confidence=confidence, reason=reason)


def compare_metadata(
    result: MetadataResult,
    title: str | None,
    creator: str | None,
    media_type: str | None,
    tracker_source: str | None = None,
) -> MetadataComparison:
    expected_title = normalize_identity(title)
    candidate_titles = {
        normalize_identity(value)
        for value in [result.title, *(result.aliases or [])]
        if normalize_identity(value)
    }
    if not expected_title or not candidate_titles:
        return MetadataComparison(False, "missing_title")
    if expected_title not in candidate_titles:
        return MetadataComparison(False, "title_mismatch")

    expected_creator = normalize_identity(creator)
    candidate_creator = normalize_identity(result.creator)
    if expected_creator and expected_creator != candidate_creator:
        return MetadataComparison(False, "creator_mismatch")

    expected_type = normalize_media_type(media_type, tracker_source=tracker_source)
    candidate_type = normalize_media_type(result.media_type, source=result.source, title=result.title)
    if expected_type and candidate_type and expected_type != candidate_type:
        return MetadataComparison(False, "media_type_mismatch")

    return MetadataComparison(True, "title_creator_media_type")


def normalize_identity(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^\w]+", " ", normalized, flags=re.UNICODE).strip()


def normalize_year(value: str | None) -> str:
    if not value:
        return ""
    match = re.match(r"\s*(\d{4})", value)
    return match.group(1) if match else ""


def normalize_media_type(
    value: str | None,
    source: str | None = None,
    tracker_source: str | None = None,
    title: str | None = None,
) -> str:
    normalized = normalize_identity(value)
    if source in {"anilist", "kitsu", "mal"} or tracker_source in {"kitsu", "mal"}:
        if normalized in {"manga", "manhwa", "manhua"}:
            return normalized
        return "manga"
    if normalized in {"comic", "comics"}:
        return "comic"
    if normalized in {"manga", "manhwa", "manhua"}:
        return normalized
    return normalized


def _match_quality(identity: MetadataIdentity) -> tuple[float, str]:
    if identity.title and identity.creator and identity.release_year:
        return 1.0, "title_creator_year"
    if identity.title and identity.creator:
        return 0.9, "title_creator"
    if identity.title and identity.release_year:
        return 0.75, "title_year"
    if identity.title:
        return 0.5, "title_only"
    return 0.0, "missing_title"