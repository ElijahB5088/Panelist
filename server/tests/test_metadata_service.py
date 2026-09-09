import asyncio

import pytest

from app.metadata import MetadataResult
from app.metadata_service import MetadataRateLimitError, MetadataSearchService, covered_primary, group_metadata
from app.providers.metadata import MetadataProvider


class FakeProvider(MetadataProvider):
    name = "fake"

    def __init__(self):
        self.calls = 0

    async def search(self, query: str, limit: int = 10) -> list[MetadataResult]:
        self.calls += 1
        return [MetadataResult(self.name, str(self.calls), query)]


class NamedProvider(MetadataProvider):
    def __init__(self, name: str, results: list[MetadataResult]):
        self.name = name
        self.results = results

    async def search(self, query: str, limit: int = 10) -> list[MetadataResult]:
        return self.results


def test_metadata_search_caches_normalized_query():
    provider = FakeProvider()
    service = MetadataSearchService([provider], upstream_interval_seconds=0, cache_ttl_seconds=60)

    async def run():
        first = await service.search("  Saga ", limit=5)
        second = await service.search("saga", limit=5)
        return first, second

    first, second = asyncio.run(run())
    assert provider.calls == 1
    assert first == second


def test_metadata_search_evicts_oldest_entry():
    provider = FakeProvider()
    service = MetadataSearchService([provider], upstream_interval_seconds=0, cache_max_entries=1)

    async def run():
        await service.search("first")
        await service.search("second")
        await service.search("first")

    asyncio.run(run())
    assert provider.calls == 3


def test_metadata_client_limit_raises_after_window_is_full():
    service = MetadataSearchService([], client_window_seconds=60, client_max_requests=2)

    service.check_client_limit("client")
    service.check_client_limit("client")
    with pytest.raises(MetadataRateLimitError):
        service.check_client_limit("client")


def test_authoritative_manga_match_requires_unambiguous_identity():
    provider = NamedProvider(
        "anilist",
        [MetadataResult("anilist", "hxh", "Hunter x Hunter", "Yoshihiro Togashi", release_date="1998-03-16", media_type="manga")],
    )
    service = MetadataSearchService([provider], upstream_interval_seconds=0)

    async def run():
        return await service.authoritative_manga_match(
            "Hunter x Hunter",
            release_date="1998-01-01",
        )

    result = asyncio.run(run())
    assert result is provider.results[0]


def test_authoritative_manga_match_rejects_title_only_identity():
    provider = NamedProvider(
        "anilist",
        [MetadataResult("anilist", "unknown", "Common Title", media_type="manga")],
    )
    service = MetadataSearchService([provider], upstream_interval_seconds=0)

    async def run():
        return await service.authoritative_manga_match("Common Title")

    assert asyncio.run(run()) is None


def test_authoritative_manga_match_accepts_title_only_asian_origin():
    provider = NamedProvider(
        "anilist",
        [
            MetadataResult(
                "anilist",
                "jp-1",
                "Japanese Title",
                country_of_origin="JP",
                media_type="manga",
            )
        ],
    )
    service = MetadataSearchService([provider], upstream_interval_seconds=0)

    async def run():
        return await service.authoritative_manga_match("Japanese Title")

    result = asyncio.run(run())
    assert result.source_id == "jp-1"
    assert result.media_type == "manga"


@pytest.mark.parametrize(
    ("origin", "expected_type"),
    [("KR", "manhwa"), ("CN", "manhua")],
)
def test_authoritative_manga_match_preserves_asian_subtype(origin, expected_type):
    provider = NamedProvider(
        "anilist",
        [MetadataResult("anilist", "1", "Common Title", country_of_origin=origin, media_type="manga")],
    )
    service = MetadataSearchService([provider], upstream_interval_seconds=0)

    async def run():
        return await service.authoritative_manga_match("Common Title")

    assert asyncio.run(run()).media_type == expected_type


def test_authoritative_manga_match_rejects_title_only_western_origin():
    provider = NamedProvider(
        "anilist",
        [
            MetadataResult(
                "anilist",
                "us-1",
                "Western Title",
                country_of_origin="US",
                media_type="manga",
            )
        ],
    )
    service = MetadataSearchService([provider], upstream_interval_seconds=0)

    async def run():
        return await service.authoritative_manga_match("Western Title")

    assert asyncio.run(run()) is None


def test_authoritative_manga_match_rejects_ambiguous_or_conflicting_results():
    provider = NamedProvider(
        "anilist",
        [
            MetadataResult("anilist", "one", "One Piece", "Eiichiro Oda", release_date="1997-07-22", media_type="manga"),
            MetadataResult("anilist", "two", "One Piece", "Different Creator", release_date="1997-07-22", media_type="manga"),
        ],
    )
    service = MetadataSearchService([provider], upstream_interval_seconds=0)

    async def run():
        return await service.authoritative_manga_match("One Piece", release_date="1997-01-01")

    assert asyncio.run(run()) is None


def test_authoritative_manga_match_accepts_anilist_title_alias():
    provider = NamedProvider(
        "anilist",
        [
            MetadataResult(
                "anilist",
                "790",
                "Attack on Titan",
                "Hajime Isayama",
                release_date="2009-04-01",
                aliases=["Shingeki no Kyojin", "進撃の巨人"],
            )
        ],
    )
    service = MetadataSearchService([provider], upstream_interval_seconds=0)

    async def run():
        return await service.authoritative_manga_match(
            "進撃の巨人",
            creator="Hajime Isayama",
            release_date="2009-01-01",
        )

    assert asyncio.run(run()).source_id == "790"


def test_authoritative_manga_match_accepts_equivalent_provider_results():
    providers = [
        NamedProvider(
            "anilist",
            [MetadataResult("anilist", "790", "Attack on Titan", "Hajime Isayama", release_date="2009-04-01")],
        ),
        NamedProvider(
            "kitsu",
            [MetadataResult("kitsu", "k-790", "Shingeki no Kyojin", "Hajime Isayama", release_date="2009-04-01")],
        ),
    ]
    providers[1].results[0].aliases = ["Attack on Titan"]
    service = MetadataSearchService(providers, upstream_interval_seconds=0)

    async def run():
        return await service.authoritative_manga_match(
            "Attack on Titan",
            creator="Hajime Isayama",
            release_date="2009-01-01",
        )

    assert asyncio.run(run()).source_id == "790"


def test_group_metadata_collapses_equivalent_provider_results_and_keeps_variants():
    results = [
        MetadataResult("comicvine", "1", "Saga", "Brian K. Vaughan", release_date="2012-03-14"),
        MetadataResult("openlibrary", "OL1", "Saga!", "Brian K. Vaughan", release_date="2012-01-01"),
        MetadataResult("anilist", "2", "Saga", "Different Creator", release_date="2012-03-14"),
    ]

    providers = [NamedProvider("comicvine", []), NamedProvider("openlibrary", []), NamedProvider("anilist", [])]
    groups = group_metadata(results, providers)

    assert len(groups) == 2
    assert groups[0].group_id
    assert [(variant.source, variant.source_id) for variant in groups[0].variants] == [("comicvine", "1"), ("openlibrary", "OL1")]
    assert groups[0].primary.source == "comicvine"


def test_group_metadata_prefers_requested_source_when_available():
    results = [
        MetadataResult("comicvine", "1", "Saga", "Brian K. Vaughan"),
        MetadataResult("openlibrary", "OL1", "Saga", "Brian K. Vaughan"),
    ]

    providers = [NamedProvider("comicvine", []), NamedProvider("openlibrary", [])]
    groups = group_metadata(results, providers, preferred_source="openlibrary")

    assert groups[0].primary.source == "openlibrary"


def test_group_metadata_keeps_provider_type_fallbacks_separate():
    results = [
        MetadataResult("comicvine", "comic-1", "Saga", "Creator"),
        MetadataResult("anilist", "manga-1", "Saga", "Creator"),
    ]
    providers = [NamedProvider("comicvine", []), NamedProvider("anilist", [])]

    groups = group_metadata(results, providers)

    assert len(groups) == 2


def test_group_metadata_promotes_matching_comicvine_manga_from_tracker():
    results = [
        MetadataResult("comicvine", "comic-1", "Hunter x Hunter", release_date="1998-03-16"),
        MetadataResult(
            "anilist",
            "manga-1",
            "Hunter x Hunter",
            "Yoshihiro Togashi",
            release_date="1998-03-16",
        ),
    ]
    providers = [NamedProvider("comicvine", []), NamedProvider("anilist", [])]

    groups = group_metadata(results, providers)

    assert len(groups) == 1
    assert groups[0].primary.media_type == "manga"
    assert groups[0].primary.creator == "Yoshihiro Togashi"


def test_covered_primary_uses_variant_cover_when_primary_is_missing_one():
    results = [
        MetadataResult("comicvine", "1", "Saga", image_url=None),
        MetadataResult("openlibrary", "OL1", "Saga", image_url="https://covers.example/saga.jpg"),
    ]
    providers = [NamedProvider("comicvine", []), NamedProvider("openlibrary", [])]

    group = group_metadata(results, providers)[0]

    assert covered_primary(group).source == "openlibrary"
