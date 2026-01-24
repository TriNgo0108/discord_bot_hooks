"""
Stock client for fetching Vietnam stock prices using DSC Securities API.
"""

import datetime
import logging
from dataclasses import dataclass, field
from typing import Any

from .dsc_client import DSCClient

logger = logging.getLogger(__name__)


@dataclass
class StockPrice:
    """Stock price data."""

    symbol: str
    price: float
    change: float
    change_percent: float
    volume: int
    date: str


@dataclass
class StockInfo:
    """Stock fundamental information."""

    symbol: str
    company_name: str = ""
    industry: str = ""
    exchange: str = ""
    market_cap: float = 0.0
    pe_ratio: float = 0.0
    pb_ratio: float = 0.0
    eps: float = 0.0
    roe: float = 0.0
    is_vn30: bool = False


class StockClient:
    """
    Client to fetch Vietnam stock prices from DSC Securities API.
    Provides real-time data without rate limits.
    """

    def __init__(self, source: str = "VCI"):
        self.source = source
        self._vn30_cache: set[str] | None = None
        self.dsc_client = DSCClient()

    def get_vn30_symbols(self) -> set[str]:
        """Get list of VN30 index component symbols."""
        if self._vn30_cache is None:
            try:
                symbols = self.dsc_client.get_vn30_symbols()
                self._vn30_cache = set(symbols)
                logger.info(f"Loaded {len(self._vn30_cache)} VN30 symbols from DSC")
            except Exception as e:
                logger.error(f"Error fetching VN30 symbols: {e}")
                self._vn30_cache = set()
        return self._vn30_cache

    def is_vn30(self, symbol: str) -> bool:
        """Check if a stock is in the VN30 index."""
        return symbol.upper() in self.get_vn30_symbols()

    def get_stock_info(self, symbol: str) -> StockInfo | None:
        """
        Fetch company fundamentals via DSC (limited info compared to vnstock).
        """
        try:
            info = self.dsc_client.get_stock_info(symbol)
            if not info:
                return None

            return StockInfo(
                symbol=info.get("symbol", symbol),
                company_name=info.get("company_name", ""),
                industry=info.get("industry", ""),
                exchange=info.get("exchange", ""),
                market_cap=info.get("market_cap", 0.0),
                pe_ratio=0.0,
                pb_ratio=0.0,
                eps=0.0,
                roe=0.0,
                is_vn30=self.is_vn30(symbol),
            )
        except Exception as e:
            logger.error(f"Error fetching stock info for {symbol}: {e}")
            return None

    def get_stock_price(self, symbol: str) -> StockPrice | None:
        """
        Fetch current price data for a single stock using DSC Client (No rate limit).

        Args:
            symbol: Stock symbol (e.g., 'FPT', 'VIC', 'MWG')

        Returns:
            StockPrice object with price, change, and volume data.
        """
        try:
            stock_data = self.dsc_client.get_stock_price(symbol)
            if stock_data:
                return StockPrice(
                    symbol=stock_data.symbol,
                    price=stock_data.price,
                    change=stock_data.change,
                    change_percent=stock_data.change_percent,
                    volume=stock_data.volume,
                    date=stock_data.last_update or datetime.datetime.now().strftime("%H:%M:%S"),
                )
            return None
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None

    def get_stock_prices(self, symbols: list[str]) -> dict[str, StockPrice]:
        """
        Fetch prices for multiple stocks using DSC Client (Efficient).

        Args:
            symbols: List of stock symbols

        Returns:
            Dictionary mapping symbol to StockPrice object.
        """
        try:
            dsc_prices = self.dsc_client.get_stock_prices(symbols)
            results = {}
            for sym, data in dsc_prices.items():
                results[sym] = StockPrice(
                    symbol=data.symbol,
                    price=data.price,
                    change=data.change,
                    change_percent=data.change_percent,
                    volume=data.volume,
                    date=data.last_update or datetime.datetime.now().strftime("%H:%M:%S"),
                )
            return results
        except Exception as e:
            logger.error(f"Error fetching stock prices: {e}")
            return {}

    def enrich_fund_holdings(self, holdings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Enrich fund holdings data with live stock prices.

        Args:
            holdings: List of holdings from fmarket (with 'stock_code' key)

        Returns:
            Holdings with added live price data and comparison.
        """
        # Extract unique stock codes
        stock_codes = [h.get("stock_code") for h in holdings if h.get("stock_code")]
        stock_codes = list(set(stock_codes))

        # Fetch live prices
        live_prices = self.get_stock_prices(stock_codes)

        # Enrich holdings
        enriched = []
        for holding in holdings:
            code = holding.get("stock_code")
            enriched_holding = holding.copy()

            if code and code in live_prices:
                live = live_prices[code]
                enriched_holding["live_price"] = live.price
                enriched_holding["live_change"] = live.change
                enriched_holding["live_change_percent"] = live.change_percent
                enriched_holding["live_volume"] = live.volume

                # Compare fmarket price with live price
                fmarket_price = holding.get("price", 0)
                if fmarket_price and live.price:
                    price_diff = live.price - fmarket_price
                    enriched_holding["price_diff"] = round(price_diff, 2)
                    enriched_holding["price_diff_percent"] = (
                        round((price_diff / fmarket_price) * 100, 2) if fmarket_price > 0 else 0
                    )

            enriched.append(enriched_holding)

        return enriched

    def get_vn30_index_history(self, days: int = 30) -> list[dict[str, Any]]:
        """
        Fetch VN30 index historical data.
        NOTE: DSC API does not provide 30-day daily history publicly.
        Returning empty list until a history endpoint is found.
        """
        logger.warning("VN30 index history temporarily unavailable with DSC client")
        return []

    def get_vn30_top_movers(self, limit: int = 5) -> dict[str, list[dict[str, Any]]]:
        """
        Get top gainers and losers among VN30 stocks.

        Note: Uses pre-cached price data to minimize API calls.

        Args:
            limit: Number of top stocks to return

        Returns:
            Dict with 'gainers' and 'losers' lists.
        """
        vn30_symbols = list(self.get_vn30_symbols())

        # Fetch prices for all VN30 stocks
        prices = self.get_stock_prices(vn30_symbols)

        # Convert to list and sort
        stock_list = [
            {
                "symbol": p.symbol,
                "price": p.price,
                "change": p.change,
                "change_percent": p.change_percent,
                "volume": p.volume,
            }
            for p in prices.values()
        ]

        sorted_by_change = sorted(stock_list, key=lambda x: x["change_percent"], reverse=True)

        return {
            "gainers": sorted_by_change[:limit],
            "losers": sorted_by_change[-limit:][::-1],  # Reverse to show worst first
        }
