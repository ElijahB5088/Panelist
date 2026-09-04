import asyncio

import pytest

from app.metadata import MetadataResult
from app.metadata_service import MetadataRateLimitError, MetadataSearchService
from app.providers.metadata import MetadataProvider


class FakeProvider(MetadataProvider):
    name = "fake"

    def __init__(self):
        self.calls = 0

    async def search(self, query: str, limit: int = 10) -> list[MetadataResult]:
        self.calls += 1
        return [MetadataResult(self.name, str(self.calls), query)]


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
