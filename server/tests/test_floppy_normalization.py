from app.providers.floppy import FloppyProvider


def test_floppy_normalization():
    provider = FloppyProvider()
    payload = [
        {
            "status": "reading",
            "progress": 42,
            "rating": 5,
            "media": {
                "id": "x1",
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
