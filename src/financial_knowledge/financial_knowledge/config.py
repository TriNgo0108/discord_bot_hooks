"""Configuration for Financial Knowledge Hook."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Application configuration."""

    # API Keys
    ZAI_API_KEY: str | None = os.getenv("ZAI_API_KEY")
    TAVILY_API_KEY: str | None = os.getenv("TAVILY_API_KEY")

    # Discord Webhook
    DISCORD_WEBHOOK_URL: str | None = os.getenv("DISCORD_WEBHOOK_FINANCE_KNOWLEDGE")

    # App Settings
    ENV: str = os.getenv("ENV", "development")

    @classmethod
    def from_env(cls) -> "Config":
        return cls()
