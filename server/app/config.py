import os


class Settings:
    host = os.getenv("PANELIST_HOST", "0.0.0.0")
    port = int(os.getenv("PANELIST_PORT", "8080"))
    secret_key = os.getenv("PANELIST_SECRET_KEY", "dev-secret")
    database_url = os.getenv("DATABASE_URL", "sqlite:///data/panelist.db")
    sync_interval_minutes = int(os.getenv("SYNC_INTERVAL_MINUTES", "60"))
    credential_encryption_key = os.getenv("CREDENTIAL_ENCRYPTION_KEY", "")
    comicvine_api_key = os.getenv("COMICVINE_API_KEY", "")
    metadata_user_agent = os.getenv("METADATA_USER_AGENT", "Panelist/0.1 (self-hosted)")
    metadata_cache_ttl_seconds = int(os.getenv("METADATA_CACHE_TTL_SECONDS", "900"))
    metadata_cache_max_entries = int(os.getenv("METADATA_CACHE_MAX_ENTRIES", "256"))
    metadata_upstream_interval_seconds = float(os.getenv("METADATA_UPSTREAM_INTERVAL_SECONDS", "1"))
    metadata_client_window_seconds = int(os.getenv("METADATA_CLIENT_WINDOW_SECONDS", "60"))
    metadata_client_max_requests = int(os.getenv("METADATA_CLIENT_MAX_REQUESTS", "30"))


settings = Settings()
