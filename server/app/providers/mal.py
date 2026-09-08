from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from ..models import NormalizedMedia
from .base import TrackingProvider


@dataclass
class OAuthState:
    state: str
    code_verifier: str
    authorization_url: str


class MALProvider(TrackingProvider):
    api_base_url = "https://api.myanimelist.net/v2"
    authorization_url = "https://myanimelist.net/v1/oauth2/authorize"
    token_url = "https://myanimelist.net/v1/oauth2/token"
    redirect_uri = "http://localhost:8080/api/integrations/mal/callback"
    manga_list_path = "/users/@me/mangalist"
    fields = "id,title,main_picture,synopsis,mean,genres,authors{first_name,last_name},serialization{name},my_list_status"

    def create_authorization(self, client_id: str, redirect_uri: str | None = None) -> OAuthState:
        state = secrets.token_urlsafe(32)
        code_verifier = secrets.token_urlsafe(64)
        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri or self.redirect_uri,
            "state": state,
            "code_challenge": code_verifier,
            "code_challenge_method": "plain",
        }
        return OAuthState(state, code_verifier, f"{self.authorization_url}?{urlencode(params)}")

    async def exchange_code(
        self,
        client_id: str,
        code: str,
        code_verifier: str,
        redirect_uri: str | None = None,
        client_secret: str = "",
    ) -> dict:
        data = {
            "client_id": client_id,
            "code": code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri or self.redirect_uri,
        }
        if client_secret:
            data["client_secret"] = client_secret
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(self.token_url, data=data)
        response.raise_for_status()
        return response.json()

    async def refresh_token(self, client_id: str, refresh_token: str, client_secret: str = "") -> dict:
        data = {"client_id": client_id, "refresh_token": refresh_token, "grant_type": "refresh_token"}
        if client_secret:
            data["client_secret"] = client_secret
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(self.token_url, data=data)
        response.raise_for_status()
        return response.json()

    async def test_connection(self, server_url: str, api_token: str) -> bool:
        headers = {"Authorization": "Bearer " + api_token}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{self.api_base_url}/users/@me", headers=headers)
        response.raise_for_status()
        return response.is_success

    async def fetch_library(self, server_url: str, api_token: str) -> list[dict]:
        headers = {"Authorization": "Bearer " + api_token}
        params = {"limit": 1000, "fields": self.fields}
        entries: list[dict] = []
        async with httpx.AsyncClient(timeout=30) as client:
            next_url = f"{self.api_base_url}{self.manga_list_path}"
            while next_url:
                response = await client.get(next_url, headers=headers, params=params if next_url.endswith("mangalist") else None)
                response.raise_for_status()
                document = response.json()
                entries.extend(document.get("data", []))
                next_url = document.get("paging", {}).get("next")
                params = None
        return entries

    def normalize_library(self, payload: list[dict]) -> list[tuple[NormalizedMedia, dict]]:
        normalized: list[tuple[NormalizedMedia, dict]] = []
        for row in payload:
            manga_id = row.get("node", {}).get("id") or row.get("id")
            manga = row.get("node", row)
            list_status = row.get("list_status") or manga.get("my_list_status") or {}
            if not manga_id:
                continue
            authors = manga.get("authors") or []
            creators = []
            for author in authors:
                person = author.get("node", author) if isinstance(author, dict) else {}
                name = " ".join(filter(None, [person.get("first_name"), person.get("last_name")]))
                if name:
                    creators.append(name)
            serialization = manga.get("serialization") or []
            publisher = None
            if serialization:
                first_serialization = serialization[0].get("node", serialization[0])
                publisher = first_serialization.get("name")
            picture = manga.get("main_picture") or {}
            normalized_media = NormalizedMedia(
                id=f"mal:{manga_id}",
                title=manga.get("title") or "Unknown",
                creator=", ".join(creators) or "Unknown",
                genres=[genre.get("name", "") for genre in manga.get("genres", []) if genre.get("name")],
                publisher=publisher,
                description=manga.get("synopsis"),
                rating=self._number(manga.get("mean")),
                source="mal",
                source_id=str(manga_id),
                media_type="manga",
                image_url=picture.get("large") or picture.get("medium"),
                source_url=f"https://myanimelist.net/manga/{manga_id}",
            )
            normalized.append(
                (
                    normalized_media,
                    {
                        "status": self._normalize_status(list_status.get("status")),
                        "progress": int(list_status.get("num_chapters_read", 0) or 0),
                        "user_rating": self._number(list_status.get("score")),
                    },
                )
            )
        return normalized

    @staticmethod
    def _number(value: object) -> float | None:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_status(status: object) -> str:
        return {
            "reading": "reading",
            "completed": "completed",
            "on_hold": "planned",
            "dropped": "dropped",
            "plan_to_read": "planned",
        }.get(str(status or "plan_to_read").lower(), "planned")


def encode_token_bundle(tokens: dict, previous: dict | None = None) -> str:
    return json.dumps(
        {
            "access_token": tokens["access_token"],
            "refresh_token": tokens.get("refresh_token") or (previous or {}).get("refresh_token"),
            "expires_in": tokens.get("expires_in"),
        }
    )


def decode_token_bundle(value: str) -> dict:
    return json.loads(value)
