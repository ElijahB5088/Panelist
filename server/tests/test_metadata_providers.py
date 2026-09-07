from app.providers.metadata import AniListProvider, ComicVineProvider, MetronProvider, OpenLibraryProvider


def test_comicvine_volume_normalization():
    result = ComicVineProvider("key")._normalize(
        {
            "id": 123,
            "name": "Saga",
            "deck": "A family in space.",
            "publisher": {"name": "Image"},
            "start_year": 2012,
            "image": {"original_url": "https://example.test/saga.jpg"},
            "site_detail_url": "https://comicvine.gamespot.com/saga/",
        }
    )

    assert result.source == "comicvine"
    assert result.source_id == "123"
    assert result.publisher == "Image"
    assert result.release_date == "2012-01-01"
    assert result.image_url.endswith("saga.jpg")


def test_openlibrary_normalization():
    result = OpenLibraryProvider()._normalize(
        {
            "key": "/works/OL123W",
            "title": "Graphic Novel",
            "author_name": ["A. Creator"],
            "publisher": ["Example Press"],
            "first_publish_year": 2020,
            "cover_i": 456,
        }
    )

    assert result.source == "openlibrary"
    assert result.source_id == "OL123W"
    assert result.creator == "A. Creator"
    assert result.image_url == "https://covers.openlibrary.org/b/id/456-L.jpg"


def test_anilist_normalization():
    result = AniListProvider()._normalize(
        {
            "id": 789,
            "title": {"romaji": "Manga", "english": None, "native": "漫画"},
            "genres": ["Drama"],
            "averageScore": 84,
            "startDate": {"year": 2021, "month": 4, "day": 2},
            "coverImage": {"large": "https://example.test/manga.jpg"},
            "siteUrl": "https://anilist.co/manga/789",
            "staff": {"edges": [{"node": {"name": {"full": "A. Mangaka"}}}]},
        }
    )

    assert result.source == "anilist"
    assert result.title == "Manga"
    assert result.creator == "A. Mangaka"
    assert result.rating == 8.4
    assert result.release_date == "2021-4-2"


def test_metron_series_normalization():
    result = MetronProvider("https://metron.example/api", "token")._normalize(
        {
            "id": 42,
            "series": "Saga",
            "year_began": 2012,
            "publisher": {"name": "Image"},
            "genres": [{"name": "Science Fiction"}],
            "desc": "A family in space.",
            "image": "https://images.example/saga.jpg",
            "resource_url": "https://metron.example/series/42/",
        }
    )

    assert result.source == "metron"
    assert result.source_id == "42"
    assert result.publisher == "Image"
    assert result.genres == ["Science Fiction"]
    assert result.release_date == "2012-01-01"
    assert result.image_url.endswith("saga.jpg")
