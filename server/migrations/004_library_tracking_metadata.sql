ALTER TABLE media ADD COLUMN media_type TEXT;
ALTER TABLE media ADD COLUMN tracker_source TEXT;
ALTER TABLE media ADD COLUMN tracker_media_id TEXT;
ALTER TABLE media ADD COLUMN tracker_item_id TEXT;

ALTER TABLE user_library ADD COLUMN progress_max INTEGER;
ALTER TABLE user_library ADD COLUMN progress_unit TEXT;
ALTER TABLE user_library ADD COLUMN progress_scope TEXT;
ALTER TABLE user_library ADD COLUMN progress_percent INTEGER;

CREATE INDEX IF NOT EXISTS media_tracker_identity
ON media(tracker_source, media_type, tracker_media_id);