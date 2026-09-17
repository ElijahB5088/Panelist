import uuid

from fastapi.testclient import TestClient

from app import main


def seed_catalog():
    alias = f"The Long Run ({uuid.uuid4().hex})"
    publisher = main.catalog_repository.upsert_entity("publisher", "Example Comics", entity_id=f"publisher-{uuid.uuid4().hex}")
    series = main.catalog_repository.upsert_entity("series", "The Long Run", entity_id=f"series-{uuid.uuid4().hex}")
    volume = main.catalog_repository.upsert_entity("volume", "The Long Run Volume 1", entity_id=f"volume-{uuid.uuid4().hex}")
    issue = main.catalog_repository.upsert_entity("issue", "The Long Run #1", entity_id=f"issue-{uuid.uuid4().hex}")
    person = main.catalog_repository.upsert_entity("person", "A. Writer", entity_id=f"person-{uuid.uuid4().hex}")
    main.catalog_repository.link_series(series.id, publisher.id)
    main.catalog_repository.link_volume(volume.id, series.id, "1")
    main.catalog_repository.link_issue(issue.id, volume.id, "1", "2024-02-01")
    main.catalog_repository.add_credit(issue.id, person.id, "writer", credited_as="A. Writer")
    main.catalog_repository.add_alias(series.id, alias, "en")
    main.catalog_repository.register_source("test", "Test Source", attribution="Test attribution")
    record_id = main.catalog_repository.upsert_source_record("test", uuid.uuid4().hex, "series", source_url="https://example.test/series")
    main.catalog_repository.link_source_record(series.id, record_id)
    return series.id, volume.id, alias


def test_catalog_search_matches_alias_and_filters_type():
    series_id, _, alias = seed_catalog()
    client = TestClient(main.app)

    response = client.get("/api/catalog/search", params={"q": alias, "entity_type": "series"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [series_id]


def test_catalog_detail_includes_relationships_credits_and_sources():
    series_id, volume_id, _ = seed_catalog()
    client = TestClient(main.app)

    series = client.get(f"/api/catalog/{series_id}")
    volume = client.get(f"/api/catalog/{volume_id}")

    assert series.status_code == 200
    assert series.json()["relationships"]["volumes"][0]["id"] == volume_id
    assert series.json()["sources"][0]["attribution"] == "Test attribution"
    assert volume.status_code == 200
    assert volume.json()["relationships"]["issues"][0]["entity_type"] == "issue"


def test_catalog_api_validates_limit_type_and_missing_entities():
    client = TestClient(main.app)

    assert client.get("/api/catalog/search", params={"q": "run", "limit": 0}).status_code == 400
    assert client.get("/api/catalog/search", params={"q": "run", "entity_type": "chapter"}).status_code == 400
    assert client.get("/api/catalog/does-not-exist").status_code == 404