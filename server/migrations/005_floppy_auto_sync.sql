ALTER TABLE tracker_integrations ADD COLUMN auto_sync_enabled INTEGER NOT NULL DEFAULT 0;
ALTER TABLE tracker_integrations ADD COLUMN auto_sync_interval_minutes INTEGER NOT NULL DEFAULT 60;
ALTER TABLE tracker_integrations ADD COLUMN next_sync_at TEXT;