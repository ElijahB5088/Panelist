from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from .metadata_mapping import normalize_identity


@dataclass(frozen=True)
class CatalogEntity:
    id: str
    entity_type: str
    title: str
    description: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class CatalogRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection

    def register_source(
        self,
        name: str,
        display_name: str,
        *,
        source_url: str | None = None,
        attribution: str | None = None,
    ) -> None:
        if not name.strip() or not display_name.strip():
            raise ValueError("catalog sources require a name and display name")
        self.connection.execute(
            "INSERT INTO catalog_sources (name, display_name, source_url, attribution) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(name) DO UPDATE SET display_name = excluded.display_name, "
            "source_url = excluded.source_url, attribution = excluded.attribution",
            (name.strip().lower(), display_name.strip(), source_url, attribution),
        )
        self.connection.commit()

    def upsert_entity(
        self,
        entity_type: str,
        title: str,
        *,
        entity_id: str | None = None,
        description: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> CatalogEntity:
        allowed_types = {"series", "volume", "issue", "person", "publisher", "edition"}
        if entity_type not in allowed_types:
            raise ValueError(f"unsupported catalog entity type: {entity_type}")
        if not title.strip():
            raise ValueError("catalog entity title cannot be empty")

        entity_id = entity_id or str(uuid.uuid4())
        now = _utc_now()
        self.connection.execute(
            """
            INSERT INTO catalog_entities
                (id, entity_type, title, normalized_title, description, start_date, end_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                entity_type = excluded.entity_type,
                title = excluded.title,
                normalized_title = excluded.normalized_title,
                description = excluded.description,
                start_date = excluded.start_date,
                end_date = excluded.end_date,
                updated_at = excluded.updated_at
            """,
            (entity_id, entity_type, title.strip(), normalize_identity(title), description, start_date, end_date, now, now),
        )
        self.connection.commit()
        return CatalogEntity(entity_id, entity_type, title.strip(), description, start_date, end_date)

    def link_series(self, series_id: str, publisher_id: str | None = None) -> None:
        self.connection.execute(
            "INSERT INTO catalog_series (entity_id, publisher_entity_id) VALUES (?, ?) "
            "ON CONFLICT(entity_id) DO UPDATE SET publisher_entity_id = excluded.publisher_entity_id",
            (series_id, publisher_id),
        )
        self.connection.commit()

    def link_volume(self, volume_id: str, series_id: str, volume_number: str | None = None) -> None:
        self.connection.execute(
            "INSERT INTO catalog_volumes (entity_id, series_entity_id, volume_number) VALUES (?, ?, ?) "
            "ON CONFLICT(entity_id) DO UPDATE SET series_entity_id = excluded.series_entity_id, volume_number = excluded.volume_number",
            (volume_id, series_id, volume_number),
        )
        self.connection.commit()

    def link_issue(self, issue_id: str, volume_id: str, issue_number: str | None = None, publication_date: str | None = None) -> None:
        self.connection.execute(
            "INSERT INTO catalog_issues (entity_id, volume_entity_id, issue_number, publication_date) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(entity_id) DO UPDATE SET volume_entity_id = excluded.volume_entity_id, issue_number = excluded.issue_number, publication_date = excluded.publication_date",
            (issue_id, volume_id, issue_number, publication_date),
        )
        self.connection.commit()

    def add_alias(self, entity_id: str, alias: str, language: str | None = None) -> None:
        if not alias.strip():
            raise ValueError("catalog alias cannot be empty")
        self.connection.execute(
            "INSERT OR IGNORE INTO catalog_aliases (entity_id, alias, normalized_alias, language) VALUES (?, ?, ?, ?)",
            (entity_id, alias.strip(), normalize_identity(alias), language),
        )
        self.connection.commit()

    def add_identifier(self, entity_id: str, identifier_type: str, identifier_value: str) -> None:
        if not identifier_type.strip() or not identifier_value.strip():
            raise ValueError("catalog identifiers require a type and value")
        self.connection.execute(
            "INSERT INTO catalog_identifiers (entity_id, identifier_type, identifier_value) VALUES (?, ?, ?) "
            "ON CONFLICT(identifier_type, identifier_value) DO UPDATE SET entity_id = excluded.entity_id",
            (entity_id, identifier_type.strip().lower(), identifier_value.strip()),
        )
        self.connection.commit()

    def add_credit(self, entity_id: str, person_id: str, role: str, credited_as: str | None = None) -> None:
        if not role.strip():
            raise ValueError("catalog credit role cannot be empty")
        self.connection.execute(
            "INSERT INTO catalog_credits (entity_id, person_entity_id, role, credited_as) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(entity_id, person_entity_id, role) DO UPDATE SET credited_as = excluded.credited_as",
            (entity_id, person_id, role.strip().lower(), credited_as),
        )
        self.connection.commit()

    def upsert_source_record(
        self,
        source: str,
        source_id: str,
        entity_type: str,
        *,
        source_url: str | None = None,
        normalization_version: str = "1",
        retrieved_at: str | None = None,
    ) -> int:
        if not source.strip() or not source_id.strip():
            raise ValueError("source records require a source and source ID")
        cursor = self.connection.execute(
            """
            INSERT INTO catalog_source_records
                (source, source_id, entity_type, source_url, retrieved_at, normalization_version)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, source_id) DO UPDATE SET
                entity_type = excluded.entity_type,
                source_url = excluded.source_url,
                retrieved_at = excluded.retrieved_at,
                normalization_version = excluded.normalization_version
            RETURNING id
            """,
            (source.strip().lower(), source_id.strip(), entity_type, source_url, retrieved_at or _utc_now(), normalization_version),
        )
        record_id = cursor.fetchone()[0]
        self.connection.commit()
        return record_id

    def link_source_record(self, entity_id: str, source_record_id: int) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO catalog_entity_sources (entity_id, source_record_id) VALUES (?, ?)",
            (entity_id, source_record_id),
        )
        self.connection.commit()

    def search_entities(self, query: str, entity_type: str | None = None, limit: int = 20) -> list[dict]:
        normalized_query = normalize_identity(query)
        if not normalized_query:
            return []
        type_clause = "AND entity_type = ?" if entity_type else ""
        parameters: list[object] = [normalized_query, normalized_query]
        if entity_type:
            parameters.append(entity_type)
        parameters.append(limit)
        rows = self.connection.execute(
            f"""
            SELECT DISTINCT id, entity_type, title, description, start_date, end_date
            FROM catalog_entities
            WHERE (normalized_title LIKE ? OR id IN (
                SELECT entity_id FROM catalog_aliases WHERE normalized_alias LIKE ?
            )) {type_clause}
            ORDER BY normalized_title, title
            LIMIT ?
            """,
            [f"%{normalized_query}%", f"%{normalized_query}%", *parameters[2:]],
        ).fetchall()
        return [_entity_dict(row) for row in rows]

    def get_entity(self, entity_id: str) -> dict | None:
        row = self.connection.execute(
            "SELECT id, entity_type, title, description, start_date, end_date FROM catalog_entities WHERE id = ?",
            (entity_id,),
        ).fetchone()
        if not row:
            return None

        entity = _entity_dict(row)
        entity["aliases"] = [
            {"value": row[0], "language": row[1]}
            for row in self.connection.execute(
                "SELECT alias, language FROM catalog_aliases WHERE entity_id = ? ORDER BY alias", (entity_id,)
            )
        ]
        entity["identifiers"] = [
            {"type": row[0], "value": row[1]}
            for row in self.connection.execute(
                "SELECT identifier_type, identifier_value FROM catalog_identifiers WHERE entity_id = ? ORDER BY identifier_type, identifier_value",
                (entity_id,),
            )
        ]
        entity["credits"] = [
            {"person_id": row[0], "person": row[1], "role": row[2], "credited_as": row[3]}
            for row in self.connection.execute(
                """
                SELECT credits.person_entity_id, people.title, credits.role, credits.credited_as
                FROM catalog_credits AS credits
                JOIN catalog_entities AS people ON people.id = credits.person_entity_id
                WHERE credits.entity_id = ?
                ORDER BY credits.role, people.title
                """,
                (entity_id,),
            )
        ]
        entity["sources"] = [
            {
                "source": row[0],
                "source_id": row[1],
                "source_url": row[2],
                "retrieved_at": row[3],
                "normalization_version": row[4],
                "attribution": row[5],
            }
            for row in self.connection.execute(
                """
                SELECT records.source, records.source_id, records.source_url, records.retrieved_at,
                       records.normalization_version, sources.attribution
                FROM catalog_entity_sources AS links
                JOIN catalog_source_records AS records ON records.id = links.source_record_id
                LEFT JOIN catalog_sources AS sources ON sources.name = records.source
                WHERE links.entity_id = ?
                ORDER BY records.source
                """,
                (entity_id,),
            )
        ]
        entity["relationships"] = self._relationships(entity_id, entity["entity_type"])
        return entity

    def _relationships(self, entity_id: str, entity_type: str) -> dict:
        if entity_type == "series":
            publisher = self.connection.execute(
                "SELECT publisher_entity_id FROM catalog_series WHERE entity_id = ?", (entity_id,)
            ).fetchone()
            volumes = self.connection.execute(
                """
                SELECT entities.id, entities.entity_type, entities.title, entities.description,
                       entities.start_date, entities.end_date
                FROM catalog_volumes AS volumes
                JOIN catalog_entities AS entities ON entities.id = volumes.entity_id
                WHERE volumes.series_entity_id = ? ORDER BY volumes.volume_number, entities.title
                """,
                (entity_id,),
            ).fetchall()
            return {"publisher_id": publisher[0] if publisher else None, "volumes": [_entity_dict(row) for row in volumes]}
        if entity_type == "volume":
            series = self.connection.execute(
                "SELECT series_entity_id FROM catalog_volumes WHERE entity_id = ?", (entity_id,)
            ).fetchone()
            issues = self.connection.execute(
                """
                SELECT entities.id, entities.entity_type, entities.title, entities.description,
                       entities.start_date, entities.end_date
                FROM catalog_issues AS issues
                JOIN catalog_entities AS entities ON entities.id = issues.entity_id
                WHERE issues.volume_entity_id = ? ORDER BY issues.issue_number, entities.title
                """,
                (entity_id,),
            ).fetchall()
            return {"series_id": series[0] if series else None, "issues": [_entity_dict(row) for row in issues]}
        if entity_type == "issue":
            volume = self.connection.execute(
                "SELECT volume_entity_id, issue_number, publication_date FROM catalog_issues WHERE entity_id = ?",
                (entity_id,),
            ).fetchone()
            return {
                "volume_id": volume[0] if volume else None,
                "issue_number": volume[1] if volume else None,
                "publication_date": volume[2] if volume else None,
            }
        return {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _entity_dict(row: sqlite3.Row | tuple) -> dict:
    return {
        "id": row[0],
        "entity_type": row[1],
        "title": row[2],
        "description": row[3],
        "start_date": row[4],
        "end_date": row[5],
    }