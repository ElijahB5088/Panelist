from datetime import datetime, timedelta, timezone
import uuid

from fastapi.testclient import TestClient

from app import main
from app.config import settings


def _authenticated_client():
    client = TestClient(main.app)
    username = f"session-{uuid.uuid4().hex}"
    assert client.post(
        "/api/auth/register",
        json={"username": username, "password": "password123"},
    ).status_code == 200
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "password123"},
    )
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    return client


def test_logout_revokes_current_session():
    client = _authenticated_client()

    assert client.get("/api/me").status_code == 200
    assert client.post("/api/auth/logout").json() == {"ok": True}
    assert client.get("/api/me").status_code == 401


def test_expired_session_is_rejected_and_deleted():
    client = _authenticated_client()
    token = client.headers["Authorization"].removeprefix("Bearer ")
    old_created_at = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
    main.conn.execute("UPDATE sessions SET created_at=? WHERE token=?", (old_created_at, token))
    main.conn.commit()
    previous_ttl = settings.session_ttl_days
    settings.session_ttl_days = 30
    try:
        assert client.get("/api/me").status_code == 401
        assert main.conn.execute("SELECT 1 FROM sessions WHERE token=?", (token,)).fetchone() is None
    finally:
        settings.session_ttl_days = previous_ttl
