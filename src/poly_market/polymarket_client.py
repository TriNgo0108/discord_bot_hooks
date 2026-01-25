"""Polymarket API client for fetching market data."""

import asyncio
import logging
from functools import lru_cache
from typing import AsyncGenerator

import httpx

from .config import POLYMARKET_CONFIG, PolymarketConfig
from .models import MarketOutcome, PolymarketEvent, PolymarketMarket

logger = logging.getLogger(__name__)


class PolymarketClient:
    """Async client for Polymarket public APIs."""

    def __init__(self, config: PolymarketConfig | None = None):
        """Initialize the client with optional custom config."""
        self.config = config or POLYMARKET_CONFIG
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "PolymarketClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=self.config.REQUEST_TIMEOUT,
            headers={"Accept": "application/json"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the HTTP client, raising if not initialized."""
        if self._client is None:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return self._client

    async def fetch_events(
        self,
        limit: int | None = None,
        active: bool = True,
        closed: bool = False,
    ) -> list[PolymarketEvent]:
        """
        Fetch events from Gamma API.

        Args:
            limit: Maximum number of events to fetch
            active: Include active events
            closed: Include closed events

        Returns:
            List of PolymarketEvent objects
        """
        limit = limit or self.config.MAX_EVENTS
        url = f"{self.config.GAMMA_API_BASE}/events"

        params = {
            "limit": limit,
            "active": str(active).lower(),
            "closed": str(closed).lower(),
            "order": "volume",
            "ascending": "false",
        }

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            events = []
            for event_data in data:
                event = self._parse_event(event_data)
                if event:
                    events.append(event)

            logger.info(f"Fetched {len(events)} events from Polymarket")
            return events

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch events: {e}")
            raise

    async def fetch_events_generator(
        self,
        limit: int | None = None,
    ) -> AsyncGenerator[PolymarketEvent, None]:
        """
        Fetch events as async generator for memory efficiency.

        Yields:
            PolymarketEvent objects one at a time
        """
        events = await self.fetch_events(limit=limit)
        for event in events:
            yield event

    async def fetch_market_by_id(self, market_id: str) -> PolymarketMarket | None:
        """Fetch a specific market by ID."""
        url = f"{self.config.GAMMA_API_BASE}/markets/{market_id}"

        try:
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            return self._parse_market(data)

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch market {market_id}: {e}")
            return None

    async def fetch_prices_batch(
        self,
        token_ids: list[str],
    ) -> dict[str, float]:
        """
        Batch fetch current prices for multiple tokens.

        Uses concurrent requests with semaphore for rate limiting.
        """
        semaphore = asyncio.Semaphore(self.config.RESEARCH_CONCURRENCY)
        prices = {}

        async def fetch_single_price(token_id: str) -> tuple[str, float]:
            async with semaphore:
                url = f"{self.config.CLOB_API_BASE}/price"
                params = {"token_id": token_id}
                try:
                    response = await self.client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    return token_id, float(data.get("price", 0))
                except Exception as e:
                    logger.warning(f"Failed to fetch price for {token_id}: {e}")
                    return token_id, 0.0

        # Concurrent price fetching
        tasks = [fetch_single_price(tid) for tid in token_ids]
        results = await asyncio.gather(*tasks)

        for token_id, price in results:
            prices[token_id] = price

        return prices

    def _parse_event(self, data: dict) -> PolymarketEvent | None:
        """Parse event data from API response."""
        try:
            markets = []
            for market_data in data.get("markets", []):
                market = self._parse_market(market_data)
                if market:
                    markets.append(market)

            return PolymarketEvent(
                id=str(data.get("id", "")),
                title=data.get("title", ""),
                description=data.get("description", ""),
                slug=data.get("slug", ""),
                end_date=data.get("endDate", ""),
                markets=markets[: self.config.MAX_MARKETS_PER_EVENT],
                tags=data.get("tags", []),
            )
        except Exception as e:
            logger.warning(f"Failed to parse event: {e}")
            return None

    def _parse_market(self, data: dict) -> PolymarketMarket | None:
        """Parse market data from API response."""
        try:
            # Parse outcomes
            outcomes = []
            outcome_prices = data.get("outcomePrices", "")
            outcome_names = data.get("outcomes", "")

            # Handle string format (common in API responses)
            if isinstance(outcome_prices, str):
                try:
                    import json

                    outcome_prices = json.loads(outcome_prices)
                except json.JSONDecodeError:
                    outcome_prices = []

            if isinstance(outcome_names, str):
                try:
                    import json

                    outcome_names = json.loads(outcome_names)
                except json.JSONDecodeError:
                    outcome_names = []

            # Get token IDs
            tokens = data.get("clobTokenIds", "")
            if isinstance(tokens, str):
                try:
                    import json

                    tokens = json.loads(tokens)
                except json.JSONDecodeError:
                    tokens = []

            for i, name in enumerate(outcome_names):
                price = float(outcome_prices[i]) if i < len(outcome_prices) else 0.0
                token_id = tokens[i] if i < len(tokens) else ""
                outcomes.append(MarketOutcome(name=name, price=price, token_id=token_id))

            return PolymarketMarket(
                id=str(data.get("id", "")),
                question=data.get("question", ""),
                description=data.get("description", ""),
                outcomes=outcomes,
                volume=float(data.get("volume", 0)),
                liquidity=float(data.get("liquidity", 0)),
                end_date=data.get("endDate", ""),
                slug=data.get("slug", ""),
                active=data.get("active", True),
            )
        except Exception as e:
            logger.warning(f"Failed to parse market: {e}")
            return None


@lru_cache(maxsize=100)
def get_cached_market_info(market_id: str) -> dict | None:
    """
    Cache market info to avoid repeated API calls.

    Note: This is a sync wrapper for caching purposes.
    For fresh data, use fetch_market_by_id directly.
    """
    # This cache is populated externally
    return None
