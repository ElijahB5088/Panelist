from __future__ import annotations

import httpx

from ..models import NormalizedMedia
from .base import TrackingProvider


class KitsuProvider(TrackingProvider):
    """Kitsu API provider restricted to manga library entries."""

    default_server_url = "https://kitsu.io"
    api_path = "/api/edge"
    connection_path = "/users?filter[self]=true"
    library_path = "/library-entries?filter[user_id]={user_id}&include=manga&page[limit]=500"

    @staticmethod
    def _headers(api_token: str) -> dict[str, str]:
        return {"Authorization": "Bearer " + api_token, "Accept": "application/vnd.api+json"}

    @classmethod
    def _base_url(cls, server_url: str) -> str:
        base = server_url.rstrip("/")
        if not base.endswith(cls.api_path):
            base += cls.api_path
        return base

    async def test_connection(self, server_url: str, api_token: str) -> bool:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{self._base_url(server_url)}{self.connection_path}",
                headers=self._headers(api_token),
            )
        response.raise_for_status()
        return response.is_success

    async def fetch_library(self, server_url: str, api_token: str) -> list[dict]:
        base_url = self._base_url(server_url)
        headers = self._headers(api_token)
        async with httpx.AsyncClient(timeout=30) as client:
            user_response = await client.get(f"{base_url}{self.connection_path}", headers=headers)
            user_response.raise_for_status()
            users = user_response.json().get("data", [])
            if not users:
                return []
            user_id = users[0].get("id")
            library_response = await client.get(
                f"{base_url}{self.library_path.format(user_id=user_id)}",
                headers=headers,
            )
            library_response.raise_for_status()
        return self._expand_included(library_response.json())

    def normalize_library(self, payload: list[dict]) -> list[tuple[NormalizedMedia, dict]]:
        normalized: list[tuple[NormalizedMedia, dict]] = []
        for entry in payload:
            manga = entry.get("manga") or {}
            if entry.get("type") and entry.get("type") != "manga":
                continue
            if manga.get("type") and manga.get("type") != "manga":
                continue
            manga_id = str(manga.get("id") or entry.get("manga_id") or "")
            if not manga_id:
                continue
            attributes = manga.get("attributes", manga)
            titles = attributes.get("titles") or {}
            title = attributes.get("canonicalTitle") or titles.get("en_jp") or attributes.get("title") or "Unknown"
            genres = attributes.get("genres") or []
            if isinstance(genres, list) and genres and isinstance(genres[0], dict):
                genres = [genre.get("name", "") for genre in genres]
            normalized_media = NormalizedMedia(
                id=f"kitsu:{manga_id}",
                title=title,
                creator=self._creator(attributes),
                genres=[str(genre) for genre in genres if genre],
                publisher=attributes.get("publisher") or attributes.get("serialization"),
                description=attributes.get("synopsis") or attributes.get("description"),
                rating=self._number(attributes.get("averageRating")),
                media_type="manga",
                image_url=(attributes.get("posterImage") or {}).get("large"),
            )
            normalized.append(
                (
                    normalized_media,
                    {
                        "status": self._normalize_status(entry.get("status")),
                        "progress": int(entry.get("progress", 0) or 0),
                        "user_rating": self._number(entry.get("rating")),
                    },
                )
            )
        return normalized

    @staticmethod
    def _expand_included(document: dict) -> list[dict]:
        included = {item.get("id"): item for item in document.get("included", []) if item.get("id")}
        entries = []
        for item in document.get("data", []):
            if item.get("type") != "libraryEntries":
                continue
            manga_ref = item.get("relationships", {}).get("manga", {}).get("data", {})
            manga = included.get(manga_ref.get("id"))
            if manga:
                entries.append({"type": manga.get("type"), "manga": manga, **item.get("attributes", {})})
        return entries

    @staticmethod
    def _creator(attributes: dict) -> str:
        authors = attributes.get("authors") or []
        if isinstance(authors, list) and authors:
            first = authors[0]
            if isinstance(first, dict):
                return first.get("name") or first.get("canonicalName") or "Unknown"
            return str(first)
        return attributes.get("author") or "Unknown"

    @staticmethod
    def _number(value: object) -> float | None:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_status(status: object) -> str:
        return {
            "current": "reading",
            "completed": "completed",
            "planned": "planned",
            "on_hold": "planned",
            "dropped": "dropped",
        }.get(str(status or "planned").lower(), "planned")
