import uuid

import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import settings


def authenticated_client():
    client = TestClient(main.app)
    username = f"audit-{uuid.uuid4().hex}"
    assert client.post("/api/auth/register", json={"username": username, "password": "password123"}).status_code == 200
    login = client.post("/api/auth/login", json={"username": username, "password": "password123"})
    client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
    return client


def test_audit_logs_are_user_scoped_and_redacted():
    client = authenticated_client()

    response = client.get("/api/audit/logs", params={"event_type": "auth.login"})

    assert response.status_code == 200
    assert response.json()
    assert all(item["event_type"] == "auth.login" for item in response.json())
    assert "password123" not in response.text
    assert "access_token" not in response.text


def test_audit_logs_record_trusted_proxy_https_observation():
    client = authenticated_client()
    previous = settings.trusted_proxy_headers
    settings.trusted_proxy_headers = True
    try:
        response = client.get("/api/audit/logs", headers={"X-Forwarded-Proto": "https"})
    finally:
        settings.trusted_proxy_headers = previous

    assert response.status_code == 200
    https_events = [item for item in response.json() if item["event_type"] == "security.https_observed"]
    assert https_events
    assert https_events[0]["details"]["observed_https"] is True


def test_readiness_checks_database():
    response = TestClient(main.app).get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_production_rejects_default_secrets():
    previous = (settings.environment, settings.secret_key, settings.credential_encryption_key)
    settings.environment = "production"
    settings.secret_key = "dev-secret"
    settings.credential_encryption_key = "configured"
    try:
        with pytest.raises(RuntimeError, match="PANELIST_SECRET_KEY"):
            settings.validate_runtime()
    finally:
        settings.environment, settings.secret_key, settings.credential_encryption_key = previous
