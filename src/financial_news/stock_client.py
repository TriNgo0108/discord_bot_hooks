"""
Stock client for fetching Vietnam stock prices using vnstock library.
"""

import datetime
import logging
from dataclasses import dataclass, field
from typing import Any

from vnstock import Listing, Vnstock

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
    Client to fetch Vietnam stock prices from vnstock library.
    Uses VCI source for reliable daily data.
    """

    def __init__(self, source: str = "VCI"):
        self.source = source
        self._vn30_cache: set[str] | None = None

    def get_vn30_symbols(self) -> set[str]:
        """Get list of VN30 index component symbols."""
        if self._vn30_cache is None:
            try:
                listing = Listing()
                vn30_series = listing.symbols_by_group(group="VN30")
                self._vn30_cache = set(vn30_series.tolist())
                logger.info(f"Loaded {len(self._vn30_cache)} VN30 symbols")
            except Exception as e:
                logger.error(f"Error fetching VN30 symbols: {e}")
                self._vn30_cache = set()
        return self._vn30_cache

    def is_vn30(self, symbol: str) -> bool:
        """Check if a stock is in the VN30 index."""
        return symbol.upper() in self.get_vn30_symbols()

    def get_stock_info(self, symbol: str) -> StockInfo | None:
        """
        Fetch company fundamentals and financial ratios.

        Args:
            symbol: Stock symbol (e.g., 'FPT', 'VIC')

        Returns:
            StockInfo with company name, industry, P/E, P/B, ROE, etc.
        """
        try:
            stock = Vnstock().stock(symbol=symbol, source=self.source)

            # Get company overview
            company_name = ""
            industry = ""
            exchange = ""
            try:
                overview = stock.company.overview()
                if hasattr(overview, "iloc") and len(overview) > 0:
                    row = overview.iloc[0]
                    company_name = str(row.get("short_name", row.get("company_name", "")))
                    industry = str(row.get("industry", ""))
                    exchange = str(row.get("exchange", ""))
            except Exception as e:
                logger.debug(f"Company overview error for {symbol}: {e}")

            # Get financial ratios
            pe_ratio = 0.0
            pb_ratio = 0.0
            eps = 0.0
            roe = 0.0
            market_cap = 0.0
            try:
                ratios = stock.finance.ratio(period="year", lang="en")
                if hasattr(ratios, "iloc") and len(ratios) > 0:
                    latest = ratios.iloc[-1]
                    # Search in multi-level columns
                    for col in ratios.columns:
                        col_name = col[1] if isinstance(col, tuple) else col
                        if col_name == "P/E":
                            pe_ratio = float(latest[col]) if latest[col] else 0.0
                        elif col_name == "P/B":
                            pb_ratio = float(latest[col]) if latest[col] else 0.0
                        elif col_name == "EPS (VND)":
                            eps = float(latest[col]) if latest[col] else 0.0
                        elif col_name == "ROE (%)":
                            roe = float(latest[col]) * 100 if latest[col] else 0.0
                        elif "Market Capital" in str(col_name):
                            market_cap = float(latest[col]) / 1e9 if latest[col] else 0.0
            except Exception as e:
                logger.debug(f"Financial ratios error for {symbol}: {e}")

            return StockInfo(
                symbol=symbol,
                company_name=company_name,
                industry=industry,
                exchange=exchange,
                market_cap=market_cap,
                pe_ratio=round(pe_ratio, 2),
                pb_ratio=round(pb_ratio, 2),
                eps=round(eps, 2),
                roe=round(roe, 2),
                is_vn30=self.is_vn30(symbol),
            )

        except Exception as e:
            logger.error(f"Error fetching stock info for {symbol}: {e}")
            return None

    def get_stock_price(self, symbol: str) -> StockPrice | None:
        """
        Fetch current price data for a single stock.

        Args:
            symbol: Stock symbol (e.g., 'FPT', 'VIC', 'MWG')

        Returns:
            StockPrice object with price, change, and volume data.
        """
        try:
            stock = Vnstock().stock(symbol=symbol, source=self.source)

            # Get last 2 trading days to calculate change
            end_date = datetime.datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")

            hist = stock.quote.history(symbol=symbol, start=start_date, end=end_date)

            if hist is None or len(hist) < 2:
                logger.warning(f"Not enough data for {symbol}")
                return None

            # Get last two rows for change calculation
            prev = hist.iloc[-2]
            curr = hist.iloc[-1]

            prev_close = float(prev["close"])
            curr_close = float(curr["close"])
            change = curr_close - prev_close
            change_pct = (change / prev_close) * 100 if prev_close > 0 else 0.0

            return StockPrice(
                symbol=symbol,
                price=curr_close,
                change=change,
                change_percent=round(change_pct, 2),
                volume=int(curr["volume"]),
                date=str(curr["time"]),
            )

        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return None

    def get_stock_prices(self, symbols: list[str]) -> dict[str, StockPrice]:
        """
        Fetch prices for multiple stocks.

        Args:
            symbols: List of stock symbols

        Returns:
            Dictionary mapping symbol to StockPrice object.
        """
        prices = {}
        for symbol in symbols:
            price = self.get_stock_price(symbol)
            if price:
                prices[symbol] = price
        return prices

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

        Args:
            days: Number of days of history

        Returns:
            List of daily OHLCV data for VN30 index.
        """
        try:
            stock = Vnstock().stock(symbol="VN30", source=self.source)

            end_date = datetime.datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime(
                "%Y-%m-%d"
            )

            hist = stock.quote.history(symbol="VN30", start=start_date, end=end_date)

            if hist is None or len(hist) == 0:
                return []

            results = []
            for _, row in hist.iterrows():
                results.append(
                    {
                        "date": str(row.get("time", "")),
                        "open": float(row.get("open", 0)),
                        "high": float(row.get("high", 0)),
                        "low": float(row.get("low", 0)),
                        "close": float(row.get("close", 0)),
                        "volume": int(row.get("volume", 0)),
                    }
                )
            return results

        except Exception as e:
            logger.error(f"Error fetching VN30 index history: {e}")
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
