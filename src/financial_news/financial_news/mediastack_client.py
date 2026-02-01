import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class MediastackClient:
    """
    Client for Mediastack API to retrieve financial news.
    """

    BASE_URL = "https://api.mediastack.com/v2"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("MEDIASTACK_API_KEY")
        if not self.api_key:
            logger.warning("MEDIASTACK_API_KEY not set. Mediastack functionality will be disabled.")

        self.client = httpx.Client(timeout=30.0)

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def _get_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Add API key to params."""
        p = params.copy()
        if self.api_key:
            p["access_key"] = self.api_key
        return p

    def get_live_news(
        self,
        keywords: str | None = None,
        categories: str = "business",
        countries: str | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        """
        Get live news articles.

        Args:
            keywords: Keywords to search for.
            categories: Comma-separated categories (e.g. 'business,technology').
            countries: Comma-separated country codes (e.g. 'us,vn,au').
            limit: Number of results (max 100).
        """
        if not self.api_key:
            return {}

        url = f"{self.BASE_URL}/news"
        params = {"categories": categories, "limit": limit, "sort": "published_desc"}

        if keywords:
            params["keywords"] = keywords
        if countries:
            params["countries"] = countries

        try:
            response = self.client.get(url, params=self._get_params(params))
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching Mediastack news: {e}")
            return {}
