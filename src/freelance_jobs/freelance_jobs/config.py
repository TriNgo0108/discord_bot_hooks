"""Configuration for Freelance Jobs Hook."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Application configuration."""

    # API Keys
    TAVILY_API_KEY: str | None = os.getenv("TAVILY_API_KEY")

    # Discord Webhook
    DISCORD_WEBHOOK_URL: str | None = os.getenv("DISCORD_WEBHOOK_FREELANCE_JOBS")

    # App Settings
    ENV: str = os.getenv("ENV", "development")

    @classmethod
    def from_env(cls) -> "Config":
        return cls()
