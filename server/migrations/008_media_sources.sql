CREATE TABLE IF NOT EXISTS media_sources (
  media_id TEXT NOT NULL,
  source TEXT NOT NULL,
  source_id TEXT NOT NULL,
  source_url TEXT,
  PRIMARY KEY (source, source_id),
  FOREIGN KEY(media_id) REFERENCES media(id)
);

CREATE TABLE IF NOT EXISTS media_source_conflicts (
  source TEXT NOT NULL,
  source_id TEXT NOT NULL,
  media_id TEXT NOT NULL,
  conflicting_media_id TEXT NOT NULL,
  PRIMARY KEY (source, source_id, media_id, conflicting_media_id),
  FOREIGN KEY(media_id) REFERENCES media(id),
  FOREIGN KEY(conflicting_media_id) REFERENCES media(id)
);

INSERT OR IGNORE INTO media_source_conflicts (source, source_id, media_id, conflicting_media_id)
SELECT first.source, first.source_id, first.id, second.id
FROM media AS first
JOIN media AS second
  ON first.source = second.source
 AND first.source_id = second.source_id
 AND first.id < second.id
WHERE first.source IS NOT NULL
  AND first.source_id IS NOT NULL
  AND first.source <> ''
  AND first.source_id <> '';

INSERT OR IGNORE INTO media_sources (media_id, source, source_id, source_url)
SELECT MIN(id), source, source_id, MIN(source_url)
FROM media
WHERE source IS NOT NULL
  AND source_id IS NOT NULL
  AND source <> ''
  AND source_id <> ''
GROUP BY source, source_id;

CREATE INDEX IF NOT EXISTS media_sources_media_id
ON media_sources(media_id);