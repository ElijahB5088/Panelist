from __future__ import annotations

from contextlib import asynccontextmanager
import httpx
import sqlite3
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from .db import get_conn, run_migrations
from .config import settings
from .metadata_service import MetadataRateLimitError, MetadataSearchService
from .providers.metadata import AniListProvider, ComicVineProvider, MetronProvider, OpenLibraryProvider
from .providers.floppy import FloppyProvider
from .recommendation import build_recommendations
from .security import (
    decrypt_secret,
    encrypt_secret,
    hash_password,
    issue_token,
    now_iso,
    verify_password,
)

conn = get_conn()
run_migrations(conn)
provider = FloppyProvider()
metadata_providers = [
    ComicVineProvider(settings.comicvine_api_key, settings.metadata_user_agent),
    MetronProvider(settings.metron_api_url, settings.metron_api_token, settings.metadata_user_agent),
    OpenLibraryProvider(settings.metadata_user_agent),
    AniListProvider(),
]
metadata_service = MetadataSearchService(
    metadata_providers,
    cache_ttl_seconds=settings.metadata_cache_ttl_seconds,
    cache_max_entries=settings.metadata_cache_max_entries,
    upstream_interval_seconds=settings.metadata_upstream_interval_seconds,
    client_window_seconds=settings.metadata_client_window_seconds,
    client_max_requests=settings.metadata_client_max_requests,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    run_migrations(conn)
    conn.execute(
        """
        INSERT OR IGNORE INTO media (id, title, creator, genres, publisher, description, rating, popularity, release_date)
        VALUES
          ('saga', 'Saga', 'Brian K. Vaughan', 'science-fiction,space-opera,drama', 'Image', 'Epic sci-fi family saga', 4.8, 95, '2012-03-14'),
          ('monstress', 'Monstress', 'Marjorie Liu', 'fantasy,dark-fantasy,drama', 'Image', 'Dark fantasy series', 4.7, 90, '2015-11-03'),
          ('descender', 'Descender', 'Jeff Lemire', 'science-fiction,adventure', 'Image', 'Sci-fi robot odyssey', 4.6, 88, '2015-03-04')
        """
    )
    conn.commit()
    yield


app = FastAPI(title="Panelist Server", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


def _metadata_response(result):
    return {
        "source": result.source,
        "source_id": result.source_id,
        "title": result.title,
        "creator": result.creator,
        "genres": result.genres or [],
        "publisher": result.publisher,
        "description": result.description,
        "rating": result.rating,
        "release_date": result.release_date,
        "image_url": result.image_url,
        "source_url": result.source_url,
    }


def _metadata_group_response(group):
    return {
        "id": group.group_id,
        "primary": _metadata_response(group.primary),
        "variants": [_metadata_response(result) for result in group.variants],
    }


class Credentials(BaseModel):
    username: str = Field(min_length=3)
    password: str = Field(min_length=6)


class FloppyConfig(BaseModel):
    server_url: str
    api_token: str


def user_from_auth(authorization: str | None = Header(default=None)):
    auth = authorization
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing auth token")
    token = auth.removeprefix("Bearer ").strip()
    row = conn.execute(
        "SELECT u.id, u.username FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token = ?",
        (token,),
    ).fetchone()
    if not row:
        raise HTTPException(401, "Invalid auth token")
    return {"id": row[0], "username": row[1], "token": token}


@app.post("/api/auth/register")
def register(body: Credentials):
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (body.username, hash_password(body.password)),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        raise HTTPException(400, "Username already exists") from exc
    return {"ok": True}


@app.post("/api/auth/login")
def login(body: Credentials):
    row = conn.execute("SELECT id, password_hash FROM users WHERE username = ?", (body.username,)).fetchone()
    if not row or not verify_password(body.password, row[1]):
        raise HTTPException(401, "Invalid credentials")
    token = issue_token()
    conn.execute("INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)", (token, row[0], now_iso()))
    conn.commit()
    return {"access_token": token}


@app.post("/api/auth/refresh")
def refresh(user=Depends(user_from_auth)):
    new_token = issue_token()
    conn.execute("DELETE FROM sessions WHERE token = ?", (user["token"],))
    conn.execute("INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)", (new_token, user["id"], now_iso()))
    conn.commit()
    return {"access_token": new_token}


@app.get("/api/me")
def me(user=Depends(user_from_auth)):
    return {"id": user["id"], "username": user["username"]}


@app.get("/api/profile")
def profile(user=Depends(user_from_auth)):
    integration = conn.execute(
        "SELECT provider, server_url, connected, last_sync_at, sync_status, sync_error FROM tracker_integrations WHERE user_id = ?",
        (user["id"],),
    ).fetchone()
    return {
        "user": {"id": user["id"], "username": user["username"]},
        "connected_tracker": {
            "provider": integration[0],
            "server_url": integration[1],
            "connected": bool(integration[2]),
            "last_sync": integration[3],
            "sync_status": integration[4],
            "sync_error": integration[5],
        }
        if integration
        else None,
    }


@app.post("/api/integrations/floppy/test")
async def test_floppy(body: FloppyConfig, user=Depends(user_from_auth)):
    try:
        ok = await provider.test_connection(body.server_url, body.api_token)
    except httpx.HTTPStatusError as exc:
        response = exc.response
        detail = response.text[:240] or response.reason_phrase
        return {
            "connected": False,
            "server_url": body.server_url,
            "error": f"Floppy returned HTTP {response.status_code}: {detail}",
        }
    except httpx.HTTPError as exc:
        detail = str(exc) or type(exc).__name__
        raise HTTPException(502, f"Could not reach Floppy at {body.server_url}: {detail}") from exc
    return {"connected": ok, "server_url": body.server_url}


@app.post("/api/integrations/floppy")
def connect_floppy(body: FloppyConfig, user=Depends(user_from_auth)):
    conn.execute(
        """
        INSERT INTO tracker_integrations (user_id, provider, server_url, encrypted_token, connected, sync_status)
        VALUES (?, 'floppy', ?, ?, 1, 'idle')
        ON CONFLICT(user_id) DO UPDATE SET
          provider='floppy', server_url=excluded.server_url,
          encrypted_token=excluded.encrypted_token, connected=1
        """,
        (user["id"], body.server_url, encrypt_secret(body.api_token)),
    )
    conn.commit()
    return {"connected": True, "server_url": body.server_url}


@app.delete("/api/integrations/floppy")
def disconnect_floppy(user=Depends(user_from_auth)):
    conn.execute("DELETE FROM tracker_integrations WHERE user_id = ?", (user["id"],))
    conn.commit()
    return {"ok": True}


@app.post("/api/sync")
async def sync(user=Depends(user_from_auth)):
    row = conn.execute("SELECT server_url, encrypted_token FROM tracker_integrations WHERE user_id = ?", (user["id"],)).fetchone()
    if not row:
        raise HTTPException(400, "Floppy is not connected")

    conn.execute(
        "UPDATE tracker_integrations SET sync_status='syncing', sync_error=NULL WHERE user_id = ?",
        (user["id"],),
    )
    conn.commit()

    try:
        payload = await provider.fetch_library(row[0], decrypt_secret(row[1]))
        normalized = provider.normalize_library(payload)
        conn.execute("DELETE FROM user_library WHERE user_id = ?", (user["id"],))
        for media, lib in normalized:
            conn.execute(
                """
                INSERT INTO media (id, title, creator, genres, publisher, description, rating)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  title=excluded.title, creator=excluded.creator, genres=excluded.genres,
                  publisher=excluded.publisher, description=excluded.description, rating=excluded.rating
                """,
                (
                    media.id,
                    media.title,
                    media.creator,
                    ",".join(media.genres),
                    media.publisher,
                    media.description,
                    media.rating,
                ),
            )
            conn.execute(
                """
                INSERT INTO user_library (user_id, media_id, status, progress, user_rating)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, media_id) DO UPDATE SET
                  status=excluded.status, progress=excluded.progress, user_rating=excluded.user_rating
                """,
                (user["id"], media.id, lib["status"], lib["progress"], lib["user_rating"]),
            )

        conn.execute(
            "UPDATE tracker_integrations SET last_sync_at=?, sync_status='idle' WHERE user_id = ?",
            (now_iso(), user["id"]),
        )
        conn.commit()
    except Exception as exc:
        conn.execute(
            "UPDATE tracker_integrations SET sync_status='error', sync_error=? WHERE user_id = ?",
            (str(exc)[:240], user["id"]),
        )
        conn.commit()
        raise HTTPException(502, "Sync failed") from exc

    return {"ok": True, "status": "syncing your library..."}


@app.get("/api/sync/status")
def sync_status(user=Depends(user_from_auth)):
    row = conn.execute(
        "SELECT sync_status, last_sync_at, sync_error FROM tracker_integrations WHERE user_id = ?",
        (user["id"],),
    ).fetchone()
    if not row:
        return {"sync_status": "not_configured"}
    return {"sync_status": row[0], "last_sync": row[1], "error": row[2]}


@app.get("/api/library")
def library(user=Depends(user_from_auth), status: str | None = None):
    query = """
      SELECT ul.media_id, ul.status, ul.progress, ul.user_rating, m.title, m.creator, m.genres, m.rating
      FROM user_library ul
      JOIN media m ON m.id = ul.media_id
      WHERE ul.user_id = ?
    """
    params: list[object] = [user["id"]]
    if status:
        query += " AND ul.status = ?"
        params.append(status)
    rows = conn.execute(query, params).fetchall()
    return [
        {
            "id": r[0],
            "status": r[1],
            "progress": r[2],
            "user_rating": r[3],
            "title": r[4],
            "creator": r[5],
            "genres": r[6].split(",") if r[6] else [],
            "rating": r[7],
        }
        for r in rows
    ]


@app.get("/api/history")
def history(user=Depends(user_from_auth)):
    return library(user)


@app.get("/api/ratings")
def ratings(user=Depends(user_from_auth)):
    rows = conn.execute(
        "SELECT media_id, user_rating FROM user_library WHERE user_id = ? AND user_rating IS NOT NULL",
        (user["id"],),
    ).fetchall()
    return [{"media_id": r[0], "rating": r[1]} for r in rows]


@app.get("/api/media")
def media_list(query: str | None = None):
    if query:
        rows = conn.execute(
            "SELECT id, title, creator, genres, rating, description FROM media WHERE title LIKE ? ORDER BY popularity DESC",
            (f"%{query}%",),
        ).fetchall()
    else:
        rows = conn.execute("SELECT id, title, creator, genres, rating, description FROM media ORDER BY popularity DESC").fetchall()
    return [
        {
            "id": r[0],
            "title": r[1],
            "creator": r[2],
            "genres": r[3].split(",") if r[3] else [],
            "rating": r[4],
            "description": r[5],
        }
        for r in rows
    ]


@app.get("/api/media/{media_id}")
def media_by_id(media_id: str, user=Depends(user_from_auth)):
    row = conn.execute(
        "SELECT id, title, creator, genres, publisher, description, rating, release_date FROM media WHERE id = ?",
        (media_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Media not found")
    user_state = conn.execute(
        "SELECT status, progress, user_rating FROM user_library WHERE user_id = ? AND media_id = ?",
        (user["id"], media_id),
    ).fetchone()
    return {
        "id": row[0],
        "title": row[1],
        "creator": row[2],
        "genres": row[3].split(",") if row[3] else [],
        "publisher": row[4],
        "description": row[5],
        "rating": row[6],
        "release_date": row[7],
        "user_state": {
            "status": user_state[0],
            "progress": user_state[1],
            "rating": user_state[2],
        }
        if user_state
        else None,
    }


@app.get("/api/search")
def search(q: str):
    return media_list(query=q)


@app.get("/api/metadata/search")
async def metadata_search(request: Request, q: str, limit: int = 10):
    if not q.strip():
        return []
    if limit < 1 or limit > 50:
        raise HTTPException(400, "limit must be between 1 and 50")
    try:
        metadata_service.check_client_limit(request.client.host if request.client else "unknown")
    except MetadataRateLimitError as exc:
        raise HTTPException(429, "Metadata search rate limit exceeded") from exc
    groups = await metadata_service.grouped_search(q.strip(), limit=limit)
    return [_metadata_group_response(group) for group in groups]


@app.get("/api/featured")
async def featured(request: Request, surface: str = "discover", limit: int = 10):
    if surface not in {"discover", "home"}:
        raise HTTPException(400, "surface must be discover or home")
    if limit < 1 or limit > 50:
        raise HTTPException(400, "limit must be between 1 and 50")
    try:
        metadata_service.check_client_limit(request.client.host if request.client else "unknown")
    except MetadataRateLimitError as exc:
        raise HTTPException(429, "Metadata search rate limit exceeded") from exc
    queries = ["Saga", "Monstress", "Descender", "The Sandman"] if surface == "discover" else ["Saga", "Monstress", "Descender"]
    results = []
    seen = set()
    for query in queries:
        for group in await metadata_service.grouped_search(query, limit=3):
            if group.group_id not in seen:
                seen.add(group.group_id)
                results.append(_metadata_group_response(group))
            if len(results) >= limit:
                return results
    return results


@app.get("/api/recommendations")
async def recommendations(request: Request, user=Depends(user_from_auth), limit: int = 20):
    recs = build_recommendations(conn, user["id"], limit=limit)
    ids = [r.media_id for r in recs]
    if not ids:
        featured_results = await featured(request, surface="home", limit=limit)
        return [
            {"id": item["id"], "score": 0, "why": "Featured pick", **item["primary"]}
            for item in featured_results
        ]
    placeholders = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"SELECT id, title, creator, genres, rating, description, source, source_id, image_url, source_url FROM media WHERE id IN ({placeholders})",
        ids,
    ).fetchall()
    by_id = {r[0]: r for r in rows}
    return [
        {
            "id": rec.media_id,
            "score": rec.score,
            "why": rec.reason,
            "title": by_id[rec.media_id][1],
            "creator": by_id[rec.media_id][2],
            "genres": by_id[rec.media_id][3].split(",") if by_id[rec.media_id][3] else [],
            "rating": by_id[rec.media_id][4],
            "description": by_id[rec.media_id][5],
            "source": by_id[rec.media_id][6],
            "source_id": by_id[rec.media_id][7],
            "image_url": by_id[rec.media_id][8],
            "source_url": by_id[rec.media_id][9],
        }
        for rec in recs
        if rec.media_id in by_id
    ]


@app.get("/api/recommendations/{media_id}")
def recommendation_by_id(media_id: str, user=Depends(user_from_auth)):
    for rec in build_recommendations(conn, user["id"], limit=100):
        if rec.media_id == media_id:
            return {"id": rec.media_id, "score": rec.score, "why": rec.reason}
    raise HTTPException(404, "Recommendation not found")


def _feedback(user_id: int, media_id: str, kind: str):
    conn.execute(
        "INSERT INTO recommendation_feedback (user_id, media_id, feedback, created_at) VALUES (?, ?, ?, ?)",
        (user_id, media_id, kind, now_iso()),
    )
    conn.commit()


@app.post("/api/recommendations/{media_id}/like")
def like(media_id: str, user=Depends(user_from_auth)):
    _feedback(user["id"], media_id, "like")
    return {"ok": True}


@app.post("/api/recommendations/{media_id}/dismiss")
def dismiss(media_id: str, user=Depends(user_from_auth)):
    _feedback(user["id"], media_id, "dismiss")
    return {"ok": True}
