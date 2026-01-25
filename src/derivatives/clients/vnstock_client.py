"""Client for Vietnam derivatives data using vnstock."""

import logging
from datetime import datetime, timedelta
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
        Uses explicit date filtering to ensure data freshness.
        """
        try:
            # Use rolling window of 7 days to get recent data
            current_time = datetime.now()
            start_date = current_time - timedelta(days=7)

            start_str = start_date.strftime("%Y-%m-%d")
            end_str = current_time.strftime("%Y-%m-%d")

            # Try VCI first as it was verified to work
            source = "VCI"
            try:
                stock = Vnstock().stock(symbol=symbol, source=source)
                df = stock.quote.history(start=start_str, end=end_str, interval="1D")
            except Exception:
                # Fallback to TCBS if VCI fails
                source = "TCBS"
                stock = Vnstock().stock(symbol=symbol, source=source)
                df = stock.quote.history(start=start_str, end=end_str, interval="1D")

            if df is None or df.empty:
                logger.warning(f"No recent data found for {symbol} (Source: {source})")
                return None

            print(f"DEBUG DATA for {symbol} (Source: {source}):")
            print(df.tail(3))
            print(df.columns)

            # Get latest row
            latest = df.iloc[-1]

            # Check for staleness
            data_date_val = latest.get("time")
            data_date = None
            is_stale = False

            if data_date_val:
                if isinstance(data_date_val, str):
                    try:
                        data_date = datetime.strptime(data_date_val, "%Y-%m-%d")
                    except ValueError:
                        pass
                else:
                    data_date = data_date_val

                if data_date:
                    days_diff = (current_time - data_date).days
                    if days_diff > 3:
                        is_stale = True
                        logger.warning(
                            f"Data for {symbol} is stale! ({days_diff} days old). Date: {data_date_val}"
                        )

            # Map columns: time, open, high, low, close, volume, ticker
            return FuturesContract(
                symbol=symbol,
                underlying="VN30",
                last_price=float(latest.get("close", 0)),
                open_interest=0,  # OI not available in standard history usually
                volume_24h=float(latest.get("volume", 0)),
                source=f"vnstock_{source}",
                data_date=data_date,
                is_stale=is_stale,
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
