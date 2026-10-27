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

        async def get(self, url, headers, params):
            calls.append((url, self.timeout, params))
            raise httpx.ReadTimeout("slow response")

    monkeypatch.setattr("app.providers.floppy.httpx.AsyncClient", FakeClient)

    with pytest.raises(Exception, match="Could not reach Floppy"):
        asyncio.run(FloppyProvider().fetch_library("https://floppy.example", "token"))

    assert len(calls) == 1
    timeout = calls[0][1]
    assert calls[0][2] == {"limit": 100, "offset": 0}
    assert timeout.connect == 5.0
    assert timeout.read == 20.0
    assert timeout.write == 10.0
    assert timeout.pool == 5.0


def test_floppy_fetches_all_pages(monkeypatch):
    calls = []

    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class FakeClient:
        def __init__(self, *, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def get(self, url, headers, params):
            calls.append(params)
            if url.endswith("/comic") and params["offset"] == 0:
                return FakeResponse({"results": [{"id": str(index)} for index in range(100)]})
            if url.endswith("/comic"):
                return FakeResponse({"results": [{"id": "100"}]})
            return FakeResponse({"results": []})

    monkeypatch.setattr("app.providers.floppy.httpx.AsyncClient", FakeClient)

    import asyncio

    items = asyncio.run(FloppyProvider().fetch_library("https://floppy.example", "token"))

    assert len(items) == 101
    assert calls[:2] == [
        {"limit": 100, "offset": 0},
        {"limit": 100, "offset": 100},
    ]


def test_floppy_fetch_does_not_collapse_rows_without_outer_identity(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"results": [
                {"item": {"media_type": "comic", "id": "comic-1"}},
                {"item": {"media_type": "comic", "id": "comic-2"}},
            ]}

    class FakeClient:
        def __init__(self, *, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def get(self, url, headers, params):
            if url.endswith("/comic"):
                return FakeResponse()
            return type("EmptyResponse", (), {
                "raise_for_status": lambda self: None,
                "json": lambda self: {"results": []},
            })()

    monkeypatch.setattr("app.providers.floppy.httpx.AsyncClient", FakeClient)

    import asyncio

    items = asyncio.run(FloppyProvider().fetch_library("https://floppy.example", "token"))

    assert len(items) == 2


def test_floppy_skips_unsupported_categories(monkeypatch):
    class FakeClient:
        def __init__(self, *, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def get(self, url, headers, params):
            request = httpx.Request("GET", url)
            if url.endswith("/comic"):
                return httpx.Response(200, json={"results": [{"id": "comic-1"}]}, request=request)
            return httpx.Response(404, json={"detail": "unsupported"}, request=request)

    monkeypatch.setattr("app.providers.floppy.httpx.AsyncClient", FakeClient)

    items = asyncio.run(FloppyProvider().fetch_library("https://floppy.example", "token"))

    assert items == [{"id": "comic-1"}]


def test_floppy_returns_empty_when_every_category_is_unsupported(monkeypatch):
    class FakeClient:
        def __init__(self, *, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return False

        async def get(self, url, headers, params):
            request = httpx.Request("GET", url)
            return httpx.Response(404, request=request)

    monkeypatch.setattr("app.providers.floppy.httpx.AsyncClient", FakeClient)

    assert asyncio.run(FloppyProvider().fetch_library("https://floppy.example", "token")) == []


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


def test_floppy_normalization_accepts_only_comic_media_types():
    provider = FloppyProvider()

    normalized = provider.normalize_library([
        {"media_id": "movie", "media_type": "movie", "item": {"title": "Film"}},
        {"media_id": "show", "media_type": "tv", "item": {"title": "Series"}},
        {"media_id": "comic", "media_type": "comics", "item": {"title": "Comic"}},
        {"media_id": "manhwa", "media_type": "manhwa", "item": {"title": "Manhwa"}},
    ])

    assert [media.id for media, _ in normalized] == ["comic", "manhwa"]
    assert [media.media_type for media, _ in normalized] == ["comic", "manhwa"]


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


def test_floppy_normalization_extracts_authors_and_deduplicates_titles():
    normalized = FloppyProvider().normalize_library([
        {
            "media_id": "comic-1",
            "media_type": "comic",
            "item": {"title": "Same Title", "authors": [{"name": "Jane Doe"}]},
        },
        {
            "media_id": "comic-2",
            "media_type": "comic",
            "item": {"title": " Same  Title ", "creator": "Jane Doe"},
        },
    ])

    assert len(normalized) == 1
    assert normalized[0][0].creator == "Jane Doe"


def test_floppy_normalization_ignores_placeholder_authors():
    normalized = FloppyProvider().normalize_library([
        {
            "media_id": "comic-1",
            "media_type": "comic",
            "item": {"title": "No Author", "creator": "Unknown"},
        }
    ])

    assert normalized[0][0].creator is None
