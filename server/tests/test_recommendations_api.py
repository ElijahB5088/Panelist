import asyncio
import uuid

import pytest
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


def test_recommendations_preserve_anilist_manga_type_during_cover_enrichment(monkeypatch):
    client = authenticated_client()
    user_id = client.get("/api/me").json()["id"]
    candidate_id = f"{user_id}-one-piece"
    main.conn.execute(
        "INSERT INTO media (id, title, creator, genres, rating, source, media_type, image_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (candidate_id, "One Piece", "Eiichiro Oda", "action,adventure", 5.0, "anilist", None, None),
    )
    main.conn.commit()

    async def grouped_search(query, limit=10):
        return [
            MetadataGroup(
                group_id="one-piece",
                primary=MetadataResult(
                    "comicvine",
                    "comicvine-one-piece",
                    "One Piece",
                    "Eiichiro Oda",
                    image_url="https://covers.example/one-piece.jpg",
                    source_url="https://comicvine.example/one-piece",
                ),
                variants=[],
            )
        ]

    async def no_featured(*args, **kwargs):
        return []

    monkeypatch.setattr(main.metadata_service, "grouped_search", grouped_search)
    monkeypatch.setattr(main, "_featured", no_featured)

    manga_response = client.get("/api/recommendations", params={"media_type": "manga", "limit": 100})
    comic_response = client.get("/api/recommendations", params={"media_type": "comic", "limit": 100})

    assert manga_response.status_code == 200
    assert candidate_id in [item["id"] for item in manga_response.json()]
    assert comic_response.status_code == 200
    assert candidate_id not in [item["id"] for item in comic_response.json()]
    assert tuple(
        main.conn.execute(
            "SELECT source, media_type, image_url FROM media WHERE id = ?", (candidate_id,)
        ).fetchone()
    ) == ("anilist", None, None)


@pytest.mark.parametrize(
    ("candidate_title", "candidate_creator", "candidate_type"),
    [
        ("Wrong Saga", "Creator", None),
        ("Candidate Saga", "Other Creator", None),
        ("Candidate Saga", "Creator", "comic"),
    ],
)
def test_recommendations_reject_unverified_cover_matches(
    monkeypatch,
    candidate_title,
    candidate_creator,
    candidate_type,
):
    client = authenticated_client()
    user_id = client.get("/api/me").json()["id"]
    candidate_id = f"{user_id}-candidate"
    stored_type = "manga" if candidate_type else None
    main.conn.execute(
        "INSERT INTO media (id, title, creator, genres, rating, media_type, image_url) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (candidate_id, "Candidate Saga", "Creator", "science-fiction", 5.0, stored_type, None),
    )
    main.conn.commit()

    async def grouped_search(query, limit=10):
        return [
            MetadataGroup(
                group_id="candidate",
                primary=MetadataResult(
                    "comicvine",
                    f"candidate-source-{user_id}",
                    candidate_title,
                    candidate_creator,
                    image_url="https://covers.example/wrong.jpg",
                    media_type=candidate_type,
                ),
                variants=[],
            )
        ]

    monkeypatch.setattr(main.metadata_service, "grouped_search", grouped_search)

    response = client.get("/api/recommendations", params={"limit": 10})

    assert response.status_code == 200
    item = next(item for item in response.json() if item["id"] == candidate_id)
    assert item["image_url"] is None
    assert tuple(
        main.conn.execute(
            "SELECT source, source_id, image_url FROM media WHERE id = ?", (candidate_id,)
        ).fetchone()
    ) == (None, None, None)
    assert main.conn.execute(
        "SELECT COUNT(*) FROM media_sources WHERE media_id = ?", (candidate_id,)
    ).fetchone()[0] == 0


def test_recommendations_keep_coverless_candidate_when_enrichment_times_out(monkeypatch):
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
        raise asyncio.TimeoutError

    monkeypatch.setattr(main.metadata_service, "grouped_search", grouped_search)

    response = client.get("/api/recommendations", params={"limit": 10})

    assert response.status_code == 200
    item = next(item for item in response.json() if item["id"] == candidate_id)
    assert item["title"] == "Candidate Saga"
    assert item["image_url"] is None
