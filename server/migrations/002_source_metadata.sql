ALTER TABLE media ADD COLUMN source TEXT;
ALTER TABLE media ADD COLUMN source_id TEXT;
ALTER TABLE media ADD COLUMN image_url TEXT;
ALTER TABLE media ADD COLUMN source_url TEXT;

CREATE INDEX IF NOT EXISTS media_source_identity
ON media(source, source_id);
