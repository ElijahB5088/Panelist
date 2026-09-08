from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from collections import OrderedDict, defaultdict, deque

from .metadata import MetadataGroup, MetadataResult
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

    async def grouped_search(
        self,
        query: str,
        limit: int = 10,
        preferred_source: str | None = None,
    ) -> list[MetadataGroup]:
        results = await self.search(query, limit=limit)
        return group_metadata(results, self.providers, preferred_source=preferred_source)

    async def _wait_for_upstream(self, provider_name: str) -> None:
        async with self._upstream_locks[provider_name]:
            last_request = self._last_upstream_request.get(provider_name)
            if last_request is not None:
                delay = self.upstream_interval_seconds - (time.monotonic() - last_request)
                if delay > 0:
                    await asyncio.sleep(delay)
            self._last_upstream_request[provider_name] = time.monotonic()


def group_metadata(
    results: list[MetadataResult],
    providers: list[MetadataProvider],
    preferred_source: str | None = None,
) -> list[MetadataGroup]:
    provider_order = {provider.name: index for index, provider in enumerate(providers)}
    groups: dict[str, list[MetadataResult]] = {}
    order: list[str] = []
    for result in results:
        key = _metadata_group_key(result)
        if key not in groups:
            groups[key] = []
            order.append(key)
        if not any(
            variant.source == result.source and variant.source_id == result.source_id
            for variant in groups[key]
        ):
            groups[key].append(result)

    grouped = []
    for key in order:
        variants = groups[key]
        variants.sort(key=lambda item: (provider_order.get(item.source, len(provider_order)), item.source, item.source_id))
        primary = next(
            (variant for variant in variants if variant.source == preferred_source),
            variants[0],
        )
        group_id = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
        grouped.append(MetadataGroup(group_id=group_id, primary=primary, variants=variants))
    return grouped


def covered_primary(group: MetadataGroup) -> MetadataResult:
    if group.primary.image_url and group.primary.image_url.strip():
        return group.primary
    return next(
        (variant for variant in group.variants if variant.image_url and variant.image_url.strip()),
        group.primary,
    )


def _metadata_group_key(result: MetadataResult) -> str:
    title = _normalize_identity(result.title)
    creator = _normalize_identity(result.creator or "")
    year = (result.release_date or "")[:4]
    return "|".join((title, creator, year))


def _normalize_identity(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()