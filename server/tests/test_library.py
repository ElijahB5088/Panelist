import uuid

from fastapi.testclient import TestClient

from app import main


def authenticated_client():
    client = TestClient(main.app)
    username = f"library-{uuid.uuid4().hex}"
    assert client.post("/api/auth/register", json={"username": username, "password": "password123"}).status_code == 200
    login = client.post("/api/auth/login", json={"username": username, "password": "password123"})
    client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
    return client


def seed_library(client):
    user_id = client.get("/api/me").json()["id"]
    media = [
        (f"{user_id}-z", "Zeta", "reading", 20, 8.0, 20, "2026-01-01T00:00:00+00:00"),
        (f"{user_id}-a", "Alpha", "completed", 100, 9.0, 100, "2026-03-01T00:00:00+00:00"),
        (f"{user_id}-m", "Mu", "planned", None, None, None, "2026-02-01T00:00:00+00:00"),
    ]
    for media_id, title, status, progress, rating, progress_percent, added_at in media:
        main.conn.execute(
            "INSERT INTO media (id, title) VALUES (?, ?)",
            (media_id, title),
        )
        main.conn.execute(
            """
            INSERT INTO user_library
                (user_id, media_id, status, progress, user_rating, progress_percent, added_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, media_id, status, progress, rating, progress_percent, added_at),
        )
    main.conn.commit()


def library_titles(client, **params):
    response = client.get("/api/library", params=params)
    assert response.status_code == 200
    return [item["title"] for item in response.json()]


def test_library_supports_sorting_and_status_filtering():
    client = authenticated_client()
    seed_library(client)

    assert library_titles(client) == ["Alpha", "Mu", "Zeta"]
    assert library_titles(client, sort="title_desc") == ["Zeta", "Mu", "Alpha"]
    assert library_titles(client, sort="rating_desc") == ["Alpha", "Zeta", "Mu"]
    assert library_titles(client, sort="progress_asc") == ["Zeta", "Alpha", "Mu"]
    assert library_titles(client, sort="added_desc") == ["Alpha", "Mu", "Zeta"]
    assert library_titles(client, status="reading", sort="title_desc") == ["Zeta"]


def test_library_rejects_unknown_sort():
    client = authenticated_client()

    response = client.get("/api/library", params={"sort": "popularity"})

    assert response.status_code == 400
