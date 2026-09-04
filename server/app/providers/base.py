from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import NormalizedMedia


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
