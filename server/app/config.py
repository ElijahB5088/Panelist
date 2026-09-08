import os


class Settings:
    environment = os.getenv("PANELIST_ENV", "development").lower()
    host = os.getenv("PANELIST_HOST", "0.0.0.0")
    port = int(os.getenv("PANELIST_PORT", "8080"))
    secret_key = os.getenv("PANELIST_SECRET_KEY", "dev-secret")
    database_url = os.getenv("DATABASE_URL", "sqlite:///data/panelist.db")
    sync_interval_minutes = int(os.getenv("SYNC_INTERVAL_MINUTES", "60"))
    sync_interval_min_minutes = 15
    sync_interval_max_minutes = 10080
    credential_encryption_key = os.getenv("CREDENTIAL_ENCRYPTION_KEY", "")
    comicvine_api_key = os.getenv("COMICVINE_API_KEY", "")
    metron_api_url = os.getenv("METRON_API_URL", "https://metron.cloud/api")
    metron_api_token = os.getenv("METRON_API_TOKEN", "")
    metadata_user_agent = os.getenv("METADATA_USER_AGENT", "Panelist/0.1 (self-hosted)")
    metadata_cache_ttl_seconds = int(os.getenv("METADATA_CACHE_TTL_SECONDS", "900"))
    metadata_cache_max_entries = int(os.getenv("METADATA_CACHE_MAX_ENTRIES", "256"))
    metadata_upstream_interval_seconds = float(os.getenv("METADATA_UPSTREAM_INTERVAL_SECONDS", "1"))
    metadata_client_window_seconds = int(os.getenv("METADATA_CLIENT_WINDOW_SECONDS", "60"))
    metadata_client_max_requests = int(os.getenv("METADATA_CLIENT_MAX_REQUESTS", "30"))
    mal_client_id = os.getenv("MAL_CLIENT_ID", "")
    mal_client_secret = os.getenv("MAL_CLIENT_SECRET", "")
    mal_redirect_uri = os.getenv("MAL_REDIRECT_URI", "http://localhost:8080/api/integrations/mal/callback")
    trusted_proxy_headers = os.getenv("TRUSTED_PROXY_HEADERS", "false").lower() == "true"

    def validate_runtime(self) -> None:
        if self.environment not in {"production", "prod"}:
            return
        if self.secret_key in {"", "dev-secret", "replace-this-with-a-long-random-value"}:
            raise RuntimeError("PANELIST_SECRET_KEY must be configured in production")
        if not self.credential_encryption_key:
            raise RuntimeError("CREDENTIAL_ENCRYPTION_KEY must be configured in production")


settings = Settings()
