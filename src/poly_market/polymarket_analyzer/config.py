"""Configuration for Polymarket integration."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class PolymarketConfig:
    """Polymarket API configuration."""

    # API Base URLs
    GAMMA_API_BASE: str = "https://gamma-api.polymarket.com"
    CLOB_API_BASE: str = "https://clob.polymarket.com"

    # Fetch limits
    MAX_EVENTS: int = 20
    MAX_MARKETS_PER_EVENT: int = 10

    # Research settings
    RESEARCH_CONCURRENCY: int = 5
    REQUEST_TIMEOUT: int = 30

    # Cache TTL in seconds
    CACHE_TTL: int = 300  # 5 minutes

    # Results directory for excluding already-analyzed events
    RESULTS_DIR: str = "results"


@dataclass(frozen=True)
class AIConfig:
    """AI services configuration."""

    # Z.AI (ZhipuAI) settings - GLM-4.7
    ZAI_API_KEY: str = ""
    ZAI_MODEL: str = "glm-4.7"
    ZAI_BASE_URL: str = "https://api.z.ai/api/coding/paas/v4"

    # Perplexity Search API settings (web search only)
    PERPLEXITY_API_KEY: str = ""
    PERPLEXITY_BASE_URL: str = "https://api.perplexity.ai"

    # Tavily Search API
    TAVILY_API_KEY: str = ""

    # WebSearchAPI.ai settings
    WEBSEARCHAPI_KEY: str = ""

    # Search Provider: "tavily" or "websearchapi" (replaces ddg)
    SEARCH_PROVIDER: str = "tavily"

    @classmethod
    def from_env(cls) -> "AIConfig":
        """Load configuration from environment variables."""
        return cls(
            ZAI_API_KEY=os.getenv("ZAI_API_KEY", ""),
            ZAI_MODEL=os.getenv("ZAI_MODEL", "glm-4.7"),
            PERPLEXITY_API_KEY=os.getenv("PERPLEXITY_API_KEY", ""),
            TAVILY_API_KEY=os.getenv("TAVILY_API_KEY", ""),
            WEBSEARCHAPI_KEY=os.getenv("WEBSEARCHAPI_KEY", ""),
            SEARCH_PROVIDER=os.getenv("SEARCH_PROVIDER", "tavily").lower(),
        )


# Default instances
POLYMARKET_CONFIG = PolymarketConfig()
