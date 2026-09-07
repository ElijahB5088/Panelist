from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import sqlite3
from datetime import datetime, timedelta, timezone
import httpx
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from .db import get_conn, run_migrations
from .config import settings
from .metadata_service import MetadataRateLimitError, MetadataSearchService
from .providers.metadata import AniListProvider, ComicVineProvider, MetronProvider, OpenLibraryProvider
from .providers.floppy import FloppyProvider, FloppyProviderError
from .providers.kitsu import KitsuProvider
from .providers.mal import MALProvider, decode_token_bundle, encode_token_bundle
from .recommendation import _normalize_title, build_recommendations, library_title_keys
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
tracking_providers = {
    "floppy": FloppyProvider(),
    "kitsu": KitsuProvider(),
    "mal": MALProvider(),
}
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
    worker = asyncio.create_task(automatic_sync_worker())
    try:
        yield
    finally:
        worker.cancel()
        await asyncio.gather(worker, return_exceptions=True)


app = FastAPI(title="Panelist Server", version="0.1.0", lifespan=lifespan)


@app.get("/")
def root() -> HTMLResponse:
    return HTMLResponse(
        """
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>Panelist</title>
            <style>
                :root {
                    color-scheme: light dark;
                    --bg: #0f172a;
                    --panel: #111827;
                    --panel-border: #334155;
                    --text: #e2e8f0;
                    --muted: #cbd5e1;
                    --accent: #7dd3fc;
                    --accent-strong: #38bdf8;
                }
                * { box-sizing: border-box; }
                body {
                    margin: 0;
                    font-family: Arial, Helvetica, sans-serif;
                    background: linear-gradient(180deg, #020817 0%, #0f172a 100%);
                    color: var(--text);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 32px;
                }
                main {
                    width: min(760px, 100%);
                    background: rgba(15, 23, 42, 0.9);
                    border: 1px solid var(--panel-border);
                    border-radius: 18px;
                    padding: 32px;
                    box-shadow: 0 20px 60px rgba(15, 23, 42, 0.45);
                }
                h1 {
                    margin: 0 0 12px;
                    font-size: clamp(2rem, 4vw, 3rem);
                }
                p {
                    color: var(--muted);
                    line-height: 1.6;
                    margin: 0 0 16px;
                    font-size: 1.05rem;
                }
                .links {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 12px;
                    margin-top: 24px;
                }
                a {
                    display: inline-block;
                    background: var(--accent);
                    color: #082f49;
                    text-decoration: none;
                    padding: 10px 16px;
                    border-radius: 10px;
                    font-weight: 700;
                }
                a.secondary {
                    background: transparent;
                    color: var(--accent);
                    border: 1px solid var(--panel-border);
                }
            </style>
        </head>
        <body>
            <main>
                <h1>Panelist</h1>
                <p>
                    Panelist is a privacy-first Android recommendation app and self-hosted backend for comics,
                    manga, and graphic novels.
                </p>
                <p>
                    Track reading activity, discover personalized recommendations, and sync your library through
                    the Panelist API while keeping your tracker credentials encrypted at rest.
                </p>
                <div class="links">
                    <a href="/docs">Open API docs</a>
                    <a class="secondary" href="/redoc">ReDoc</a>
                    <a class="secondary" href="/openapi.json">OpenAPI schema</a>
                    <a class="secondary" href="/health">Health</a>
                </div>
            </main>
        </body>
        </html>
        """
    )


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
        "media_type": result.media_type,
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


class FloppySyncSettings(BaseModel):
    enabled: bool
    interval_minutes: int = Field(
        default=settings.sync_interval_minutes,
        ge=settings.sync_interval_min_minutes,
        le=settings.sync_interval_max_minutes,
    )


class KitsuConfig(BaseModel):
    server_url: str = "https://kitsu.io"
    api_token: str


class MALAuthorizeResponse(BaseModel):
    authorization_url: str


def tracking_provider(provider_name: str):
    try:
        return tracking_providers[provider_name]
    except KeyError as exc:
        raise HTTPException(400, f"Unsupported tracker: {provider_name}") from exc


def _sync_settings_response(row):
    return {
        "enabled": bool(row[0]),
        "interval_minutes": row[1],
        "next_sync_at": row[2],
    }


_sync_locks: dict[int, asyncio.Lock] = {}


def _sync_lock(user_id: int) -> asyncio.Lock:
    return _sync_locks.setdefault(user_id, asyncio.Lock())


async def sync_user_library(user_id: int) -> None:
    async with _sync_lock(user_id):
        row = conn.execute(
            "SELECT provider, server_url, encrypted_token, auto_sync_enabled, auto_sync_interval_minutes FROM tracker_integrations WHERE user_id = ? AND connected = 1",
            (user_id,),
        ).fetchone()
        if not row:
            raise ValueError("No tracker is connected")
        active_provider = tracking_provider(row[0])

        conn.execute(
            "UPDATE tracker_integrations SET sync_status='syncing', sync_error=NULL WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()

        try:
            credential = decrypt_secret(row[2])
            if row[0] == "mal":
                token_bundle = decode_token_bundle(credential)
                try:
                    payload = await active_provider.fetch_library(row[1], token_bundle["access_token"])
                except httpx.HTTPStatusError as exc:
                    if exc.response.status_code != 401 or not token_bundle.get("refresh_token"):
                        raise
                    refreshed = await active_provider.refresh_token(
                        settings.mal_client_id,
                        token_bundle["refresh_token"],
                        settings.mal_client_secret,
                    )
                    conn.execute(
                        "UPDATE tracker_integrations SET encrypted_token=? WHERE user_id=?",
                        (encrypt_secret(encode_token_bundle(refreshed, token_bundle)), user_id),
                    )
                    conn.commit()
                    payload = await active_provider.fetch_library(row[1], refreshed["access_token"])
            else:
                payload = await active_provider.fetch_library(row[1], credential)
            normalized = active_provider.normalize_library(payload)
            if payload and not normalized:
                raise ValueError("Tracker returned entries, but none were recognized as supported library media")
            conn.execute("DELETE FROM user_library WHERE user_id = ?", (user_id,))
            for media, lib in normalized:
                conn.execute(
                    """
                    INSERT INTO media (id, title, creator, genres, publisher, description, rating, source, source_id, media_type, image_url, source_url, tracker_source, tracker_media_id, tracker_item_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      title=excluded.title, creator=excluded.creator, genres=excluded.genres,
                      publisher=excluded.publisher, description=excluded.description, rating=excluded.rating,
                      source=excluded.source, source_id=excluded.source_id, media_type=excluded.media_type,
                      image_url=COALESCE(excluded.image_url, media.image_url),
                      source_url=COALESCE(excluded.source_url, media.source_url),
                      tracker_source=excluded.tracker_source, tracker_media_id=excluded.tracker_media_id,
                      tracker_item_id=excluded.tracker_item_id
                    """,
                    (
                        media.id, media.title, media.creator, ",".join(media.genres), media.publisher,
                        media.description, media.rating, media.source, media.source_id, media.media_type,
                        media.image_url, media.source_url, lib.get("tracker_source"),
                        lib.get("tracker_media_id"), lib.get("tracker_item_id"),
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO user_library (user_id, media_id, status, progress, user_rating, progress_max, progress_unit, progress_scope, progress_percent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, media_id) DO UPDATE SET
                      status=excluded.status, progress=excluded.progress, user_rating=excluded.user_rating,
                      progress_max=excluded.progress_max, progress_unit=excluded.progress_unit,
                      progress_scope=excluded.progress_scope, progress_percent=excluded.progress_percent
                    """,
                    (
                        user_id, media.id, lib["status"], lib["progress"], lib["user_rating"],
                        lib.get("progress_max"), lib.get("progress_unit"), lib.get("progress_scope"),
                        lib.get("progress_percent"),
                    ),
                )

            synced_at = datetime.now(timezone.utc)
            next_sync_at = (
                (synced_at + timedelta(minutes=row[4])).isoformat()
                if row[3]
                else None
            )
            conn.execute(
                "UPDATE tracker_integrations SET last_sync_at=?, next_sync_at=?, sync_status='idle' WHERE user_id = ?",
                (synced_at.isoformat(), next_sync_at, user_id),
            )
            conn.commit()
        except Exception as exc:
            error_message = str(exc)[:240] or "Unknown sync error"
            conn.execute(
                "UPDATE tracker_integrations SET sync_status='error', sync_error=? WHERE user_id = ?",
                (error_message, user_id),
            )
            conn.commit()
            raise


async def run_due_auto_syncs(now: datetime | None = None) -> None:
    current = now or datetime.now(timezone.utc)
    rows = conn.execute(
        "SELECT user_id FROM tracker_integrations WHERE provider='floppy' AND connected=1 AND auto_sync_enabled=1 AND (next_sync_at IS NULL OR next_sync_at <= ?)",
        (current.isoformat(),),
    ).fetchall()
    for row in rows:
        try:
            await sync_user_library(row[0])
        except Exception:
            continue


async def automatic_sync_worker():
    while True:
        await run_due_auto_syncs()
        await asyncio.sleep(60)


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
        "SELECT provider, server_url, connected, last_sync_at, sync_status, sync_error, auto_sync_enabled, auto_sync_interval_minutes, next_sync_at FROM tracker_integrations WHERE user_id = ?",
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
            "auto_sync_enabled": bool(integration[6]),
            "auto_sync_interval_minutes": integration[7],
            "next_sync_at": integration[8],
        }
        if integration
        else None,
    }


@app.post("/api/integrations/mal/authorize", response_model=MALAuthorizeResponse)
def authorize_mal(user=Depends(user_from_auth)):
    if not settings.mal_client_id:
        raise HTTPException(503, "MAL_CLIENT_ID is not configured")
    provider = tracking_providers["mal"]
    authorization = provider.create_authorization(settings.mal_client_id, settings.mal_redirect_uri)
    conn.execute("DELETE FROM mal_oauth_states WHERE expires_at < ?", (now_iso(),))
    conn.execute(
        "INSERT INTO mal_oauth_states (state, user_id, code_verifier, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
        (authorization.state, user["id"], authorization.code_verifier, now_iso(), (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()),
    )
    conn.commit()
    return {"authorization_url": authorization.authorization_url}


@app.get("/api/integrations/mal/callback", response_class=HTMLResponse)
async def mal_callback(code: str | None = None, state: str | None = None, error: str | None = None):
    if error or not code or not state:
        return HTMLResponse(f"<h1>MyAnimeList connection failed</h1><p>{escape(error or 'Invalid callback.')}</p>", status_code=400)
    row = conn.execute(
        "SELECT user_id, code_verifier FROM mal_oauth_states WHERE state = ? AND expires_at >= ?",
        (state, now_iso()),
    ).fetchone()
    if not row:
        return HTMLResponse("<h1>MyAnimeList connection failed</h1><p>Expired or invalid authorization state.</p>", status_code=400)
    conn.execute("DELETE FROM mal_oauth_states WHERE state = ?", (state,))
    conn.commit()
    try:
        tokens = await tracking_providers["mal"].exchange_code(
            settings.mal_client_id,
            code,
            row[1],
            settings.mal_redirect_uri,
            settings.mal_client_secret,
        )
        conn.execute(
            """
            INSERT INTO tracker_integrations (user_id, provider, server_url, encrypted_token, connected, sync_status)
            VALUES (?, 'mal', 'https://api.myanimelist.net/v2', ?, 1, 'idle')
            ON CONFLICT(user_id) DO UPDATE SET
              provider='mal', server_url=excluded.server_url,
              encrypted_token=excluded.encrypted_token, connected=1, sync_error=NULL
            """,
            (row[0], encrypt_secret(encode_token_bundle(tokens))),
        )
        conn.commit()
    except httpx.HTTPError:
        return HTMLResponse("<h1>MyAnimeList connection failed</h1><p>Could not complete authorization.</p>", status_code=502)
    return HTMLResponse("<h1>MyAnimeList connected</h1><p>You can return to Panelist and sync your manga library.</p>")


@app.delete("/api/integrations/mal")
def disconnect_mal(user=Depends(user_from_auth)):
    conn.execute("DELETE FROM tracker_integrations WHERE user_id = ?", (user["id"],))
    conn.commit()
    return {"ok": True}


@app.post("/api/integrations/floppy/test")
async def test_floppy(body: FloppyConfig, user=Depends(user_from_auth)):
    try:
        ok = await tracking_providers["floppy"].test_connection(body.server_url, body.api_token)
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


@app.post("/api/integrations/kitsu/test")
async def test_kitsu(body: KitsuConfig, user=Depends(user_from_auth)):
    try:
        ok = await tracking_providers["kitsu"].test_connection(body.server_url, body.api_token)
    except httpx.HTTPStatusError as exc:
        response = exc.response
        detail = response.text[:240] or response.reason_phrase
        return {
            "connected": False,
            "server_url": body.server_url,
            "error": f"Kitsu returned HTTP {response.status_code}: {detail}",
        }
    except httpx.HTTPError as exc:
        detail = str(exc) or type(exc).__name__
        raise HTTPException(502, f"Could not reach Kitsu at {body.server_url}: {detail}") from exc
    return {"connected": ok, "server_url": body.server_url}


@app.post("/api/integrations/floppy")
def connect_floppy(body: FloppyConfig, user=Depends(user_from_auth)):
    conn.execute(
        """
        INSERT INTO tracker_integrations (user_id, provider, server_url, encrypted_token, connected, sync_status)
        VALUES (?, 'floppy', ?, ?, 1, 'idle')
        ON CONFLICT(user_id) DO UPDATE SET
          provider='floppy', server_url=excluded.server_url,
                    encrypted_token=excluded.encrypted_token, connected=1,
                    auto_sync_enabled=0, next_sync_at=NULL, sync_error=NULL
        """,
        (user["id"], body.server_url, encrypt_secret(body.api_token)),
    )
    conn.commit()
    return {"connected": True, "server_url": body.server_url}


@app.get("/api/integrations/floppy/sync-settings")
def floppy_sync_settings(user=Depends(user_from_auth)):
    row = conn.execute(
        "SELECT auto_sync_enabled, auto_sync_interval_minutes, next_sync_at FROM tracker_integrations WHERE user_id = ? AND provider = 'floppy' AND connected = 1",
        (user["id"],),
    ).fetchone()
    if not row:
        raise HTTPException(400, "Floppy is not connected")
    return _sync_settings_response(row)


@app.post("/api/integrations/floppy/sync-settings")
def update_floppy_sync_settings(body: FloppySyncSettings, user=Depends(user_from_auth)):
    row = conn.execute(
        "SELECT auto_sync_enabled, auto_sync_interval_minutes, next_sync_at FROM tracker_integrations WHERE user_id = ? AND provider = 'floppy' AND connected = 1",
        (user["id"],),
    ).fetchone()
    if not row:
        raise HTTPException(400, "Floppy is not connected")
    next_sync_at = datetime.now(timezone.utc).isoformat() if body.enabled else None
    conn.execute(
        "UPDATE tracker_integrations SET auto_sync_enabled=?, auto_sync_interval_minutes=?, next_sync_at=? WHERE user_id=?",
        (int(body.enabled), body.interval_minutes, next_sync_at, user["id"]),
    )
    conn.commit()
    return {
        "enabled": body.enabled,
        "interval_minutes": body.interval_minutes,
        "next_sync_at": next_sync_at,
    }


@app.post("/api/integrations/kitsu")
def connect_kitsu(body: KitsuConfig, user=Depends(user_from_auth)):
        conn.execute(
                """
                INSERT INTO tracker_integrations (user_id, provider, server_url, encrypted_token, connected, sync_status)
                VALUES (?, 'kitsu', ?, ?, 1, 'idle')
                ON CONFLICT(user_id) DO UPDATE SET
                    provider='kitsu', server_url=excluded.server_url,
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


@app.delete("/api/integrations/kitsu")
def disconnect_kitsu(user=Depends(user_from_auth)):
    conn.execute("DELETE FROM tracker_integrations WHERE user_id = ?", (user["id"],))
    conn.commit()
    return {"ok": True}


@app.post("/api/sync")
async def sync(user=Depends(user_from_auth)):
    try:
        await sync_user_library(user["id"])
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except FloppyProviderError as exc:
        raise HTTPException(502, f"Sync failed: {exc}") from exc
    except Exception as exc:
        raise HTTPException(502, "Tracker sync failed") from exc
    return {"ok": True, "status": "synced"}


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
            SELECT ul.media_id, ul.status, ul.progress, ul.progress_max, ul.progress_unit,
                         ul.progress_scope, ul.progress_percent, ul.user_rating, m.title, m.creator,
                         m.genres, m.rating, m.source, m.source_id, m.media_type, m.image_url, m.source_url,
                         m.tracker_source, m.tracker_media_id, m.tracker_item_id
      FROM user_library ul
      JOIN media m ON m.id = ul.media_id
      WHERE ul.user_id = ?
    """
    params: list[object] = [user["id"]]
    if status == "rated":
        query += " AND ul.user_rating IS NOT NULL"
    elif status:
        query += " AND ul.status = ?"
        params.append(status)
    rows = conn.execute(query, params).fetchall()
    return [
        {
            "id": r[0],
            "status": r[1],
            "progress": r[2],
            "progress_max": r[3],
            "progress_unit": r[4],
            "progress_scope": r[5],
            "progress_percent": r[6],
            "user_rating": r[7],
            "title": r[8],
            "creator": r[9],
            "genres": r[10].split(",") if r[10] else [],
            "rating": r[11],
            "source": r[12],
            "source_id": r[13],
            "library_media_type": r[14],
            "image_url": r[15],
            "source_url": r[16],
            "tracker_source": r[17],
            "tracker_media_id": r[18],
            "tracker_item_id": r[19],
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
        "SELECT id, title, creator, genres, publisher, description, rating, release_date, source, source_id, media_type, tracker_source, tracker_media_id, tracker_item_id FROM media WHERE id = ?",
        (media_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Media not found")
    user_state = conn.execute(
        "SELECT status, progress, progress_max, progress_unit, progress_scope, progress_percent, user_rating FROM user_library WHERE user_id = ? AND media_id = ?",
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
        "source": row[8],
        "source_id": row[9],
        "library_media_type": row[10],
        "tracker_source": row[11],
        "tracker_media_id": row[12],
        "tracker_item_id": row[13],
        "user_state": {
            "status": user_state[0],
            "progress": user_state[1],
            "progress_max": user_state[2],
            "progress_unit": user_state[3],
            "progress_scope": user_state[4],
            "progress_percent": user_state[5],
            "rating": user_state[6],
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


async def _featured(request: Request, surface: str = "discover", limit: int = 10, excluded_titles: set[str] | None = None):
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
                item = _metadata_group_response(group)
                if excluded_titles and _normalize_title(item["primary"]["title"]) in excluded_titles:
                    continue
                results.append(item)
            if len(results) >= limit:
                return results
    return results


@app.get("/api/featured")
async def featured(request: Request, surface: str = "discover", limit: int = 10):
    return await _featured(request, surface=surface, limit=limit)


@app.get("/api/recommendations")
async def recommendations(request: Request, user=Depends(user_from_auth), limit: int = 100):
    recs = build_recommendations(conn, user["id"], limit=limit)
    ids = [r.media_id for r in recs]
    if not ids:
        featured_results = await _featured(
            request,
            surface="home",
            limit=min(limit, 50),
            excluded_titles=library_title_keys(conn, user["id"]),
        )
        return [
            {"id": item["id"], "score": 0, "why": "Featured pick", **item["primary"]}
            for item in featured_results
        ]
    placeholders = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"""
        SELECT id, title, creator, genres, rating, description, source, source_id,
               image_url, source_url,
               COALESCE(
                   CASE WHEN media_type = 'comics' THEN 'comic' ELSE media_type END,
                   CASE
                       WHEN source IN ('anilist', 'kitsu', 'mal')
                            OR tracker_source IN ('kitsu', 'mal') THEN 'manga'
                       WHEN source IN ('comicvine', 'metron', 'openlibrary')
                            OR tracker_source = 'floppy' THEN 'comic'
                   END
               ) AS media_type,
               release_date
        FROM media
        WHERE id IN ({placeholders})
        """,
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
            "media_type": by_id[rec.media_id][10],
            "release_date": by_id[rec.media_id][11],
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
