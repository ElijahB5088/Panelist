CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS tracker_integrations (
  user_id INTEGER PRIMARY KEY,
  provider TEXT NOT NULL,
  server_url TEXT NOT NULL,
  encrypted_token TEXT NOT NULL,
  connected INTEGER NOT NULL DEFAULT 0,
  last_sync_at TEXT,
  sync_status TEXT,
  sync_error TEXT,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS media (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  creator TEXT,
  genres TEXT,
  publisher TEXT,
  description TEXT,
  rating REAL,
  popularity REAL,
  release_date TEXT
);

CREATE TABLE IF NOT EXISTS user_library (
  user_id INTEGER NOT NULL,
  media_id TEXT NOT NULL,
  status TEXT,
  progress INTEGER,
  user_rating REAL,
  PRIMARY KEY (user_id, media_id),
  FOREIGN KEY(user_id) REFERENCES users(id),
  FOREIGN KEY(media_id) REFERENCES media(id)
);

CREATE TABLE IF NOT EXISTS recommendation_feedback (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  media_id TEXT NOT NULL,
  feedback TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id),
  FOREIGN KEY(media_id) REFERENCES media(id)
);
