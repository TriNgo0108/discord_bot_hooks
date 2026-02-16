"""Configuration for Tech Interview Hook."""

import os
from dataclasses import dataclass


@dataclass
class Config:
    """Application configuration."""

    # API Keys
    ZAI_API_KEY: str | None = os.getenv("ZAI_API_KEY")
    TAVILY_API_KEY: str | None = os.getenv("TAVILY_API_KEY")

    # Discord Webhook
    DISCORD_WEBHOOK_URL: str | None = os.getenv("DISCORD_WEBHOOK_TECH_INTERVIEW")

    # App Settings
    ENV: str = os.getenv("ENV", "development")

    @classmethod
    def from_env(cls) -> "Config":
        return cls()
