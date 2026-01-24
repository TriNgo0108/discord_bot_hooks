"""
DSC Securities client for fetching Vietnam stock and index data.
No rate limits, provides real-time intraday data.
"""

import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class IndexData:
    """Market index data."""

    symbol: str
    current: float
    reference: float
    change: float
    change_percent: float
    volume: int
    last_update: str


@dataclass
class StockData:
    """Stock price data."""

    symbol: str
    price: float
    reference: float
    change: float
    change_percent: float
    volume: int
    last_update: str


class DSCClient:
    """
    Client to fetch Vietnam stock data from DSC Securities API.
    No rate limits, suitable for batch requests.
    """

    BASE_URL = "https://trading.dsc.com.vn/datafeed"

    def __init__(self, timeout: int = 30):
        self.client = httpx.Client(timeout=timeout)

    def get_index_data(self, index: str = "HOSE,30") -> dict[str, IndexData]:
        """
        Fetch market index data (HOSE and VN30).

        Args:
            index: Index symbols, e.g., "HOSE,30" for both HOSE and VN30

        Returns:
            Dictionary with IndexData for each requested index.
        """
        try:
            url = f"{self.BASE_URL}/chartinday/{index}"
            response = self.client.get(url)
            response.raise_for_status()
            data = response.json()

            if data.get("s") != "ok":
                logger.error(f"DSC API error: {data.get('em')}")
                return {}

            result = {}
            d = data.get("d", {})

            # Parse VN30 (key "30")
            if "30" in d:
                vn30 = d["30"]
                closes = vn30.get("close", [])
                refs = vn30.get("reference", [])
                vols = vn30.get("volume", [])
                times = vn30.get("formattedtime", [])

                current = closes[-1] if closes else 0
                ref = refs[0] if refs else 0
                change = current - ref
                change_pct = (change / ref) * 100 if ref > 0 else 0
                total_vol = sum(vols) if vols else 0

                result["VN30"] = IndexData(
                    symbol="VN30",
                    current=current,
                    reference=ref,
                    change=round(change, 2),
                    change_percent=round(change_pct, 2),
                    volume=total_vol,
                    last_update=times[-1] if times else "",
                )

            # Parse HOSE
            if "HOSE" in d:
                hose = d["HOSE"]
                closes = hose.get("close", [])
                refs = hose.get("reference", [])
                vols = hose.get("volume", [])
                times = hose.get("formattedtime", [])

                current = closes[-1] if closes else 0
                ref = refs[0] if refs else 0
                change = current - ref
                change_pct = (change / ref) * 100 if ref > 0 else 0
                total_vol = sum(vols) if vols else 0

                result["HOSE"] = IndexData(
                    symbol="HOSE",
                    current=current,
                    reference=ref,
                    change=round(change, 2),
                    change_percent=round(change_pct, 2),
                    volume=total_vol,
                    last_update=times[-1] if times else "",
                )

            return result

        except Exception as e:
            logger.error(f"Error fetching index data: {e}")
            return {}

    def get_stock_price(self, symbol: str) -> StockData | None:
        """
        Fetch stock price data using snapshots for better accuracy.

        Args:
            symbol: Stock symbol (e.g., 'FPT', 'VIC', 'MWG')

        Returns:
            StockData with current price, reference, change, and volume.
        """
        try:
            # Try quotes endpoint first for snapshot
            url = f"{self.BASE_URL.replace('/datafeed', '')}/quotes?symbols={symbol.upper()}"
            response = self.client.get(url)

            if response.status_code == 200:
                data = response.json()
                d = data.get("d", [])
                if d and isinstance(d, list) and len(d) > 0:
                    item = d[0]
                    # Common keys in quotes: matchPrice, reference, totalVolume
                    # Fallback to chartinday keys if needed
                    current = item.get("matchPrice") or item.get("close") or 0
                    ref = item.get("reference") or 0
                    vol = item.get("totalVolume") or item.get("volume") or 0

                    if current and ref:
                        change = current - ref
                        change_pct = (change / ref) * 100
                        return StockData(
                            symbol=symbol.upper(),
                            price=float(current),
                            reference=float(ref),
                            change=round(change, 2),
                            change_percent=round(change_pct, 2),
                            volume=int(vol),
                            last_update="",
                        )

            # Fallback to chartinday if quotes fails
            url = f"{self.BASE_URL}/chartinday/{symbol.upper()}"
            response = self.client.get(url)
            response.raise_for_status()
            data = response.json()

            if data.get("s") != "ok":
                return None

            d = data.get("d", {})
            stock = d.get(symbol.upper(), {})

            if not stock:
                return None

            closes = stock.get("close", [])
            refs = stock.get("reference", [])
            vols = stock.get("volume", [])
            times = stock.get("formattedtime", [])

            # Handle scaling issue: chartinday close is often in thousands
            raw_close = closes[-1] if closes else 0
            ref = refs[0] if refs else 0

            # Auto-detect scaling: if close is tiny vs ref, multiply by 1000
            current = raw_close
            if ref > 1000 and raw_close < ref / 100:
                current = raw_close * 1000

            change = current - ref
            change_pct = (change / ref) * 100 if ref > 0 else 0
            total_vol = sum(vols) if vols else 0

            return StockData(
                symbol=symbol.upper(),
                price=current,
                reference=ref,
                change=round(change, 2),
                change_percent=round(change_pct, 2),
                volume=total_vol,
                last_update=times[-1] if times else "",
            )

        except Exception as e:
            logger.error(f"Error fetching stock {symbol}: {e}")
            return None

    def get_stock_prices(self, symbols: list[str]) -> dict[str, StockData]:
        """
        Fetch prices for multiple stocks efficiently using quotes=ALL or batch.

        Args:
            symbols: List of stock symbols

        Returns:
            Dictionary mapping symbol to StockData.
        """
        try:
            # Fetch ALL quotes in one go if list is long, or join symbols
            # For efficiency, if list is small, pass comma separated
            # But /quotes?symbols=ALL is great for comprehensive data

            # Let's try fetching specified symbols first
            sym_str = ",".join(symbols)
            url = f"{self.BASE_URL.replace('/datafeed', '')}/quotes?symbols={sym_str}"
            response = self.client.get(url)

            result = {}
            if response.status_code == 200:
                data = response.json()
                items = data.get("d", [])
                for item in items:
                    sym = item.get("symbol")
                    if sym:
                        current = item.get("matchPrice") or item.get("close") or 0
                        ref = item.get("reference") or 0
                        vol = item.get("totalVolume") or item.get("volume") or 0

                        if current and ref:
                            change = current - ref
                            change_pct = (change / ref) * 100
                            result[sym] = StockData(
                                symbol=sym,
                                price=float(current),
                                reference=float(ref),
                                change=round(change, 2),
                                change_percent=round(change_pct, 2),
                                volume=int(vol),
                                last_update="",
                            )

            # Fill missing with individual calls (fallback)
            for sym in symbols:
                if sym not in result:
                    stock = self.get_stock_price(sym)
                    if stock:
                        result[sym] = stock

            return result

        except Exception as e:
            logger.error(f"Error fetching batch stocks: {e}")
            return {}

    def get_vn30_symbols(self) -> list[str]:
        """Get list of VN30 index component symbols."""
        try:
            url = f"{self.BASE_URL}/instruments/30"
            response = self.client.get(url)
            if response.status_code == 200:
                data = response.json()
                return data.get("d", [])
            return []
        except Exception as e:
            logger.error(f"Error fetching VN30 symbols: {e}")
            return []

    def get_stock_info(self, symbol: str) -> dict[str, Any] | None:
        """
        Fetch stock fundamental info (Market Cap, Industry, Company Name).
        Note: P/E, EPS, ROE might be missing or defaulted to 0 as DSC doesn't provide them explicitly in public API.
        """
        try:
            # Fetch all instruments if not cached (naive caching)
            if not hasattr(self, "_instruments_cache"):
                self._instruments_cache = {}
                self._fetch_all_instruments()

            # Fetch industries if not cached
            if not hasattr(self, "_industry_cache"):
                self._industry_cache = {}
                self._fetch_all_industries()

            info = self._instruments_cache.get(symbol.upper())
            if not info:
                # Try fetching specifically if missing from cache (e.g. newly listed or other exchange)
                # But mostly we rely on the bulk fetch
                return None

            # Calculate Market Cap: ListedShare * ClosePrice
            listed_shares = float(info.get("ListedShare", 0))
            close_price = float(info.get("closePrice", 0))  # closePrice is in VND
            market_cap_billion = (listed_shares * close_price) / 1e9

            industry = self._industry_cache.get(symbol.upper(), "Unknown")

            return {
                "symbol": symbol.upper(),
                "company_name": info.get("FullName", ""),
                "industry": industry,
                "exchange": info.get("exchange", ""),
                "market_cap": round(market_cap_billion, 2),
                "pe_ratio": 0.0,  # Not available
                "pb_ratio": 0.0,
                "eps": 0.0,
                "roe": 0.0,
                "is_vn30": symbol.upper()
                in self.get_vn30_symbols(),  # This effectively calls API again, maybe cache it too
            }

        except Exception as e:
            logger.error(f"Error getting stock info for {symbol}: {e}")
            return None

    def _fetch_all_instruments(self):
        """Fetch instruments from HOSE, HNX, UPCOM to cache."""
        exchanges = ["HOSE", "HNX", "UPCOM"]
        for exc in exchanges:
            try:
                url = f"{self.BASE_URL}/instruments?exchange={exc}"
                response = self.client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("d", [])
                    for item in items:
                        sym = item.get("symbol")
                        if sym:
                            self._instruments_cache[sym] = item
            except Exception as e:
                logger.warning(f"Failed to fetch instruments for {exc}: {e}")

    def _fetch_all_industries(self):
        """Fetch industry mapping."""
        try:
            url = f"https://trading.dsc.com.vn/userdata/industry"
            response = self.client.get(url)
            if response.status_code == 200:
                data = response.json()
                items = data.get("d", [])
                for item in items:
                    ind_name = item.get("industryName", "")
                    code_list = item.get("codeList", "").split(",")
                    for code in code_list:
                        if code:
                            self._industry_cache[code.strip()] = ind_name
        except Exception as e:
            logger.warning(f"Failed to fetch industries: {e}")
