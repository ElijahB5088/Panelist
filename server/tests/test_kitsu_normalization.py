from app.providers.kitsu import KitsuProvider


def test_kitsu_api_paths_and_base_url():
    provider = KitsuProvider()

    assert provider._base_url("https://kitsu.io") == "https://kitsu.io/api/edge"
    assert provider._base_url("https://kitsu.io/api/edge") == "https://kitsu.io/api/edge"


def test_kitsu_normalization_is_manga_only():
    provider = KitsuProvider()
    payload = [
        {
            "type": "manga",
            "manga": {
                "id": "42",
                "type": "manga",
                "attributes": {
                    "canonicalTitle": "Witch Hat Atelier",
                    "authors": [{"name": "Kamome Shirahama"}],
                    "averageRating": "88.5",
                    "genres": ["Fantasy"],
                    "posterImage": {"large": "https://example.test/witch-hat.jpg"},
                },
            },
            "status": "current",
            "progress": 7,
            "rating": 5,
        },
        {
            "type": "anime",
            "manga": {"id": "99", "type": "anime", "attributes": {"canonicalTitle": "Anime"}},
            "status": "current",
        },
    ]

    normalized = provider.normalize_library(payload)

    assert len(normalized) == 1
    media, library = normalized[0]
    assert media.id == "kitsu:42"
    assert media.title == "Witch Hat Atelier"
    assert media.creator == "Kamome Shirahama"
    assert media.rating == 88.5
    assert media.media_type == "manga"
    assert media.image_url == "https://example.test/witch-hat.jpg"
    assert library == {"status": "reading", "progress": 7, "user_rating": 5.0}


def test_kitsu_expands_json_api_included_manga():
    payload = {
        "data": [
            {
                "type": "libraryEntries",
                "id": "entry-1",
                "attributes": {"status": "completed", "progress": 100},
                "relationships": {"manga": {"data": {"type": "manga", "id": "42"}}},
            }
        ],
        "included": [
            {"type": "manga", "id": "42", "attributes": {"canonicalTitle": "X"}}
        ],
    }

    assert KitsuProvider._expand_included(payload)[0]["manga"]["id"] == "42"
