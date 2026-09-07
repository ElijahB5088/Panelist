import asyncio

import httpx
import pytest

from app.providers.floppy import FloppyProvider, FloppyProviderError


class FakeAsyncClient:
    response = None
    error = None
    response_sequence = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, headers, params=None):
        if self.error:
            raise self.error
        if self.response_sequence:
            return self.response_sequence.pop(0)
        return self.response


def test_floppy_api_paths():
    provider = FloppyProvider()

    assert provider.connection_path == "/api/v1/user/preferences/"
    assert provider.library_path == "/api/v1/media/"


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
        {"media_id": "x3", "media_type": "manga", "status": 5, "progress": 0, "item": {"title": "Queued"}},
    ])

    assert [library["status"] for _, library in normalized] == ["completed", "planned"]


def test_floppy_completed_payload_keeps_cover_and_rating():
    media, library = FloppyProvider().normalize_library([
        {
            "status": 3,
            "score": 8.9,
            "progress": 1,
            "item_id": "comic/comicvine/139922",
            "item": {
                "media_id": "139922",
                "media_type": "comic",
                "library_media_type": "comic",
                "source": "comicvine",
                "title": "The Human Target",
                "image": "https://comicvine.gamespot.com/a/uploads/scale_medium/6/67663/8227890-01.jpg",
                "source_url": "",
            },
        }
    ])[0]

    assert media.image_url == "https://comicvine.gamespot.com/a/uploads/scale_medium/6/67663/8227890-01.jpg"
    assert media.source_url is None
    assert library["status"] == "completed"
    assert library["user_rating"] == 8.9


def test_floppy_fetch_library_accepts_supported_envelopes(monkeypatch):
    request = httpx.Request("GET", "https://floppy.example/api/v1/media/")
    response = httpx.Response(200, request=request, json={"results": [{"id": "x1"}], "next": None})
    empty_manga = httpx.Response(200, request=request, json={"results": [], "next": None})
    monkeypatch.setattr("app.providers.floppy.httpx.AsyncClient", lambda **kwargs: FakeAsyncClient())
    FakeAsyncClient.response = response
    FakeAsyncClient.response_sequence = [response, empty_manga]

    payload = asyncio.run(FloppyProvider().fetch_library("https://floppy.example/", "token"))

    assert payload == [{"id": "x1"}]


def test_floppy_fetch_library_follows_pagination(monkeypatch):
    request = httpx.Request("GET", "https://floppy.example/api/v1/media/")
    first_page = httpx.Response(200, request=request, json={"results": [{"id": "x1"}], "next": "next-page"})
    second_page = httpx.Response(200, request=request, json={"results": [{"id": "x2"}], "next": None})
    empty_manga = httpx.Response(200, request=request, json={"results": [], "next": None})
    monkeypatch.setattr("app.providers.floppy.httpx.AsyncClient", lambda **kwargs: FakeAsyncClient())
    FakeAsyncClient.response_sequence = [first_page, second_page, empty_manga]

    payload = asyncio.run(FloppyProvider().fetch_library("https://floppy.example", "token"))

    assert payload == [{"id": "x1"}, {"id": "x2"}]


def test_floppy_fetch_library_reports_upstream_status(monkeypatch):
    request = httpx.Request("GET", "https://floppy.example/api/v1/media/")
    response = httpx.Response(502, request=request)
    FakeAsyncClient.response = response
    monkeypatch.setattr("app.providers.floppy.httpx.AsyncClient", lambda **kwargs: FakeAsyncClient())

    with pytest.raises(FloppyProviderError, match="Floppy API returned HTTP 502"):
        asyncio.run(FloppyProvider().fetch_library("https://floppy.example", "token"))


def test_floppy_fetch_library_rejects_unsupported_response(monkeypatch):
    request = httpx.Request("GET", "https://floppy.example/api/v1/media/")
    FakeAsyncClient.response = httpx.Response(200, request=request, json={"unexpected": []})
    monkeypatch.setattr("app.providers.floppy.httpx.AsyncClient", lambda **kwargs: FakeAsyncClient())

    with pytest.raises(FloppyProviderError, match="unsupported library response"):
        asyncio.run(FloppyProvider().fetch_library("https://floppy.example", "token"))


def test_floppy_fetch_library_reports_invalid_json(monkeypatch):
    request = httpx.Request("GET", "https://floppy.example/api/v1/media/")
    FakeAsyncClient.response = httpx.Response(200, request=request, content=b"not-json")
    monkeypatch.setattr("app.providers.floppy.httpx.AsyncClient", lambda **kwargs: FakeAsyncClient())

    with pytest.raises(FloppyProviderError, match="invalid JSON"):
        asyncio.run(FloppyProvider().fetch_library("https://floppy.example", "token"))


def test_floppy_fetch_library_reports_transport_failure(monkeypatch):
    FakeAsyncClient.error = httpx.ConnectError("connection refused")
    monkeypatch.setattr("app.providers.floppy.httpx.AsyncClient", lambda **kwargs: FakeAsyncClient())

    with pytest.raises(FloppyProviderError, match="Could not reach the Floppy API"):
        asyncio.run(FloppyProvider().fetch_library("https://floppy.example", "token"))

    FakeAsyncClient.error = None


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


def test_floppy_normalization_maps_real_manga_row_shape():
    normalized = FloppyProvider().normalize_library([
        {
            "item_id": "manga/mal/90160",
            "status": 1,
            "progress": 3209,
            "progress_unit": "chapters",
            "progress_scope": "entry",
            "score": 7,
            "item": {
                "media_id": "90160",
                "source": "mal",
                "library_media_type": "manga",
                "title": "Zui Wu Dao",
                "authors": [{"first_name": "Wu", "last_name": "Dao"}],
                "genres": ["Adventure"],
                "synopsis": "A martial arts story.",
                "provider_rating": 7.2,
            },
        }
    ])

    media, library = normalized[0]
    assert media.id == "floppy:mal:90160"
    assert media.title == "Zui Wu Dao"
    assert media.creator == "Wu Dao"
    assert media.source == "mal"
    assert media.source_id == "90160"
    assert media.media_type == "manga"
    assert library["progress"] == 3209
    assert library["progress_unit"] == "chapters"
    assert library["progress_percent"] is None


def test_floppy_completed_row_has_full_progress_percent():
    normalized = FloppyProvider().normalize_library([
        {
            "status": 3,
            "progress": 12,
            "max_progress": 100,
            "media_type": "comic",
            "media_id": "done",
            "item": {"title": "Done"},
        }
    ])

    assert normalized[0][1]["progress_percent"] == 100
