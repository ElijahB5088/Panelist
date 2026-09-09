CREATE TABLE IF NOT EXISTS catalog_entities (
  id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL CHECK (entity_type IN ('series', 'volume', 'issue', 'person', 'publisher', 'edition')),
  title TEXT NOT NULL,
  normalized_title TEXT NOT NULL,
  description TEXT,
  start_date TEXT,
  end_date TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS catalog_entities_title ON catalog_entities(normalized_title);

CREATE TABLE IF NOT EXISTS catalog_series (
  entity_id TEXT PRIMARY KEY,
  publisher_entity_id TEXT,
  FOREIGN KEY(entity_id) REFERENCES catalog_entities(id) ON DELETE CASCADE,
  FOREIGN KEY(publisher_entity_id) REFERENCES catalog_entities(id)
);

CREATE TABLE IF NOT EXISTS catalog_volumes (
  entity_id TEXT PRIMARY KEY,
  series_entity_id TEXT NOT NULL,
  volume_number TEXT,
  FOREIGN KEY(entity_id) REFERENCES catalog_entities(id) ON DELETE CASCADE,
  FOREIGN KEY(series_entity_id) REFERENCES catalog_entities(id)
);

CREATE INDEX IF NOT EXISTS catalog_volumes_series ON catalog_volumes(series_entity_id, volume_number);

CREATE TABLE IF NOT EXISTS catalog_issues (
  entity_id TEXT PRIMARY KEY,
  volume_entity_id TEXT NOT NULL,
  issue_number TEXT,
  publication_date TEXT,
  FOREIGN KEY(entity_id) REFERENCES catalog_entities(id) ON DELETE CASCADE,
  FOREIGN KEY(volume_entity_id) REFERENCES catalog_entities(id)
);

CREATE INDEX IF NOT EXISTS catalog_issues_volume ON catalog_issues(volume_entity_id, issue_number);

CREATE TABLE IF NOT EXISTS catalog_aliases (
  entity_id TEXT NOT NULL,
  alias TEXT NOT NULL,
  normalized_alias TEXT NOT NULL,
  language TEXT,
  PRIMARY KEY(entity_id, alias),
  FOREIGN KEY(entity_id) REFERENCES catalog_entities(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS catalog_aliases_search ON catalog_aliases(normalized_alias);

CREATE TABLE IF NOT EXISTS catalog_identifiers (
  entity_id TEXT NOT NULL,
  identifier_type TEXT NOT NULL,
  identifier_value TEXT NOT NULL,
  PRIMARY KEY(identifier_type, identifier_value),
  FOREIGN KEY(entity_id) REFERENCES catalog_entities(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS catalog_credits (
  entity_id TEXT NOT NULL,
  person_entity_id TEXT NOT NULL,
  role TEXT NOT NULL,
  credited_as TEXT,
  PRIMARY KEY(entity_id, person_entity_id, role),
  FOREIGN KEY(entity_id) REFERENCES catalog_entities(id) ON DELETE CASCADE,
  FOREIGN KEY(person_entity_id) REFERENCES catalog_entities(id)
);

CREATE INDEX IF NOT EXISTS catalog_credits_person ON catalog_credits(person_entity_id);

CREATE TABLE IF NOT EXISTS catalog_sources (
  name TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  source_url TEXT,
  attribution TEXT
);

CREATE TABLE IF NOT EXISTS catalog_source_records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  source_id TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  source_url TEXT,
  retrieved_at TEXT NOT NULL,
  normalization_version TEXT NOT NULL,
  FOREIGN KEY(source) REFERENCES catalog_sources(name),
  UNIQUE(source, source_id)
);

CREATE TABLE IF NOT EXISTS catalog_entity_sources (
  entity_id TEXT NOT NULL,
  source_record_id INTEGER NOT NULL,
  PRIMARY KEY(entity_id, source_record_id),
  FOREIGN KEY(entity_id) REFERENCES catalog_entities(id) ON DELETE CASCADE,
  FOREIGN KEY(source_record_id) REFERENCES catalog_source_records(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS catalog_entity_sources_record ON catalog_entity_sources(source_record_id);