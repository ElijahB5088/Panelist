import asyncio
from types import SimpleNamespace

from app import main
from app.metadata import MetadataGroup, MetadataResult


def test_featured_excludes_normalized_library_titles(monkeypatch):
    groups = [
        MetadataGroup(
            group_id="read",
            primary=MetadataResult("fake", "read", "  SAGA  ", image_url="https://covers.example/saga.jpg"),
            variants=[],
        ),
        MetadataGroup(
            group_id="unread",
            primary=MetadataResult("fake", "unread", "Monstress", image_url="https://covers.example/monstress.jpg"),
            variants=[],
        ),
    ]

    async def grouped_search(query, limit=10):
        return groups

    monkeypatch.setattr(main.metadata_service, "grouped_search", grouped_search)
    request = SimpleNamespace(client=SimpleNamespace(host="test"))

    results = asyncio.run(main._featured(request, surface="home", limit=1, excluded_titles={"saga"}))

    assert [result["primary"]["title"] for result in results] == ["Monstress"]