import httpx
import pytest

from app.providers.metadata import AniListProvider, ComicVineProvider, GCDProvider, MetronProvider, OpenLibraryProvider


@pytest.mark.anyio
async def test_comicvine_search_enriches_results_with_volume_credits(monkeypatch):
    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, params):
            if url.endswith("/search/"):
                return httpx.Response(
                    200,
                    json={"status_code": 1, "results": [{"id": 123, "name": "Saga", "api_detail_url": "https://example.test/volume/123"}]},
                    request=httpx.Request("GET", url),
                )
            return httpx.Response(
                200,
                json={"status_code": 1, "results": {"person_credits": [{"name": "Brian K. Vaughan"}]}},
                request=httpx.Request("GET", url),
            )

    monkeypatch.setattr("app.providers.metadata.httpx.AsyncClient", FakeClient)
    results = await ComicVineProvider("key").search("Saga", limit=1)

    assert results[0].creator == "Brian K. Vaughan"


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
            "person_credits": [{"name": "Brian K. Vaughan", "role": "writer"}],
        }
    )

    assert result.source == "comicvine"
    assert result.source_id == "123"
    assert result.publisher == "Image"
    assert result.release_date == "2012-01-01"
    assert result.image_url.endswith("saga.jpg")
    assert result.creator == "Brian K. Vaughan"


def test_comicvine_normalization_accepts_nested_author_credit():
    result = ComicVineProvider("key")._normalize(
        {
            "id": 456,
            "name": "Paper Girls",
            "authors": [{"author": {"name": "Brian K. Vaughan"}}],
        }
    )

    assert result.creator == "Brian K. Vaughan"


def test_comicvine_normalization_falls_back_when_person_credits_have_no_name():
    result = ComicVineProvider("key")._normalize(
        {
            "id": 789,
            "name": "Y: The Last Man",
            "person_credits": [{"role": "artist"}],
            "writers": [{"name": "Brian K. Vaughan"}],
        }
    )

    assert result.creator == "Brian K. Vaughan"


def test_comicvine_normalization_leaves_media_type_unresolved_and_rejects_placeholder_creator():
    result = ComicVineProvider("key")._normalize(
        {
            "id": 999,
            "name": "Hunter x Hunter",
            "start_year": 1998,
            "person_credits": [{"name": "comic", "role": "writer"}],
        }
    )

    assert result.media_type is None
    assert result.creator is None


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


def test_anilist_normalization_preserves_all_title_aliases():
    result = AniListProvider()._normalize(
        {
            "id": 790,
            "title": {
                "romaji": "Shingeki no Kyojin",
                "english": "Attack on Titan",
                "native": "進撃の巨人",
            },
            "synonyms": ["AOT", "Attack on Titan"],
        }
    )

    assert result.title == "Attack on Titan"
    assert result.aliases == ["Shingeki no Kyojin", "進撃の巨人", "AOT"]


@pytest.mark.parametrize("country", ["JP", "kr", "Cn"])
def test_anilist_normalization_preserves_manga_origin(country):
    result = AniListProvider()._normalize(
        {
            "id": 791,
            "title": {"romaji": "Example"},
            "countryOfOrigin": country,
        }
    )

    assert result.country_of_origin == country.upper()


def test_anilist_normalization_does_not_invent_missing_origin():
    result = AniListProvider()._normalize({"id": 792, "title": {"romaji": "Example"}})

    assert result.country_of_origin is None


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
            "creators": [{"name": "Brian K. Vaughan"}],
        }
    )

    assert result.source == "metron"
    assert result.source_id == "42"
    assert result.publisher == "Image"
    assert result.genres == ["Science Fiction"]
    assert result.release_date == "2012-01-01"
    assert result.image_url.endswith("saga.jpg")
    assert result.creator == "Brian K. Vaughan"


def test_gcd_series_normalization():
    result = GCDProvider()._normalize(
        {
            "api_url": "https://www.comics.org/api/series/7096/",
            "name": "Batman",
            "year_began": 1940,
        }
    )

    assert result.source == "gcd"
    assert result.source_id == "7096"
    assert result.title == "Batman"
    assert result.release_date == "1940-01-01"
    assert result.source_url == "https://www.comics.org/series/7096/"
    assert result.media_type == "comic"


@pytest.mark.anyio
async def test_gcd_search_enriches_results_with_issue_metadata(monkeypatch):
    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            if "/series/name/" in url:
                return httpx.Response(
                    200,
                    json={
                        "results": [
                            {
                                "api_url": "https://www.comics.org/api/series/7096/",
                                "name": "Batman",
                                "year_began": 1940,
                                "active_issues": [{"api_url": "https://www.comics.org/api/issue/1/"}],
                            }
                        ]
                    },
                    request=httpx.Request("GET", url),
                )
            return httpx.Response(
                200,
                json={
                    "results": {
                        "cover": "[https://images.example/batman.jpg](https://images.example/batman.jpg)",
                        "story_set": [{"synopsis": "The Dark Knight protects Gotham."}],
                    }
                },
                request=httpx.Request("GET", url),
            )

    monkeypatch.setattr("app.providers.metadata.httpx.AsyncClient", FakeClient)
    results = await GCDProvider().search("Batman", limit=1)

    assert results[0].image_url == "https://images.example/batman.jpg"
    assert results[0].description == "The Dark Knight protects Gotham."


@pytest.mark.anyio
async def test_gcd_search_keeps_series_when_issue_enrichment_fails(monkeypatch):
    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url):
            if "/series/name/" in url:
                return httpx.Response(
                    200,
                    json={
                        "results": [
                            {
                                "api_url": "https://www.comics.org/api/series/7096/",
                                "name": "Batman",
                                "active_issues": [{"api_url": "https://www.comics.org/api/issue/1/"}],
                            }
                        ]
                    },
                    request=httpx.Request("GET", url),
                )
            raise httpx.ConnectError("offline", request=httpx.Request("GET", url))

    monkeypatch.setattr("app.providers.metadata.httpx.AsyncClient", FakeClient)
    results = await GCDProvider().search("Batman", limit=1)

    assert len(results) == 1
    assert results[0].source_id == "7096"
    assert results[0].image_url is None
    assert results[0].description is None


def test_metadata_normalizers_mark_missing_ids_invalid():
    assert ComicVineProvider("key")._normalize({"name": "Missing"}).source_id == ""
    assert MetronProvider("https://metron.example/api", "token")._normalize({"series": "Missing"}).source_id == ""
    assert OpenLibraryProvider()._normalize({"title": "Missing"}).source_id == ""
    assert AniListProvider()._normalize({"title": {"romaji": "Missing"}}).source_id == ""
