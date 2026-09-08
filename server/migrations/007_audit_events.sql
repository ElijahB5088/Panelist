CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    outcome TEXT NOT NULL DEFAULT 'success',
    details TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_events_user_created
    ON audit_events(user_id, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_type_created
    ON audit_events(event_type, created_at DESC, id DESC);
