from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_homepage_has_panelist_overview_and_links():
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Panelist" in response.text
    assert "privacy-first" in response.text.lower()
    assert "/docs" in response.text
    assert "/redoc" in response.text
    assert "/openapi.json" in response.text
    assert "/health" in response.text
