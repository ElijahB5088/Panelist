import asyncio

import httpx
import pytest

from app.providers.floppy import FloppyProvider


def test_floppy_api_paths():
    provider = FloppyProvider()

    assert provider.connection_path == "/api/v1/user/preferences/"
    assert provider.library_path == "/api/v1/media/"


def test_floppy_fetch_uses_bounded_timeout_without_retries(monkeypatch):
    calls = []

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def get(self, url, headers):
            calls.append((url, self.timeout))
            raise httpx.ReadTimeout("slow response")

    monkeypatch.setattr("app.providers.floppy.httpx.AsyncClient", FakeClient)

    with pytest.raises(httpx.ReadTimeout):
        asyncio.run(FloppyProvider().fetch_library("https://floppy.example", "token"))

    assert len(calls) == 1
    timeout = calls[0][1]
    assert timeout.connect == 5.0
    assert timeout.read == 20.0
    assert timeout.write == 10.0
    assert timeout.pool == 5.0


def test_floppy_normalization():
    provider = FloppyProvider()
    payload = [
        {
            "status": 1,
            "progress": 42,
            "rating": 5,
            "media_id": "x1",
            "media_type": "manga",
            "item": {
                "title": "X",
                "creator": "C",
                "genres": ["sci-fi"],
            },
        }
    ]
    normalized = provider.normalize_library(payload)
    media, lib = normalized[0]
    assert media.id == "x1"
    assert media.genres == ["sci-fi"]
    assert lib["status"] == "reading"


def test_floppy_envelope_and_statuses():
    provider = FloppyProvider()

    assert provider.fetch_library
    normalized = provider.normalize_library([
        {"media_id": "x2", "media_type": "comic", "status": 3, "progress": 100, "item": {"title": "Done"}},
        {"media_id": "x3", "media_type": "manga", "status": 0, "progress": 0, "item": {"title": "Queued"}},
    ])

    assert [library["status"] for _, library in normalized] == ["completed", "planned"]


def test_floppy_anime_payload_is_excluded():
    provider = FloppyProvider()

    normalized = provider.normalize_library([
        {
            "media_id": "anime-1",
            "media_type": "anime",
            "status": 1,
            "progress": 4,
            "item": {"title": "Current Anime"},
        }
    ])

    assert normalized == []


def test_floppy_normalization_excludes_other_media_types():
    provider = FloppyProvider()

    normalized = provider.normalize_library([
        {"media_id": "movie", "media_type": "movie", "item": {"title": "Film"}},
        {"media_id": "show", "media_type": "tv", "item": {"title": "Series"}},
        {"media_id": "comic", "media_type": "comics", "item": {"title": "Comic"}},
    ])

    assert [media.id for media, _ in normalized] == ["comic"]


def test_floppy_normalization_accepts_nested_type_and_data_fields():
    provider = FloppyProvider()

    normalized = provider.normalize_library([
        {
            "id": "entry-1",
            "status": "reading",
            "progress": 12,
            "data": {
                "id": "comic-1",
                "type": "comic",
                "title": "Nested Comic",
            },
        }
    ])

    assert len(normalized) == 1
    media, library = normalized[0]
    assert media.id == "comic-1"
    assert media.title == "Nested Comic"
    assert library["status"] == "reading"


def test_floppy_normalization_preserves_type_and_cover_url():
    provider = FloppyProvider()

    normalized = provider.normalize_library([
        {
            "media_id": "comic-1",
            "media_type": "comics",
            "item": {"title": "Covered Comic", "cover": "https://covers.example/comic.jpg"},
        }
    ])

    media, _ = normalized[0]
    assert media.media_type == "comic"
    assert media.image_url == "https://covers.example/comic.jpg"


def test_floppy_normalization_skips_missing_ids():
    normalized = FloppyProvider().normalize_library([
        {"media_type": "comic", "item": {"title": "Invalid"}},
        {"media_type": "comic", "media_id": "None", "item": {"title": "Invalid"}},
    ])

    assert normalized == []
