from __future__ import annotations

import httpx

from ..models import NormalizedMedia
from .base import TrackingProvider


class FloppyProvider(TrackingProvider):
    connection_path = "/api/v1/user/preferences/"
    library_path = "/api/v1/media/"

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
            return data.get("results", data.get("items", []))
        return data

    def normalize_library(self, payload: list[dict]) -> list[tuple[NormalizedMedia, dict]]:
        normalized: list[tuple[NormalizedMedia, dict]] = []
        for row in payload:
            media = row.get("item") or row.get("media") or {}
            if not isinstance(media, dict):
                media = {}
            status = self._normalize_status(row.get("status"))
            normalized_media = NormalizedMedia(
                id=str(row.get("media_id") or media.get("media_id") or media.get("id") or row.get("id")),
                title=media.get("title") or row.get("title") or "Unknown",
                creator=media.get("creator") or row.get("creator") or row.get("source") or "Unknown",
                genres=media.get("genres", row.get("genres", [])) or [],
                publisher=media.get("publisher"),
                description=media.get("description") or media.get("synopsis"),
                rating=media.get("rating") or media.get("score"),
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
