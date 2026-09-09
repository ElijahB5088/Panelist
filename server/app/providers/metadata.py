from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
import re
from urllib.parse import quote, urlparse

import httpx

from ..metadata import MetadataResult
from .base import valid_external_id


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
            "field_list": "id,name,deck,description,publisher,start_year,image,site_detail_url,api_detail_url,person_credits",
        }
        headers = {"User-Agent": self.user_agent}
        async with httpx.AsyncClient(timeout=10, headers=headers) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            payload = response.json()
            rows = await asyncio.gather(*(self._with_details(client, row) for row in payload.get("results", [])))
        if payload.get("status_code") != 1:
            raise RuntimeError(payload.get("error", "Comic Vine request failed"))
        return [result for result in (self._normalize(row) for row in rows) if valid_external_id(result.source_id)]

    async def _with_details(self, client: httpx.AsyncClient, row: dict) -> dict:
        if row.get("person_credits") or not row.get("api_detail_url"):
            return row
        response = await client.get(
            row["api_detail_url"],
            params={
                "api_key": self.api_key,
                "format": "json",
                "field_list": "id,name,deck,description,publisher,start_year,image,site_detail_url,api_detail_url,person_credits",
            },
        )
        response.raise_for_status()
        detail = response.json()
        if detail.get("status_code") != 1:
            return row
        return {**row, **(detail.get("results") or {})}

    def _normalize(self, row: dict) -> MetadataResult:
        publisher = row.get("publisher") or {}
        image = row.get("image") or {}
        year = row.get("start_year")
        credits = [
            credit
            for field in ("person_credits", "credits", "authors", "writers")
            for credit in (row.get(field) or [])
        ]

        def credit_name(credit: object) -> str | None:
            if isinstance(credit, str):
                return credit.strip() or None
            if not isinstance(credit, dict):
                return None
            for key in ("name", "person", "creator", "author", "writer"):
                value = credit.get(key)
                if isinstance(value, str) and value:
                    return value.strip() or None
                if isinstance(value, dict):
                    name = value.get("name")
                    if isinstance(name, str) and name:
                        return name.strip() or None
            return None

        creator = next(
            (
                name
                for name in (credit_name(credit) for credit in credits)
                if name and name.casefold() not in {"comic", "comics", "manga", "unknown", "n/a"}
            ),
            None,
        )
        return MetadataResult(
            source=self.name,
            source_id=valid_external_id(row.get("id")) or "",
            title=row.get("name") or "Untitled",
            creator=creator,
            publisher=publisher.get("name"),
            description=row.get("description") or row.get("deck"),
            release_date=f"{year}-01-01" if year else None,
            image_url=image.get("original_url") or image.get("super_url"),
            source_url=row.get("site_detail_url"),
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
        return [
            result
            for result in (self._normalize(row) for row in payload.get("results", [])[:limit])
            if valid_external_id(result.source_id)
        ]

    def _normalize(self, row: dict) -> MetadataResult:
        publisher = row.get("publisher") or {}
        year = row.get("year_began")
        source_id = valid_external_id(row.get("id")) or ""
        credits = row.get("creators") or row.get("credits") or []
        creator = next(
            (
                credit.get("name")
                or (credit.get("creator") or {}).get("name")
                or (credit.get("person") or {}).get("name")
                for credit in credits
                if isinstance(credit, dict)
                and (
                    credit.get("name")
                    or (credit.get("creator") or {}).get("name")
                    or (credit.get("person") or {}).get("name")
                )
            ),
            None,
        )
        return MetadataResult(
            source=self.name,
            source_id=source_id,
            title=row.get("series") or row.get("name") or "Untitled",
            creator=creator,
            genres=[genre.get("name", genre) for genre in row.get("genres", []) if genre],
            publisher=publisher.get("name"),
            description=row.get("desc"),
            release_date=f"{year}-01-01" if year else None,
            image_url=row.get("image"),
            source_url=row.get("resource_url") or f"https://metron.cloud/series/{source_id}/",
        )


class GCDProvider(MetadataProvider):
    name = "gcd"
    base_url = "https://www.comics.org/api"

    def __init__(self, user_agent: str = "Panelist/0.1"):
        self.user_agent = user_agent

    async def search(self, query: str, limit: int = 10) -> list[MetadataResult]:
        if not query.strip() or limit <= 0:
            return []
        path_query = quote(query.strip(), safe="")
        headers = {"Accept": "application/json", "User-Agent": self.user_agent}
        async with httpx.AsyncClient(timeout=10, headers=headers) as client:
            response = await client.get(f"{self.base_url}/series/name/{path_query}/")
            response.raise_for_status()
            payload = response.json()
            rows = payload.get("results", []) if isinstance(payload, dict) else payload
            rows = await asyncio.gather(
                *(self._with_issue_details(client, row) for row in rows[:limit] if isinstance(row, dict))
            )
        return [
            result
            for result in (
                self._normalize(row)
                for row in rows[:limit]
                if isinstance(row, dict)
            )
            if valid_external_id(result.source_id)
        ]

    async def _with_issue_details(self, client: httpx.AsyncClient, row: dict) -> dict:
        active_issues = row.get("active_issues") or []
        issue_url = next(
            (
                issue.get("api_url") or issue.get("resource_url")
                if isinstance(issue, dict)
                else issue
                for issue in active_issues
                if (isinstance(issue, dict) and (issue.get("api_url") or issue.get("resource_url")))
                or isinstance(issue, str)
            ),
            None,
        )
        if not issue_url:
            return row
        try:
            response = await client.get(issue_url)
            response.raise_for_status()
            issue = response.json()
            if isinstance(issue, dict) and isinstance(issue.get("results"), dict):
                issue = issue["results"]
            if not isinstance(issue, dict):
                return row
            description = next(
                (
                    story.get("synopsis")
                    for story in (issue.get("story_set") or issue.get("stories") or [])
                    if isinstance(story, dict) and story.get("synopsis")
                ),
                None,
            )
            return {
                **row,
                "description": description or issue.get("notes") or row.get("notes"),
                "image_url": self._cover_url(issue.get("cover")),
            }
        except Exception:
            return row

    @staticmethod
    def _cover_url(value: object) -> str | None:
        if isinstance(value, dict):
            value = value.get("url") or value.get("image_url")
        if not isinstance(value, str):
            return None
        markdown_match = re.search(r"\]\((https?://[^)]+)\)", value)
        if markdown_match:
            return markdown_match.group(1).rstrip(".,")
        match = re.search(r"https?://[^\s)\]]+", value)
        return match.group(0).rstrip(".,") if match else None

    def _normalize(self, row: dict) -> MetadataResult:
        api_url = row.get("api_url") or row.get("resource_url")
        source_id = self._source_id(api_url)
        source_url = row.get("url") or self._public_url(api_url, source_id)
        year = row.get("year_began")
        return MetadataResult(
            source=self.name,
            source_id=source_id,
            title=row.get("name") or "Untitled",
            description=row.get("description") or row.get("notes"),
            release_date=f"{year}-01-01" if year else None,
            image_url=row.get("image_url"),
            source_url=source_url,
            media_type="comic",
        )

    @staticmethod
    def _source_id(api_url: str | None) -> str:
        if not api_url:
            return ""
        match = re.search(r"/series/(\d+)/?", urlparse(api_url).path)
        return match.group(1) if match else ""

    @staticmethod
    def _public_url(api_url: str | None, source_id: str) -> str | None:
        if api_url:
            parsed = urlparse(api_url)
            return f"{parsed.scheme}://{parsed.netloc}/series/{source_id}/" if source_id else api_url
        return f"https://www.comics.org/series/{source_id}/" if source_id else None


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
        return [
            result
            for result in (self._normalize(row) for row in response.json().get("docs", []))
            if valid_external_id(result.source_id)
        ]

    def _normalize(self, row: dict) -> MetadataResult:
        cover_id = row.get("cover_i")
        return MetadataResult(
            source=self.name,
            source_id=valid_external_id(row.get("key", "").removeprefix("/works/")) or "",
            title=row.get("title") or "Untitled",
            creator=(row.get("author_name") or [None])[0],
            publisher=(row.get("publisher") or [None])[0],
            release_date=f"{row['first_publish_year']}-01-01" if row.get("first_publish_year") else None,
            image_url=f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else None,
            source_url=f"https://openlibrary.org{row['key']}" if row.get("key") else None,
        )


class AniListProvider(MetadataProvider):
    name = "anilist"
    base_url = "https://graphql.anilist.co"
    query_document = """
    query ($search: String!, $perPage: Int!) {
      Page(perPage: $perPage) {
        media(search: $search, type: MANGA) {
          id title { romaji english native } synonyms description averageScore startDate { year month day }
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
        return [
            result
            for result in (self._normalize(row) for row in body.get("data", {}).get("Page", {}).get("media", []))
            if valid_external_id(result.source_id)
        ]

    def _normalize(self, row: dict) -> MetadataResult:
        title = row.get("title") or {}
        display_title = title.get("english") or title.get("romaji") or title.get("native") or "Untitled"
        aliases = list(
            dict.fromkeys(
                value
                for value in [
                    title.get("romaji"),
                    title.get("english"),
                    title.get("native"),
                    *(row.get("synonyms") or []),
                ]
                if value and value != display_title
            )
        )
        start_date = row.get("startDate") or {}
        date_parts = [str(start_date[key]) for key in ("year", "month", "day") if start_date.get(key)]
        staff = row.get("staff", {}).get("edges", [])
        return MetadataResult(
            source=self.name,
            source_id=valid_external_id(row.get("id")) or "",
            title=display_title,
            creator=(staff[0].get("node", {}).get("name", {}).get("full") if staff else None),
            genres=row.get("genres") or [],
            description=row.get("description"),
            rating=(row.get("averageScore") / 10) if row.get("averageScore") else None,
            release_date="-".join(date_parts) if date_parts else None,
            image_url=(row.get("coverImage") or {}).get("large"),
            source_url=row.get("siteUrl"),
            aliases=aliases,
        )