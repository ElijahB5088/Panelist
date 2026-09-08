from __future__ import annotations

import httpx

from ..models import NormalizedMedia
from .base import TrackingProvider


class FloppyProviderError(Exception):
    pass


class FloppyProvider(TrackingProvider):
    connection_path = "/api/v1/user/preferences/"
    library_path = "/api/v1/media/"
    supported_media_types = {"comic", "comics", "manga"}

    async def test_connection(self, server_url: str, api_token: str) -> bool:
        headers = {
            "Authorization": "Bearer " + api_token,
            "X-API-Key": api_token,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{server_url.rstrip('/')}{self.connection_path}", headers=headers)
        resp.raise_for_status()
        return resp.is_success

    async def fetch_library(self, server_url: str, api_token: str) -> list[dict]:
        headers = {
            "Authorization": "Bearer " + api_token,
            "X-API-Key": api_token,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{server_url.rstrip('/')}{self.library_path}", headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            for key in ("results", "items", "data"):
                value = data.get(key)
                if isinstance(value, list):
                    return value
            return []
        return data

    def normalize_library(self, payload: list[dict]) -> list[tuple[NormalizedMedia, dict]]:
        normalized: list[tuple[NormalizedMedia, dict]] = []
        for row in payload:
            media = row.get("item") or row.get("media") or row.get("data") or {}
            if not isinstance(media, dict):
                media = {}
            media_type = str(
                row.get("library_media_type")
                or row.get("media_type")
                or row.get("type")
                or media.get("library_media_type")
                or media.get("media_type")
                or media.get("type")
                or ""
            ).strip().lower()
            if media_type not in self.supported_media_types:
                continue
            if media_type == "comics":
                media_type = "comic"
            image_url = next(
                (
                    value
                    for value in (
                        row.get("image_url"),
                        row.get("image"),
                        row.get("cover_url"),
                        row.get("cover"),
                        row.get("thumbnail"),
                        media.get("image_url"),
                        media.get("image"),
                        media.get("cover_url"),
                        media.get("cover"),
                        media.get("thumbnail"),
                    )
                    if isinstance(value, str) and value.strip()
                ),
                None,
            )
            status = self._normalize_status(row.get("status"))
            normalized_media = NormalizedMedia(
                id=str(row.get("media_id") or media.get("media_id") or media.get("id") or row.get("id")),
                title=media.get("title") or row.get("title") or "Unknown",
                creator=media.get("creator") or row.get("creator") or row.get("source") or "Unknown",
                genres=media.get("genres", row.get("genres", [])) or [],
                publisher=media.get("publisher"),
                description=media.get("description") or media.get("synopsis"),
                rating=media.get("rating") or media.get("score"),
                media_type=media_type,
                image_url=image_url,
            )
            lib = {
                "status": status,
                "progress": int(row.get("progress", 0) or 0),
                "user_rating": row.get("score") or row.get("rating"),
            }
            normalized.append((normalized_media, lib))
        return normalized

    @staticmethod
    def _normalize_status(status: object) -> str:
        try:
            numeric_status = int(status)
        except (TypeError, ValueError):
            return str(status or "planned").lower()
        return {
            1: "reading",
            2: "completed",
            3: "planned",
            4: "dropped",
            5: "planned",
        }.get(numeric_status, "planned")
