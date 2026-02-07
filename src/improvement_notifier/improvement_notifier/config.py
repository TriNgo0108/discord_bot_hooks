from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    DB_URL: str
    DISCORD_WEBHOOK_IMPROVEMENT: str | None = None
    ENV: str = "production"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # Allow missing for dry-runs/tests, validation will happen in logic if needed
        # But for strictly required vars, it's better to fail early in production.
        # So I will keep it strict and just provide env vars in the run_command.
    )


settings = Settings()
