import asyncio
import uuid

from fastapi.testclient import TestClient

from app import main
from app.security import decrypt_secret


def authenticated_client():
    client = TestClient(main.app)
    username = f"sync-{uuid.uuid4().hex}"
    assert client.post("/api/auth/register", json={"username": username, "password": "password123"}).status_code == 200
    login = client.post("/api/auth/login", json={"username": username, "password": "password123"})
    client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
    return client


def test_floppy_key_is_stored_encrypted_and_sync_is_opt_in():
    client = authenticated_client()

    response = client.post(
        "/api/integrations/floppy",
        json={"server_url": "https://floppy.example", "api_token": "secret-token"},
    )

    assert response.status_code == 200
    row = main.conn.execute(
        "SELECT encrypted_token, auto_sync_enabled, auto_sync_interval_minutes FROM tracker_integrations ORDER BY user_id DESC LIMIT 1"
    ).fetchone()
    assert row[0] != "secret-token"
    assert decrypt_secret(row[0]) == "secret-token"
    assert row[1:] == (0, 60)

    profile = client.get("/api/profile").json()["connected_tracker"]
    assert profile["auto_sync_enabled"] is False
    assert "api_token" not in str(profile)


def test_floppy_sync_settings_validate_and_update():
    client = authenticated_client()
    client.post(
        "/api/integrations/floppy",
        json={"server_url": "https://floppy.example", "api_token": "secret-token"},
    )

    invalid = client.post(
        "/api/integrations/floppy/sync-settings",
        json={"enabled": True, "interval_minutes": 5},
    )
    assert invalid.status_code == 422

    updated = client.post(
        "/api/integrations/floppy/sync-settings",
        json={"enabled": True, "interval_minutes": 30},
    )
    assert updated.status_code == 200
    assert updated.json()["enabled"] is True
    assert updated.json()["interval_minutes"] == 30
    assert updated.json()["next_sync_at"]


def test_due_runner_only_calls_enabled_floppy_integrations(monkeypatch):
    client = authenticated_client()
    client.post(
        "/api/integrations/floppy",
        json={"server_url": "https://floppy.example", "api_token": "secret-token"},
    )
    user_id = client.get("/api/me").json()["id"]
    main.conn.execute("UPDATE tracker_integrations SET auto_sync_enabled=0, next_sync_at=NULL")
    main.conn.execute(
        "UPDATE tracker_integrations SET auto_sync_enabled=1, next_sync_at=? WHERE user_id=?",
        ("2000-01-01T00:00:00+00:00", user_id),
    )
    main.conn.commit()
    calls = []

    async def fake_sync(sync_user_id):
        calls.append(sync_user_id)

    monkeypatch.setattr(main, "sync_user_library", fake_sync)
    asyncio.run(main.run_due_auto_syncs())

    assert calls == [user_id]


def test_floppy_sync_ignores_unsupported_media_without_clearing_library(monkeypatch):
    client = authenticated_client()
    client.post(
        "/api/integrations/floppy",
        json={"server_url": "https://floppy.example", "api_token": "secret-token"},
    )
    user_id = client.get("/api/me").json()["id"]
    media_id = f"existing-{user_id}"
    main.conn.execute("INSERT INTO media (id, title, media_type) VALUES (?, ?, ?)", (media_id, "Existing Comic", "comic"))
    main.conn.execute(
        "INSERT INTO user_library (user_id, media_id, status) VALUES (?, ?, ?)",
        (user_id, media_id, "reading"),
    )
    main.conn.commit()

    async def fake_fetch_library(server_url, api_token):
        return [{"media_id": "anime-1", "media_type": "anime", "item": {"title": "Anime"}}]

    monkeypatch.setattr(main.tracking_providers["floppy"], "fetch_library", fake_fetch_library)

    response = client.post("/api/sync")

    assert response.status_code == 200
    rows = main.conn.execute(
        "SELECT media_id FROM user_library WHERE user_id = ?", (user_id,)
    ).fetchall()
    assert [row[0] for row in rows] == [media_id]
    assert client.get("/api/sync/status").json()["error"] is None