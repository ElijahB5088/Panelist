from app.providers.floppy import FloppyProvider


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
        {"media_id": "x2", "status": 2, "progress": 100, "item": {"title": "Done"}},
        {"media_id": "x3", "status": 5, "progress": 0, "item": {"title": "Queued"}},
    ])

    assert [library["status"] for _, library in normalized] == ["completed", "planned"]
