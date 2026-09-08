import uuid

from fastapi.testclient import TestClient

from app import main
from app.metadata import MetadataGroup, MetadataResult


def authenticated_client():
    client = TestClient(main.app)
    username = f"recommendations-{uuid.uuid4().hex}"
    assert client.post("/api/auth/register", json={"username": username, "password": "password123"}).status_code == 200
    login = client.post("/api/auth/login", json={"username": username, "password": "password123"})
    client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
    return client


def test_recommendations_exclude_read_items_and_enrich_covers(monkeypatch):
    client = authenticated_client()
    user_id = client.get("/api/me").json()["id"]
    read_id = f"{user_id}-read"
    candidate_id = f"{user_id}-candidate"
    main.conn.executemany(
        "INSERT INTO media (id, title, creator, genres, rating, source, image_url) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (read_id, "Read Saga", "Creator", "science-fiction", 5.0, "comicvine", "https://covers.example/read.jpg"),
            (candidate_id, "Unread Saga", "Creator", "science-fiction", 5.0, None, None),
        ],
    )
    main.conn.executemany(
        "INSERT INTO user_library (user_id, media_id, status, progress, user_rating) VALUES (?, ?, ?, ?, ?)",
        [
            (user_id, read_id, "completed", 100, 5.0),
            (user_id, candidate_id, "planned", 0, None),
        ],
    )
    main.conn.commit()

    async def grouped_search(query, limit=10):
        return [
            MetadataGroup(
                group_id="candidate",
                primary=MetadataResult(
                    "comicvine",
                    "candidate-source-id",
                    "Unread Saga",
                    "Creator",
                    image_url="https://covers.example/candidate.jpg",
                    source_url="https://comicvine.example/candidate",
                ),
                variants=[],
            )
        ]

    monkeypatch.setattr(main.metadata_service, "grouped_search", grouped_search)

    response = client.get("/api/recommendations", params={"limit": 10})

    assert response.status_code == 200
    recommendations = response.json()
    assert read_id not in [item["id"] for item in recommendations]
    assert candidate_id in [item["id"] for item in recommendations]


def test_recommendations_enrich_coverless_candidate(monkeypatch):
    client = authenticated_client()
    user_id = client.get("/api/me").json()["id"]
    library_id = f"{user_id}-library"
    candidate_id = f"{user_id}-candidate"
    main.conn.executemany(
        "INSERT INTO media (id, title, creator, genres, rating, source, image_url) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (library_id, "Library Saga", "Creator", "science-fiction", 5.0, "comicvine", "https://covers.example/library.jpg"),
            (candidate_id, "Candidate Saga", "Creator", "science-fiction", 5.0, None, None),
        ],
    )
    main.conn.execute(
        "INSERT INTO user_library (user_id, media_id, status, progress, user_rating) VALUES (?, ?, ?, ?, ?)",
        (user_id, library_id, "completed", 100, 5.0),
    )
    main.conn.commit()

    async def grouped_search(query, limit=10):
        return [
            MetadataGroup(
                group_id="candidate",
                primary=MetadataResult(
                    "comicvine",
                    "candidate-source-id",
                    "Candidate Saga",
                    "Creator",
                    image_url="https://covers.example/candidate.jpg",
                    source_url="https://comicvine.example/candidate",
                ),
                variants=[],
            )
        ]

    monkeypatch.setattr(main.metadata_service, "grouped_search", grouped_search)

    response = client.get("/api/recommendations", params={"limit": 10})

    assert response.status_code == 200
    item = next(item for item in response.json() if item["id"] == candidate_id)
    assert item["image_url"] == "https://covers.example/candidate.jpg"
    assert item["source"] == "comicvine"
    assert main.conn.execute("SELECT image_url FROM media WHERE id = ?", (candidate_id,)).fetchone()[0] == item["image_url"]
