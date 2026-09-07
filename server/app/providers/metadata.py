from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from ..metadata import MetadataResult


class MetadataProvider(ABC):
    name: str

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[MetadataResult]:
        raise NotImplementedError


class ComicVineProvider(MetadataProvider):
    name = "comicvine"
    base_url = "https://comicvine.gamespot.com/api/search/"

    def __init__(self, api_key: str, user_agent: str = "Panelist/0.1"):
        self.api_key = api_key
        self.user_agent = user_agent

    async def search(self, query: str, limit: int = 10) -> list[MetadataResult]:
        if not self.api_key:
            return []
        params = {
            "api_key": self.api_key,
            "format": "json",
            "resources": "volume",
            "query": query,
            "limit": min(limit, 100),
            "field_list": "id,name,deck,description,publisher,start_year,image,site_detail_url",
        }
        headers = {"User-Agent": self.user_agent}
        async with httpx.AsyncClient(timeout=10, headers=headers) as client:
            response = await client.get(self.base_url, params=params)
        response.raise_for_status()
        payload = response.json()
        if payload.get("status_code") != 1:
            raise RuntimeError(payload.get("error", "Comic Vine request failed"))
        return [self._normalize(row) for row in payload.get("results", [])]

    def _normalize(self, row: dict) -> MetadataResult:
        publisher = row.get("publisher") or {}
        image = row.get("image") or {}
        year = row.get("start_year")
        return MetadataResult(
            source=self.name,
            source_id=str(row["id"]),
            title=row.get("name") or "Untitled",
            publisher=publisher.get("name"),
            description=row.get("description") or row.get("deck"),
            release_date=f"{year}-01-01" if year else None,
            image_url=image.get("original_url") or image.get("super_url"),
            source_url=row.get("site_detail_url"),
            media_type="comic",
        )


class MetronProvider(MetadataProvider):
    name = "metron"

    def __init__(self, api_url: str, token: str, user_agent: str = "Panelist/0.1"):
        self.api_url = api_url.rstrip("/")
        self.token = token
        self.user_agent = user_agent

    async def search(self, query: str, limit: int = 10) -> list[MetadataResult]:
        if not self.token:
            return []
        headers = {"Authorization": f"Bearer {self.token}", "User-Agent": self.user_agent}
        params = {"q": query, "page_size": min(limit, 100)}
        async with httpx.AsyncClient(timeout=10, headers=headers) as client:
            response = await client.get(f"{self.api_url}/series/", params=params)
        response.raise_for_status()
        payload = response.json()
        return [self._normalize(row) for row in payload.get("results", [])[:limit]]

    def _normalize(self, row: dict) -> MetadataResult:
        publisher = row.get("publisher") or {}
        year = row.get("year_began")
        source_id = str(row.get("id"))
        return MetadataResult(
            source=self.name,
            source_id=source_id,
            title=row.get("series") or row.get("name") or "Untitled",
            genres=[genre.get("name", genre) for genre in row.get("genres", []) if genre],
            publisher=publisher.get("name"),
            description=row.get("desc"),
            release_date=f"{year}-01-01" if year else None,
            image_url=row.get("image"),
            source_url=row.get("resource_url") or f"https://metron.cloud/series/{source_id}/",
            media_type="comic",
        )


class OpenLibraryProvider(MetadataProvider):
    name = "openlibrary"
    base_url = "https://openlibrary.org/search.json"

    def __init__(self, user_agent: str = "Panelist/0.1 (metadata@example.invalid)"):
        self.user_agent = user_agent

    async def search(self, query: str, limit: int = 10) -> list[MetadataResult]:
        params = {"q": query, "limit": min(limit, 100), "fields": "key,title,author_name,publisher,first_publish_year,cover_i"}
        headers = {"User-Agent": self.user_agent}
        async with httpx.AsyncClient(timeout=10, headers=headers) as client:
            response = await client.get(self.base_url, params=params)
        response.raise_for_status()
        return [self._normalize(row) for row in response.json().get("docs", [])]

    def _normalize(self, row: dict) -> MetadataResult:
        cover_id = row.get("cover_i")
        return MetadataResult(
            source=self.name,
            source_id=row.get("key", "").removeprefix("/works/"),
            title=row.get("title") or "Untitled",
            creator=(row.get("author_name") or [None])[0],
            publisher=(row.get("publisher") or [None])[0],
            release_date=f"{row['first_publish_year']}-01-01" if row.get("first_publish_year") else None,
            image_url=f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else None,
            source_url=f"https://openlibrary.org{row['key']}" if row.get("key") else None,
            media_type="comic",
        )


class AniListProvider(MetadataProvider):
    name = "anilist"
    base_url = "https://graphql.anilist.co"
    query_document = """
    query ($search: String!, $perPage: Int!) {
      Page(perPage: $perPage) {
        media(search: $search, type: MANGA) {
          id title { romaji english native } description averageScore startDate { year month day }
          coverImage { large } genres siteUrl
          staff(perPage: 3) { edges { node { name { full } } } }
        }
      }
    }
    """

    async def search(self, query: str, limit: int = 10) -> list[MetadataResult]:
        payload = {"query": self.query_document, "variables": {"search": query, "perPage": min(limit, 50)}}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(self.base_url, json=payload)
        response.raise_for_status()
        body = response.json()
        if body.get("errors"):
            raise RuntimeError(body["errors"][0].get("message", "AniList request failed"))
        return [self._normalize(row) for row in body.get("data", {}).get("Page", {}).get("media", [])]

    def _normalize(self, row: dict) -> MetadataResult:
        title = row.get("title") or {}
        start_date = row.get("startDate") or {}
        date_parts = [str(start_date[key]) for key in ("year", "month", "day") if start_date.get(key)]
        staff = row.get("staff", {}).get("edges", [])
        return MetadataResult(
            source=self.name,
            source_id=str(row["id"]),
            title=title.get("english") or title.get("romaji") or title.get("native") or "Untitled",
            creator=(staff[0].get("node", {}).get("name", {}).get("full") if staff else None),
            genres=row.get("genres") or [],
            description=row.get("description"),
            rating=(row.get("averageScore") / 10) if row.get("averageScore") else None,
            release_date="-".join(date_parts) if date_parts else None,
            image_url=(row.get("coverImage") or {}).get("large"),
            source_url=row.get("siteUrl"),
            media_type="manga",
        )