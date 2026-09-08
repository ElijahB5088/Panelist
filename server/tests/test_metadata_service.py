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


def test_covered_primary_uses_variant_cover_when_primary_is_missing_one():
    results = [
        MetadataResult("comicvine", "1", "Saga", image_url=None),
        MetadataResult("openlibrary", "OL1", "Saga", image_url="https://covers.example/saga.jpg"),
    ]
    providers = [NamedProvider("comicvine", []), NamedProvider("openlibrary", [])]

    group = group_metadata(results, providers)[0]

    assert covered_primary(group).source == "openlibrary"
