"""
SSI iBoard API client for fetching VN30 stock and index data.
Public API - no API key required.
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Common headers required by iBoard API
_IBOARD_HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "vi",
    "cache-control": "no-cache",
    "device-id": str(uuid.uuid4()),
    "origin": "https://iboard.ssi.com.vn",
    "pragma": "no-cache",
    "referer": "https://iboard.ssi.com.vn/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/145.0.0.0 Safari/537.36"
    ),
}

BASE_URL = "https://iboard-query.ssi.com.vn"


@dataclass
class SSIStockData:
    """Per-stock data from the SSI /stock/group/VN30 endpoint."""

    stock_symbol: str
    company_name: str
    exchange: str

    # Prices
    matched_price: float
    ref_price: float
    ceiling: float
    floor: float
    open_price: float
    highest: float
    lowest: float
    avg_price: float
    price_change: float
    price_change_percent: float

    # Volume & Value
    total_volume: int
    total_value: float

    # Foreign flow
    buy_foreign_qtty: int
    buy_foreign_value: float
    sell_foreign_qtty: int
    sell_foreign_value: float

    # Best bid/offer (top of order book)
    best1_bid: float = 0
    best1_bid_vol: int = 0
    best1_offer: float = 0
    best1_offer_vol: int = 0

    @property
    def foreign_net_qtty(self) -> int:
        """Net foreign quantity (positive = net buy)."""
        return self.buy_foreign_qtty - self.sell_foreign_qtty

    @property
    def foreign_net_value(self) -> float:
        """Net foreign value (positive = net buy)."""
        return self.buy_foreign_value - self.sell_foreign_value


@dataclass
class SSIIndexData:
    """VN30 index data from the /exchange-index/VN30 endpoint."""

    index_id: str
    index_value: float
    prev_index_value: float
    change: float
    change_percent: float

    # Market breadth
    advances: int
    declines: int
    nochanges: int

    # Session stats
    chart_open: float
    chart_high: float
    chart_low: float
    total_qtty: int
    total_value: float

    # Aggregate foreign
    total_buy_foreign_qtty: int
    total_sell_foreign_qtty: int

    # Intraday chart history
    history: list[dict[str, Any]] = field(default_factory=list)

    @property
    def foreign_net_qtty(self) -> int:
        """Aggregate net foreign quantity for VN30."""
        return self.total_buy_foreign_qtty - self.total_sell_foreign_qtty


class SSIClient:
    """
    Client to fetch VN30 data from SSI iBoard API.
    Public API - no authentication required.
    """

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout, headers=_IBOARD_HEADERS)

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def _get(self, path: str) -> dict[str, Any] | list:
        """Send GET request to iBoard API."""
        url = f"{BASE_URL}{path}"
        response = self._client.get(url)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != "SUCCESS":
            msg = data.get("message", "Unknown error")
            raise ValueError(f"SSI API error: {msg}")

        return data.get("data", {})

    def get_vn30_stocks(self) -> list[SSIStockData]:
        """
        Fetch per-stock data for all VN30 component stocks.

        Returns:
            List of SSIStockData with prices, foreign flow, and order book.
        """
        try:
            raw_stocks = self._get("/stock/group/VN30")
        except Exception as e:
            logger.error(f"Failed to fetch VN30 stocks from SSI: {e}")
            return []

        if not isinstance(raw_stocks, list):
            logger.warning("SSI VN30 stocks response is not a list")
            return []

        stocks = []
        for item in raw_stocks:
            try:
                stocks.append(
                    SSIStockData(
                        stock_symbol=item.get("stockSymbol", ""),
                        company_name=item.get("companyNameEn", ""),
                        exchange=item.get("exchange", ""),
                        matched_price=item.get("matchedPrice", 0),
                        ref_price=item.get("refPrice", 0),
                        ceiling=item.get("ceiling", 0),
                        floor=item.get("floor", 0),
                        open_price=item.get("openPrice", 0),
                        highest=item.get("highest", 0),
                        lowest=item.get("lowest", 0),
                        avg_price=item.get("avgPrice", 0),
                        price_change=item.get("priceChange", 0),
                        price_change_percent=item.get("priceChangePercent", 0),
                        total_volume=item.get("nmTotalTradedQty", 0),
                        total_value=item.get("nmTotalTradedValue", 0),
                        buy_foreign_qtty=item.get("buyForeignQtty", 0),
                        buy_foreign_value=item.get("buyForeignValue", 0),
                        sell_foreign_qtty=item.get("sellForeignQtty", 0),
                        sell_foreign_value=item.get("sellForeignValue", 0),
                        best1_bid=item.get("best1Bid", 0),
                        best1_bid_vol=item.get("best1BidVol", 0),
                        best1_offer=item.get("best1Offer", 0),
                        best1_offer_vol=item.get("best1OfferVol", 0),
                    )
                )
            except Exception as e:
                symbol = item.get("stockSymbol", "unknown")
                logger.warning(f"Failed to parse SSI stock data for {symbol}: {e}")

        logger.info(f"Fetched {len(stocks)} VN30 stocks from SSI")
        return stocks

    def get_vn30_index(self) -> SSIIndexData | None:
        """
        Fetch VN30 index data with intraday chart history.

        Returns:
            SSIIndexData with index value, breadth, and chart history, or None.
        """
        try:
            raw = self._get("/exchange-index/VN30?hasHistory=true")
        except Exception as e:
            logger.error(f"Failed to fetch VN30 index from SSI: {e}")
            return None

        if not isinstance(raw, dict):
            logger.warning("SSI VN30 index response is not a dict")
            return None

        try:
            return SSIIndexData(
                index_id=raw.get("indexId", "VN30"),
                index_value=raw.get("indexValue", 0),
                prev_index_value=raw.get("prevIndexValue", 0),
                change=raw.get("change", 0),
                change_percent=raw.get("changePercent", 0),
                advances=raw.get("advances", 0),
                declines=raw.get("declines", 0),
                nochanges=raw.get("nochanges", 0),
                chart_open=raw.get("chartOpen", 0),
                chart_high=raw.get("chartHigh", 0),
                chart_low=raw.get("chartLow", 0),
                total_qtty=raw.get("totalQtty", 0),
                total_value=raw.get("totalValue", 0),
                total_buy_foreign_qtty=raw.get("totalBuyForeignQtty", 0),
                total_sell_foreign_qtty=raw.get("totalSellForeignQtty", 0),
                history=raw.get("history", []),
            )
        except Exception as e:
            logger.error(f"Failed to parse SSI VN30 index data: {e}")
            return None

    def get_market_summary(self) -> dict[str, Any]:
        """
        Aggregate VN30 market summary from both SSI endpoints.

        Returns:
            Dictionary with:
            - index: SSIIndexData dict
            - stocks: list of SSIStockData dicts
            - foreign_summary: aggregate foreign flow
            - top_foreign_buy: top 5 stocks by foreign net buy
            - top_foreign_sell: top 5 stocks by foreign net sell
            - top_gainers: top 5 stocks by price change %
            - top_losers: bottom 5 stocks by price change %
        """
        stocks = self.get_vn30_stocks()
        index = self.get_vn30_index()

        summary: dict[str, Any] = {
            "index": None,
            "stocks": [],
            "foreign_summary": {},
            "top_foreign_buy": [],
            "top_foreign_sell": [],
            "top_gainers": [],
            "top_losers": [],
        }

        # Index data
        if index:
            summary["index"] = {
                "value": index.index_value,
                "prev_value": index.prev_index_value,
                "change": index.change,
                "change_percent": index.change_percent,
                "advances": index.advances,
                "declines": index.declines,
                "nochanges": index.nochanges,
                "chart_open": index.chart_open,
                "chart_high": index.chart_high,
                "chart_low": index.chart_low,
                "total_qtty": index.total_qtty,
                "total_value": index.total_value,
                "foreign_net_qtty": index.foreign_net_qtty,
                "total_buy_foreign_qtty": index.total_buy_foreign_qtty,
                "total_sell_foreign_qtty": index.total_sell_foreign_qtty,
            }

        if not stocks:
            return summary

        # Stock list (compact)
        stock_dicts = []
        for s in stocks:
            stock_dicts.append(
                {
                    "symbol": s.stock_symbol,
                    "company": s.company_name,
                    "price": s.matched_price,
                    "change": s.price_change,
                    "change_percent": s.price_change_percent,
                    "volume": s.total_volume,
                    "value": s.total_value,
                    "foreign_net_qtty": s.foreign_net_qtty,
                    "foreign_net_value": s.foreign_net_value,
                    "buy_foreign_qtty": s.buy_foreign_qtty,
                    "sell_foreign_qtty": s.sell_foreign_qtty,
                }
            )
        summary["stocks"] = stock_dicts

        # Foreign flow aggregation
        total_buy_val = sum(s.buy_foreign_value for s in stocks)
        total_sell_val = sum(s.sell_foreign_value for s in stocks)
        summary["foreign_summary"] = {
            "total_buy_value": total_buy_val,
            "total_sell_value": total_sell_val,
            "net_value": total_buy_val - total_sell_val,
        }

        # Top foreign activity (sorted by net quantity)
        sorted_by_foreign = sorted(stocks, key=lambda s: s.foreign_net_qtty, reverse=True)
        summary["top_foreign_buy"] = [
            {
                "symbol": s.stock_symbol,
                "net_qtty": s.foreign_net_qtty,
                "net_value": s.foreign_net_value,
            }
            for s in sorted_by_foreign[:5]
            if s.foreign_net_qtty > 0
        ]
        summary["top_foreign_sell"] = [
            {
                "symbol": s.stock_symbol,
                "net_qtty": s.foreign_net_qtty,
                "net_value": s.foreign_net_value,
            }
            for s in sorted_by_foreign[-5:]
            if s.foreign_net_qtty < 0
        ]

        # Top gainers/losers
        sorted_by_change = sorted(stocks, key=lambda s: s.price_change_percent, reverse=True)
        summary["top_gainers"] = [
            {
                "symbol": s.stock_symbol,
                "price": s.matched_price,
                "change_percent": s.price_change_percent,
            }
            for s in sorted_by_change[:5]
        ]
        summary["top_losers"] = [
            {
                "symbol": s.stock_symbol,
                "price": s.matched_price,
                "change_percent": s.price_change_percent,
            }
            for s in sorted_by_change[-5:]
        ]

        return summary
