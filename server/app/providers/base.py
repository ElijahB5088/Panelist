from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import NormalizedMedia


def valid_external_id(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized or normalized.casefold() in {"none", "null", "undefined"}:
        return None
    return normalized


class TrackingProvider(ABC):
    @abstractmethod
    async def test_connection(self, server_url: str, api_token: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def fetch_library(self, server_url: str, api_token: str) -> list[dict]:
        raise NotImplementedError

    @abstractmethod
    def normalize_library(self, payload: list[dict]) -> list[tuple[NormalizedMedia, dict]]:
        raise NotImplementedError
