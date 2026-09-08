ALTER TABLE user_library ADD COLUMN added_at TEXT;

UPDATE user_library
SET added_at = datetime('now')
WHERE added_at IS NULL;