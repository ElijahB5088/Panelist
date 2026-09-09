import sqlite3

from app import db
from app.catalog_repository import CatalogRepository


def repository():
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    db.run_migrations(connection)
    return connection, CatalogRepository(connection)


def test_catalog_preserves_series_volume_issue_and_credit_relationships():
    connection, catalog = repository()
    publisher = catalog.upsert_entity("publisher", "Example Comics")
    series = catalog.upsert_entity("series", "The Long Run", start_date="2024-01-01")
    volume = catalog.upsert_entity("volume", "The Long Run, Volume 1")
    issue = catalog.upsert_entity("issue", "The Long Run #1")
    person = catalog.upsert_entity("person", "A. Writer")

    catalog.link_series(series.id, publisher.id)
    catalog.link_volume(volume.id, series.id, "1")
    catalog.link_issue(issue.id, volume.id, "1", "2024-02-01")
    catalog.add_credit(issue.id, person.id, "writer", credited_as="A. Writer")

    assert connection.execute("SELECT publisher_entity_id FROM catalog_series").fetchone()[0] == publisher.id
    assert connection.execute("SELECT series_entity_id FROM catalog_volumes").fetchone()[0] == series.id
    assert connection.execute("SELECT volume_entity_id FROM catalog_issues").fetchone()[0] == volume.id
    assert connection.execute("SELECT role FROM catalog_credits").fetchone()[0] == "writer"
    connection.close()


def test_source_record_is_idempotent_and_can_link_to_one_canonical_entity():
    connection, catalog = repository()
    catalog.upsert_entity("series", "The Long Run")
    source = "comicvine"
    catalog.register_source(source, "Comic Vine", attribution="Comic Vine API")
    series_id = connection.execute("SELECT id FROM catalog_entities").fetchone()[0]
    first = catalog.upsert_source_record(source, "123", "series", source_url="https://example/123")
    second = catalog.upsert_source_record(source, "123", "series", source_url="https://example/123-updated")
    catalog.link_source_record(series_id, second)
    catalog.link_source_record(series_id, second)

    assert first == second
    assert connection.execute("SELECT COUNT(*) FROM catalog_source_records").fetchone()[0] == 1
    assert connection.execute("SELECT source_url FROM catalog_source_records").fetchone()[0] == "https://example/123-updated"
    assert connection.execute("SELECT COUNT(*) FROM catalog_entity_sources").fetchone()[0] == 1
    connection.close()


def test_catalog_supports_aliases_and_identifiers_without_flattening_them():
    connection, catalog = repository()
    series = catalog.upsert_entity("series", "The Long Run")
    catalog.add_alias(series.id, "The Long Run (2024)", "en")
    catalog.add_identifier(series.id, "isbn", "9780000000001")

    assert connection.execute("SELECT normalized_alias FROM catalog_aliases").fetchone()[0] == "the long run 2024"
    assert connection.execute("SELECT identifier_type, identifier_value FROM catalog_identifiers").fetchone() == ("isbn", "9780000000001")
    connection.close()