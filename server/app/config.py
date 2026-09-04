import os


class Settings:
    host = os.getenv("NEXTPANEL_HOST", "0.0.0.0")
    port = int(os.getenv("NEXTPANEL_PORT", "8080"))
    secret_key = os.getenv("NEXTPANEL_SECRET_KEY", "dev-secret")
    database_url = os.getenv("DATABASE_URL", "sqlite:///data/nextpanel.db")
    sync_interval_minutes = int(os.getenv("SYNC_INTERVAL_MINUTES", "60"))
    credential_encryption_key = os.getenv("CREDENTIAL_ENCRYPTION_KEY", "")


settings = Settings()
