from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict, defaultdict, deque

from .metadata import MetadataResult
from .providers.metadata import MetadataProvider

logger = logging.getLogger(__name__)


class MetadataRateLimitError(Exception):
    pass


class MetadataSearchService:
    def __init__(
        self,
        providers: list[MetadataProvider],
        cache_ttl_seconds: int = 900,
        cache_max_entries: int = 256,
        upstream_interval_seconds: float = 1.0,
        client_window_seconds: int = 60,
        client_max_requests: int = 30,
    ):
        self.providers = providers
        self.cache_ttl_seconds = cache_ttl_seconds
        self.cache_max_entries = cache_max_entries
        self.upstream_interval_seconds = upstream_interval_seconds
        self.client_window_seconds = client_window_seconds
        self.client_max_requests = client_max_requests
        self._cache: OrderedDict[tuple[str, int], tuple[float, list[MetadataResult]]] = OrderedDict()
        self._last_upstream_request: dict[str, float] = {}
        self._upstream_locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._client_requests: defaultdict[str, deque[float]] = defaultdict(deque)

    def check_client_limit(self, client_id: str) -> None:
        now = time.monotonic()
        requests = self._client_requests[client_id]
        while requests and now - requests[0] >= self.client_window_seconds:
            requests.popleft()
        if len(requests) >= self.client_max_requests:
            raise MetadataRateLimitError
        requests.append(now)

    async def search(self, query: str, limit: int = 10) -> list[MetadataResult]:
        normalized_query = " ".join(query.split()).casefold()
        cache_key = (normalized_query, limit)
        now = time.monotonic()
        cached = self._cache.get(cache_key)
        if cached and now - cached[0] < self.cache_ttl_seconds:
            self._cache.move_to_end(cache_key)
            return cached[1]
        if cached:
            del self._cache[cache_key]

        results: list[MetadataResult] = []
        for provider in self.providers:
            try:
                await self._wait_for_upstream(provider.name)
                results.extend(await provider.search(normalized_query, limit=limit))
            except Exception:
                logger.warning("Metadata provider %s failed for query %r", provider.name, normalized_query, exc_info=True)
                continue
        self._cache[cache_key] = (time.monotonic(), results)
        self._cache.move_to_end(cache_key)
        while len(self._cache) > self.cache_max_entries:
            self._cache.popitem(last=False)
        return results

    async def _wait_for_upstream(self, provider_name: str) -> None:
        async with self._upstream_locks[provider_name]:
            last_request = self._last_upstream_request.get(provider_name)
            if last_request is not None:
                delay = self.upstream_interval_seconds - (time.monotonic() - last_request)
                if delay > 0:
                    await asyncio.sleep(delay)
            self._last_upstream_request[provider_name] = time.monotonic()