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
            return data.get("items", [])
        return data

    def normalize_library(self, payload: list[dict]) -> list[tuple[NormalizedMedia, dict]]:
        normalized: list[tuple[NormalizedMedia, dict]] = []
        for row in payload:
            media = row.get("media", {})
            normalized_media = NormalizedMedia(
                id=str(media.get("id", row.get("id"))),
                title=media.get("title", row.get("title", "Unknown")),
                creator=media.get("creator", row.get("creator", "Unknown")),
                genres=media.get("genres", row.get("genres", [])) or [],
                publisher=media.get("publisher"),
                description=media.get("description"),
                rating=media.get("rating"),
            )
            lib = {
                "status": row.get("status", "planned"),
                "progress": int(row.get("progress", 0) or 0),
                "user_rating": row.get("rating"),
            }
            normalized.append((normalized_media, lib))
        return normalized
