CREATE TABLE IF NOT EXISTS mal_oauth_states (
  state TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL,
  code_verifier TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS mal_oauth_states_expiry ON mal_oauth_states(expires_at);
