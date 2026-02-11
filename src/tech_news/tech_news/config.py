"""Configuration for Tech News Hook."""

from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Application settings."""

    DISCORD_WEBHOOK_TECH_NEWS: str
    TAVILY_API_KEY: str
    ZAI_API_KEY: str

    class Config:
        """Pydantic config."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore other env vars

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls()
