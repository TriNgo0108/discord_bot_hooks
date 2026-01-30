import datetime
import logging
import json
import os
import time
import re
from typing import Any


import httpx

logger = logging.getLogger(__name__)


class FmarketClient:
    """
    Client to interact with Fmarket API to retrieve financial data.
    """

    BASE_URL = "https://api.fmarket.vn/res"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    def __init__(self):
        self.client = httpx.Client(headers=self.HEADERS, timeout=30.0)

    def get_fund_detail(self, product_id: int) -> dict[str, Any]:
        """
        Fetch detailed fund information including top holdings.

        Args:
            product_id: The fund product ID.

        Returns:
            Dictionary with fund details including top_holdings, asset_allocation,
            and industry_allocation.
        """
        url = f"{self.BASE_URL}/products/{product_id}"

        try:
            response = self.client.get(url)
            response.raise_for_status()
            data = response.json()

            if "data" not in data:
                return {}

            product = data["data"]

            # Extract top holdings
            top_holdings = []
            for holding in product.get("productTopHoldingList", []):
                top_holdings.append(
                    {
                        "stock_code": holding.get("stockCode"),
                        "price": holding.get("price"),
                        "change_percent": holding.get("changeFromPreviousPercent"),
                        "portfolio_weight": holding.get("netAssetPercent"),
                        "industry": holding.get("industry"),
                    }
                )

            # Extract asset allocation
            asset_allocation = []
            for asset in product.get("productAssetHoldingList", []):
                asset_type = asset.get("assetType", {})
                asset_allocation.append(
                    {
                        "type": asset_type.get("name"),
                        "percent": asset.get("assetPercent"),
                    }
                )

            # Extract industry allocation
            industry_allocation = []
            for industry in product.get("productIndustriesHoldingList", []):
                industry_allocation.append(
                    {
                        "industry": industry.get("industry"),
                        "percent": industry.get("assetPercent"),
                    }
                )

            return {
                "id": product.get("id"),
                "name": product.get("shortName"),
                "full_name": product.get("name"),
                "nav": product.get("nav"),
                "description": product.get("description"),
                "top_holdings": top_holdings,
                "asset_allocation": asset_allocation,
                "industry_allocation": industry_allocation,
            }

        except Exception as e:
            logger.error(f"Error fetching fund detail for product {product_id}: {e}")
            return {}

    def search_funds(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        Search for funds by name or code.
        """
        url = f"{self.BASE_URL}/products/filter"
        payload = {
            "types": ["NEW_FUND", "TRADING_FUND"],
            "issuerIds": [],
            "sortOrder": "DESC",
            "sortField": "navTo6Months",
            "page": 1,
            "pageSize": limit,
            "isIpo": False,
            "fundAssetTypes": [],
            "bondRemainPeriods": [],
            "searchField": query,
            "isBuyByReward": False,
            "thirdAppIds": [],
        }

        try:
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            if "data" in data and "rows" in data["data"]:
                funds = []
                for row in data["data"]["rows"]:
                    funds.append(self._parse_fund_row(row))
                return funds
            return []
        except Exception as e:
            logger.error(f"Error searching funds with query '{query}': {e}")
            return []

    def get_funds_by_codes(self, codes: list[str]) -> list[dict[str, Any]]:
        """
        Fetch specific funds by their codes.
        Since there's no direct bulk get by code, we search for each.
        """
        results = []
        for code in codes:
            # increasing limit slightly in case of partial matches, though exact code usually comes first
            funds = self.search_funds(code, limit=5)
            # Filter for exact match or close match if needed
            # For now, take the first one that matches the code in shortName if possible
            found = None
            for f in funds:
                if code.upper() in f["name"].upper():
                    found = f
                    break

            if found:
                # enrich with detailed holdings
                detail = self.get_fund_detail(found["id"])
                if detail:
                    found["top_holdings"] = detail.get("top_holdings", [])
                    found.update(detail)  # Merge details
                results.append(found)
        return results

    def _parse_fund_row(self, row: dict[str, Any]) -> dict[str, Any]:
        """Helper to parse a fund row from search/filter response."""
        fund_type = None
        if row.get("fundAssetType"):
            fund_type = row["fundAssetType"].get("name")
        elif row.get("dataFundAssetType"):
            fund_type = row["dataFundAssetType"].get("name")

        return {
            "id": row.get("id"),
            "name": row.get("shortName"),
            "full_name": row.get("name"),
            "nav": row.get("nav"),
            "nav_12m": row.get("productNavChange", {}).get("navTo12Months"),
            "nav_ytd": row.get("productNavChange", {}).get("navToLastYear"),
            "nav_6m": row.get("productNavChange", {}).get("navTo6Months"),
            "nav_3y": row.get("productNavChange", {}).get("navTo36Months"),
            "type": fund_type,
        }

    def get_top_funds(
        self,
        limit: int = 20,
        include_holdings: bool = False,
        sort_field: str = "navTo12Months",
    ) -> list[dict[str, Any]]:
        """
        Fetch top performing funds from Fmarket.

        Args:
            limit: Maximum number of funds to return.
            include_holdings: If True, fetch detailed holdings for each fund.
            sort_field: Field to sort by (e.g., 'navTo12Months', 'navTo6Months').
        """
        url = f"{self.BASE_URL}/products/filter"
        payload = {
            "types": ["NEW_FUND", "TRADING_FUND"],
            "issuerIds": [],
            "sortOrder": "DESC",
            "sortField": sort_field,
            "page": 1,
            "pageSize": limit,
            "isIpo": False,
            "fundAssetTypes": [],  # All types
            "bondRemainPeriods": [],
            "searchField": "",
            "isBuyByReward": False,
            "thirdAppIds": [],
        }

        try:
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            if "data" in data and "rows" in data["data"]:
                funds = []
                for row in data["data"]["rows"]:
                    fund_data = self._parse_fund_row(row)

                    # Optionally fetch detailed holdings
                    if include_holdings and row.get("id"):
                        detail = self.get_fund_detail(row["id"])
                        if detail:
                            fund_data["top_holdings"] = detail.get("top_holdings", [])
                            fund_data["asset_allocation"] = detail.get("asset_allocation", [])
                            fund_data["industry_allocation"] = detail.get("industry_allocation", [])

                    funds.append(fund_data)
                return funds
            return []
        except Exception as e:
            logger.error(f"Error fetching top funds: {e}")
            return []

    def get_gold_prices(self) -> dict[str, Any]:
        """
        Fetch gold prices from multiple sources:
        - Vietnam (SJC, Ring): vnappmob API
        - World: freegoldapi
        - History: vnappmob with caching
        """
        result = {
            "sjc_buy": 0.0,
            "sjc_sell": 0.0,
            "ring_buy": 0.0,
            "ring_sell": 0.0,
            "world_gold": 0.0,
            "usd_vnd": 0.0,
            "history": [],
        }

        # 1. Fetch Vietnam Gold Data (SJC & Ring)
        try:
            # Get cached or fresh API Key
            api_key = self._get_vnappmob_key()

            # vnappmob v2 SJC endpoint
            vn_url = "https://api.vnappmob.com/api/v2/gold/sjc"
            headers = {"Authorization": f"Bearer {api_key}"}

            resp = self.client.get(vn_url, headers=headers)

            if resp.status_code == 403:
                # Key might be expired, force refresh (delete cache and retry once)
                logger.warning("VNAppMob Key expired (403). Refreshing key...")
                api_key = self._get_vnappmob_key(force_refresh=True)
                headers = {"Authorization": f"Bearer {api_key}"}
                resp = self.client.get(vn_url, headers=headers)

            resp.raise_for_status()
            data = resp.json()

            # Structure expectation: {'results': [{'buy_1l': ..., 'sell_1l': ..., 'buy_nhan1c': ..., ...}]}
            if "results" in data and len(data["results"]) > 0:
                latest = data["results"][0]
                # Price is already in full VND (e.g. 178000000.0), do NOT multiply by 1000.
                result["sjc_buy"] = float(latest.get("buy_1l", 0))
                result["sjc_sell"] = float(latest.get("sell_1l", 0))
                result["ring_buy"] = float(latest.get("buy_nhan1c", 0))
                result["ring_sell"] = float(latest.get("sell_nhan1c", 0))

        except Exception as e:
            logger.error(f"Error fetching Vietnam gold prices: {e}")

        # 2. Fetch World Gold
        try:
            world_url = "https://freegoldapi.com/data/latest.json"
            # Try freegoldapi (might default to USD/oz)
            # Or use explicit currency if supported e.g. /data/XAU/USD/latest.json
            # Simplest fallback: calculate if not easy.
            # actually freegoldapi requires no key? Let's try.
            # If it fails, leave as 0.
            w_resp = getattr(self.client, "get")(world_url)  # type safe
            if w_resp.status_code == 200:
                # Expecting {"price": 1234.56, ...}
                w_data = w_resp.json()
                result["world_gold"] = float(w_data.get("price", 0))
        except Exception:
            # logger.error(f"Error fetching World gold: {e}")
            # Silent fail for secondary data
            pass

        # 3. History with Caching
        try:
            cache_dir = "data"
            os.makedirs(cache_dir, exist_ok=True)
            cache_file = os.path.join(cache_dir, "gold_history_cache.json")

            history_data = []

            # Load cache
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, "r") as f:
                        history_data = json.load(f)
                except Exception:
                    history_data = []  # Corrupt cache

            today = datetime.datetime.now()
            today_str = today.strftime("%Y-%m-%d")

            # Determine start date
            start_date = today - datetime.timedelta(days=365)

            if not history_data:
                fetch_from = start_date
            else:
                # Sort caching
                history_data.sort(key=lambda x: x.get("date", ""))
                last_entry = history_data[-1]
                try:
                    last_date = datetime.datetime.strptime(last_entry.get("date"), "%Y-%m-%d")
                    fetch_from = last_date + datetime.timedelta(days=1)
                except:
                    fetch_from = start_date

            if fetch_from < today:
                # Fetch missing data
                from_s = fetch_from.strftime("%Y-%m-%d")
                to_s = today_str

                # Only fetch if gap exists
                if from_s <= to_s:
                    # Need API Key for history too?
                    # Docs say: "Authorization – Bearer <api_key|scope=gold|permission=0>"
                    # Assuming same key works.
                    api_key = self._get_vnappmob_key()
                    h_url = f"https://api.vnappmob.com/api/v2/gold/sjc?date_from={from_s}&date_to={to_s}"
                    headers = {"Authorization": f"Bearer {api_key}"}

                    h_resp = self.client.get(h_url, headers=headers)
                    if h_resp.status_code == 200:
                        h_json = h_resp.json()
                        new_items = []
                        if "results" in h_json:
                            for item in h_json["results"]:
                                # Parse Date: Items use 'datetime' timestamp (seconds)
                                d_str = ""
                                if "datetime" in item:
                                    try:
                                        ts = int(float(item["datetime"]))
                                        d_str = datetime.datetime.fromtimestamp(ts).strftime(
                                            "%Y-%m-%d"
                                        )
                                    except:
                                        pass
                                elif "date" in item:
                                    d_str = item["date"]

                                if d_str:
                                    new_items.append(
                                        {
                                            "date": d_str,
                                            "sjc_buy": float(item.get("buy_1l", 0)),
                                            "sjc_sell": float(item.get("sell_1l", 0)),
                                        }
                                    )

                        # Merge and Deduplicate
                        # Use dict to dedupe by date
                        hist_map = {x["date"]: x for x in history_data}
                        for ni in new_items:
                            hist_map[ni["date"]] = ni

                        # Re-convert to list and sort
                        full_hist = list(hist_map.values())
                        full_hist.sort(key=lambda x: x["date"])

                        # Trim to 365 days to avoid unlimited growth
                        # actually cache can grow, but result returned should be limited?
                        # Let's keep cache full, but output simple.

                        history_data = full_hist

                        # Save Cache
                        with open(cache_file, "w") as f:
                            json.dump(history_data, f, indent=2)

            # Filter result history to last 365 days for return
            cutoff = (today - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
            result["history"] = [x for x in history_data if x["date"] >= cutoff]

        except Exception as e:
            logger.error(f"Error processing gold history: {e}")

        return result

    def _get_vnappmob_key(self, force_refresh: bool = False) -> str:
        """
        Get VNAppMob API Key.
        - Check data/vnappmob_key.json
        - If missing/expired or force_refresh is True, request new key.
        - Cache key.
        """
        cache_dir = "data"
        os.makedirs(cache_dir, exist_ok=True)
        key_file = os.path.join(cache_dir, "vnappmob_key.json")

        # Try load cache
        if not force_refresh and os.path.exists(key_file):
            try:
                with open(key_file, "r") as f:
                    data = json.load(f)
                    # Check expiry (15 days = 15 * 24 * 3600 seconds)
                    # Let's refresh if older than 14 days to be safe
                    created_at = data.get("created_at", 0)
                    if time.time() - created_at < 14 * 24 * 3600:
                        return data.get("key", "")
            except Exception:
                pass  # Load failed

        # Fetch new key
        try:
            url = "https://api.vnappmob.com/api/request_api_key?scope=gold"
            resp = self.client.get(url)
            resp.raise_for_status()

            # Clean key: Response might be "{results:JWT}" or just "JWT" or quoted.
            # Use regex to find JWT pattern (header.payload.signature)
            match = re.search(r"eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+", resp.text)
            if match:
                new_key = match.group(0)
            else:
                # Fallback: simple strip
                raw_text = resp.text.strip().replace('"', "").replace("'", "")
                new_key = raw_text.encode("ascii", "ignore").decode("ascii")

            # Save to cache
            with open(key_file, "w") as f:
                json.dump({"key": new_key, "created_at": time.time()}, f)

            return new_key

        except Exception as e:
            logger.error(f"Failed to fetch VNAppMob API key: {e}")
            return ""

    def get_bank_rates(self) -> list[dict[str, Any]]:
        """
        Fetch bank interest rates.
        """
        url = f"{self.BASE_URL}/bank-interest-rate"
        try:
            response = self.client.get(url)
            response.raise_for_status()
            data = response.json()

            rates = []
            # data['data'] contains 'bankList'
            if "data" in data and isinstance(data["data"], dict):
                bank_list = data["data"].get("bankList", [])

                # Sort by value (rate) descending
                # Value is string, need to convert to float
                sorted_banks = sorted(
                    bank_list,
                    key=lambda x: float(x.get("value", 0) if x.get("value") else 0),
                    reverse=True,
                )

                for bank in sorted_banks[:5]:
                    rates.append(
                        {
                            "bank": bank.get("name"),
                            "rate_12m": bank.get(
                                "value"
                            ),  # It seems to be the single displayed rate
                        }
                    )
            return rates
        except Exception as e:
            logger.error(f"Error fetching bank rates: {e}")
            logger.error(f"Response was: {data}")
            return []

    def get_market_news(self) -> list[dict[str, Any]]:
        """
        Fetch market news/blog from Fmarket.
        """
        url = f"{self.BASE_URL}/blog/filter"
        payload = {
            "types": ["MARKET_NEWS", "KNOWLEDGE", "PERSONAL_FINANCE"],
            "page": 1,
            "pageSize": 5,
        }

        try:
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            news = []
            rows = []
            if "data" in data:
                if "rows" in data["data"]:
                    rows = data["data"]["rows"]
                elif "content" in data["data"]:
                    rows = data["data"]["content"]
                elif isinstance(data["data"], list):
                    rows = data["data"]

            for item in rows:
                news.append(
                    {
                        "title": item.get("title"),
                        "link": "https://fmarket.vn/blog/" + item.get("slug", ""),
                        "summary": item.get("shortDescription", ""),
                        "source": "Fmarket",
                        "published_at": datetime.datetime.fromtimestamp(
                            item.get("createAt", 0) / 1000
                        ),
                        "id": str(item.get("id")),
                    }
                )
            return news
        except Exception as e:
            logger.error(f"Error fetching Fmarket news: {e}")
            return []
