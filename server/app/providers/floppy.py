from __future__ import annotations

import httpx

from ..models import NormalizedMedia
from .base import TrackingProvider


class FloppyProviderError(RuntimeError):
    """A safe, user-facing description of a Floppy API failure."""


class FloppyProvider(TrackingProvider):
    connection_path = "/api/v1/user/preferences/"
    library_path = "/api/v1/media/"
    supported_media_types = {"comic", "comics", "manga"}
    api_media_types = ("comic", "manga")

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
        library: list[dict] = []
        async with httpx.AsyncClient(timeout=30) as client:
            for media_type in self.api_media_types:
                offset = 0
                while True:
                    try:
                        resp = await client.get(
                            f"{server_url.rstrip('/')}{self.library_path}",
                            headers=headers,
                            params={"media_type": media_type, "limit": 100, "offset": offset},
                        )
                        resp.raise_for_status()
                    except httpx.HTTPStatusError as exc:
                        raise FloppyProviderError(
                            f"Floppy API returned HTTP {exc.response.status_code}"
                        ) from exc
                    except httpx.HTTPError as exc:
                        raise FloppyProviderError("Could not reach the Floppy API") from exc

                    try:
                        data = resp.json()
                    except ValueError as exc:
                        raise FloppyProviderError("Floppy API returned invalid JSON") from exc

                    if isinstance(data, list):
                        page = data
                        next_url = None
                    elif isinstance(data, dict):
                        page = next((data[key] for key in ("results", "items", "data") if isinstance(data.get(key), list)), None)
                        next_url = data.get("next")
                    else:
                        page = None
                        next_url = None
                    if page is None:
                        raise FloppyProviderError("Floppy API returned an unsupported library response")

                    library.extend(page)
                    if not page or not next_url:
                        break
                    offset += len(page)
        return library

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
            status = self._normalize_status(row.get("status"))
            source = str(row.get("source") or media.get("source") or "").strip() or None
            source_id = str(
                row.get("media_id")
                or media.get("media_id")
                or media.get("id")
                or row.get("item_id")
                or row.get("id")
            )
            creator = self._creator(media.get("authors") or media.get("creators"))
            creator = creator or media.get("creator") or row.get("creator")
            local_id = f"floppy:{source}:{source_id}" if source else source_id
            progress = int(row.get("progress", 0) or 0)
            progress_max = row.get("max_progress") or media.get("max_progress")
            try:
                progress_max = int(progress_max) if progress_max is not None else None
            except (TypeError, ValueError):
                progress_max = None
            progress_percent = None
            if status == "completed":
                progress_percent = 100
            elif progress_max and progress_max > 0:
                progress_percent = min(100, max(0, round(progress / progress_max * 100)))
            normalized_media = NormalizedMedia(
                id=local_id,
                title=media.get("title") or row.get("title") or "Unknown",
                creator=creator,
                genres=media.get("genres", row.get("genres", [])) or [],
                publisher=media.get("publisher"),
                description=media.get("description") or media.get("synopsis"),
                rating=media.get("rating") or media.get("provider_rating") or media.get("score"),
                source=source,
                source_id=source_id,
                media_type=media_type,
            )
            lib = {
                "status": status,
                "progress": progress,
                "progress_max": progress_max,
                "progress_unit": row.get("progress_unit") or media.get("progress_unit"),
                "progress_scope": row.get("progress_scope") or media.get("progress_scope"),
                "progress_percent": progress_percent,
                "tracker_source": source,
                "tracker_media_id": source_id,
                "tracker_item_id": row.get("item_id"),
                "user_rating": row.get("score") or row.get("rating"),
            }
            normalized.append((normalized_media, lib))
        return normalized

    @staticmethod
    def _creator(value: object) -> str | None:
        if not isinstance(value, list):
            return None
        names = []
        for person in value:
            if isinstance(person, str) and person.strip():
                names.append(person.strip())
            elif isinstance(person, dict):
                name = person.get("name") or " ".join(
                    filter(None, [person.get("first_name"), person.get("last_name")])
                )
                if name:
                    names.append(str(name).strip())
        return ", ".join(names) or None

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
