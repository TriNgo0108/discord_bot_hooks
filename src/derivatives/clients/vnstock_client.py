"""Client for Vietnam derivatives data using vnstock."""

import logging
from datetime import datetime
from typing import Any

from vnstock import Vnstock

from ..models import FuturesContract

logger = logging.getLogger(__name__)


class VNStockClient:
    """Client for Vietnam derivatives data."""

    def __init__(self):
        pass

    async def fetch_futures_list(self) -> list[dict[str, Any]]:
        """Fetch list of available futures contracts."""
        # This seems hard to get generic list without source,
        # defaulting to returning empty or known list if needed.
        # For now, just return empty list as we rely on explicit symbols in main.
        return []

    async def fetch_latest_price(self, symbol: str) -> FuturesContract | None:
        """
        Fetch latest price and data for a specific futures contract.
        Uses Vnstock class.
        """
        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            start_str = "2024-01-01"  # Arbitrary start to ensure we get *some* history if strictly needed, but we mostly need latest.

            # Using VCI as source which seems reliable for this
            stock = Vnstock().stock(symbol=symbol, source="VCI")

            # Fetch history
            df = stock.quote.history(start=start_str, end=today_str, interval="1D")

            if df is None or df.empty:
                logger.warning(f"No match data found for {symbol}")
                return None

            # Get latest row
            latest = df.iloc[-1]

            # Map columns: time, open, high, low, close, volume, ticker
            return FuturesContract(
                symbol=symbol,
                underlying="VN30",
                last_price=float(latest.get("close", 0)),
                open_interest=0,  # OI not available in standard history usually
                volume_24h=float(latest.get("volume", 0)),
                source="vnstock",
            )

        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None

    async def get_market_snapshot(self, symbol: str = "VN30F1M") -> dict | None:
        """
        Get a snapshot of the market for the main active contract.
        This adapts to the 'market_structure' expectation of the aggregator.
        """
        try:
            # We can use the price data as the structure for now
            contract = await self.fetch_latest_price(symbol)
            if contract:
                return contract.__dict__
            return None
        except Exception as e:
            logger.error(f"Error getting snapshot: {e}")
            return None

    async def close(self):
        """No-op for compatibility."""
        pass
