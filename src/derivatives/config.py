"""Configuration for derivatives data integration."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DerivativesConfig:
    """Configuration for derivatives data sources."""

    # API Keys (optional - most sources are free without keys)
    # Alpha Vantage Key (Free tier: 25 requests/day)
    ALPHA_VANTAGE_API_KEY: str = os.getenv("ALPHA_VANTAGE_API_KEY", "")

    # Finnhub Key (Free tier: 60 requests/minute)
    FINNHUB_API_KEY: str = os.getenv("FINNHUB_API_KEY", "")

    # Government sources
    CFTC_COT_URL: str = "https://www.cftc.gov/dea/futures/deacbt.htm"
    # Alternative COT source if official site is down/slow
    NASDAQ_DATA_LINK_API_KEY: str = os.getenv("NASDAQ_DATA_LINK_API_KEY", "")

    # AI Configuration matches existing project patterns
    # AI Configuration matches existing project patterns
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    ZAI_API_KEY: str = os.getenv("ZAI_API_KEY", "")

    # Notification
    DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_DERIVATIVES")

    # Rate limiting & Retries
    REQUEST_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 2


# Default instance
DERIVATIVES_CONFIG = DerivativesConfig()
