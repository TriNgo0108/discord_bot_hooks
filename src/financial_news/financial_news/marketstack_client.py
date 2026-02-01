import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class MarketstackClient:
    """
    Client for Marketstack API to retrieve stock market data.
    """

    BASE_URL = "https://api.marketstack.com/v2"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("MARKETSTACK_API_KEY")
        if not self.api_key:
            logger.warning(
                "MARKETSTACK_API_KEY not set. Marketstack functionality will be disabled."
            )

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

    def get_intraday(self, symbol: str, limit: int = 1) -> dict[str, Any]:
        """
        Get intraday data for a symbol.
        Note: Free plan might not support intraday for all exchanges.
        """
        if not self.api_key:
            return {}

        url = f"{self.BASE_URL}/intraday"
        params = {"symbols": symbol, "limit": limit}

        try:
            response = self.client.get(url, params=self._get_params(params))
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching Marketstack intraday for {symbol}: {e}")
            return {}

    def get_eod(self, symbol: str, limit: int = 1) -> dict[str, Any]:
        """
        Get End-of-Day data for a symbol.
        """
        if not self.api_key:
            return {}

        url = f"{self.BASE_URL}/eod"
        params = {"symbols": symbol, "limit": limit}

        try:
            response = self.client.get(url, params=self._get_params(params))
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching Marketstack EOD for {symbol}: {e}")
            return {}
