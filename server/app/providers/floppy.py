from __future__ import annotations

import httpx

from ..models import NormalizedMedia
from ..metadata_mapping import normalize_identity
from .base import TrackingProvider, valid_external_id


class FloppyProviderError(Exception):
    pass


class FloppyProvider(TrackingProvider):
    request_timeout = httpx.Timeout(connect=5.0, read=20.0, write=10.0, pool=5.0)
    connection_path = "/api/v1/user/preferences/"
    library_path = "/api/v1/media/"
    library_media_types = ("comic", "comics", "manga", "manhwa", "manhua")
    supported_media_types = set(library_media_types)

    async def test_connection(self, server_url: str, api_token: str) -> bool:
        headers = {
            "Authorization": "Bearer " + api_token,
            "X-API-Key": api_token,
        }
        async with httpx.AsyncClient(timeout=self.request_timeout) as client:
            resp = await client.get(f"{server_url.rstrip('/')}{self.connection_path}", headers=headers)
        resp.raise_for_status()
        return resp.is_success

    async def fetch_library(self, server_url: str, api_token: str) -> list[dict]:
        headers = {
            "Authorization": "Bearer " + api_token,
            "X-API-Key": api_token,
        }
        async with httpx.AsyncClient(timeout=self.request_timeout) as client:
            items: list[dict] = []
            seen: set[tuple[object, ...]] = set()
            successful_categories = 0
            skipped_categories = 0
            for media_type in self.library_media_types:
                limit = 100
                offset = 0
                while True:
                    try:
                        resp = await client.get(
                            f"{server_url.rstrip('/')}{self.library_path}{media_type}",
                            headers=headers,
                            params={"limit": limit, "offset": offset},
                        )
                        resp.raise_for_status()
                    except httpx.HTTPStatusError as exc:
                        if exc.response.status_code in {400, 404, 405, 422}:
                            skipped_categories += 1
                            break
                        raise FloppyProviderError(
                            f"Floppy library request for media/{media_type} returned HTTP "
                            f"{exc.response.status_code}"
                        ) from exc
                    except httpx.HTTPError as exc:
                        raise FloppyProviderError(
                            f"Could not reach Floppy while loading media/{media_type}: "
                            f"{type(exc).__name__}"
                        ) from exc
                    try:
                        data = resp.json()
                    except ValueError as exc:
                        raise FloppyProviderError(
                            f"Floppy returned invalid JSON for media/{media_type}"
                        ) from exc
                    successful_categories += 1
                    if isinstance(data, list):
                        page = data
                    elif isinstance(data, dict):
                        page = next(
                            (
                                value
                                for key in ("results", "items", "data")
                                for value in (data.get(key),)
                                if isinstance(value, list)
                            ),
                            [],
                        )
                    else:
                        page = []
                    for item in page:
                        if not isinstance(item, dict):
                            continue
                        item = dict(item)
                        nested = item.get("item") or item.get("media") or item.get("data") or {}
                        if isinstance(nested, dict):
                            nested = dict(nested)
                            nested.setdefault("library_media_type", media_type)
                            item["item"] = nested
                        item.setdefault("library_media_type", media_type)
                        identity = (
                            item.get("media_type") or (nested.get("media_type") if isinstance(nested, dict) else None),
                            item.get("source") or (nested.get("source") if isinstance(nested, dict) else None),
                            item.get("media_id")
                            or item.get("id")
                            or (nested.get("media_id") or nested.get("id") if isinstance(nested, dict) else None),
                        )
                        if identity[2] is None or identity not in seen:
                            seen.add(identity)
                            items.append(item)
                    if len(page) < limit:
                        break
                    offset += limit
            return items

    def normalize_library(self, payload: list[dict]) -> list[tuple[NormalizedMedia, dict]]:
        normalized_by_identity: dict[tuple[str, str], tuple[NormalizedMedia, dict]] = {}
        for row in payload:
            media = row.get("item") or row.get("media") or row.get("data") or {}
            if not isinstance(media, dict):
                media = {}
            endpoint_type = str(row.get("library_media_type") or "").strip().lower()
            payload_type = str(
                row.get("media_type")
                or row.get("type")
                or media.get("media_type")
                or media.get("type")
                or ""
            ).strip().lower()
            if endpoint_type and payload_type:
                normalized_endpoint_type = "comic" if endpoint_type == "comics" else endpoint_type
                normalized_payload_type = "comic" if payload_type == "comics" else payload_type
                if normalized_endpoint_type != normalized_payload_type:
                    continue
            media_type = str(
                row.get("library_media_type")
                or media.get("library_media_type")
                or row.get("media_type")
                or row.get("type")
                or media.get("library_media_type")
                or media.get("media_type")
                or media.get("type")
                or ""
            ).strip().lower()
            if media_type not in self.supported_media_types:
                continue
            if media_type in {"comic", "comics"}:
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
            external_id = valid_external_id(
                row.get("media_id") or media.get("media_id") or media.get("id") or row.get("id")
            )
            if not external_id:
                continue
            creator = self._creator(row, media)
            normalized_media = NormalizedMedia(
                id=external_id,
                title=media.get("title") or row.get("title") or "Unknown",
                creator=creator,
                genres=media.get("genres", row.get("genres", [])) or [],
                publisher=media.get("publisher"),
                description=media.get("description") or media.get("synopsis"),
                rating=media.get("rating") or media.get("score"),
                source="floppy",
                source_id=external_id,
                media_type=media_type,
                image_url=image_url,
            )
            lib = {
                "tracker_source": "floppy",
                "tracker_media_id": external_id,
                "tracker_item_id": valid_external_id(row.get("id")),
                "status": status,
                "progress": int(row.get("progress", 0) or 0),
                "user_rating": row.get("score") or row.get("rating"),
            }
            identity = (
                normalize_identity(normalized_media.title),
                normalize_identity(creator) if creator else "",
            )
            existing = normalized_by_identity.get(identity)
            if existing is None or (not existing[0].creator and creator):
                normalized_by_identity[identity] = (normalized_media, lib)
        return list(normalized_by_identity.values())

    @classmethod
    def _creator(cls, row: dict, media: dict) -> str | None:
        values = (
            row.get("creator"),
            row.get("author"),
            media.get("creator"),
            media.get("author"),
            media.get("writer"),
            media.get("writers"),
            media.get("authors"),
            media.get("credits"),
        )
        for value in values:
            creator = cls._creator_value(value)
            if creator:
                return creator
        return None

    @staticmethod
    def _creator_value(value: object) -> str | None:
        if isinstance(value, str):
            candidate = value.strip()
            return candidate if normalize_identity(candidate) not in {"unknown", "n/a", "n a", "none"} else None
        if isinstance(value, dict):
            for key in ("name", "display_name", "creator", "author", "writer", "person"):
                creator = FloppyProvider._creator_value(value.get(key))
                if creator:
                    return creator
            return None
        if isinstance(value, list):
            creators = [FloppyProvider._creator_value(item) for item in value]
            names = [name for name in creators if name]
            return ", ".join(names) if names else None
        return None

    @staticmethod
    def _normalize_status(status: object) -> str:
        try:
            numeric_status = int(status)
        except (TypeError, ValueError):
            return str(status or "planned").lower()
        return {
            0: "planned",
            1: "reading",
            2: "reading",
            3: "completed",
            4: "dropped",
        }.get(numeric_status, "planned")
