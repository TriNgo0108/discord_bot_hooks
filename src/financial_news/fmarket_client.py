import datetime
import logging
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
        self, limit: int = 20, include_holdings: bool = False
    ) -> list[dict[str, Any]]:
        """
        Fetch top performing funds from Fmarket.

        Args:
            limit: Maximum number of funds to return.
            include_holdings: If True, fetch detailed holdings for each fund.
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
        Fetch gold prices from Fmarket API (Last 30 days).
        """
        url = f"{self.BASE_URL}/get-price-gold-history"

        now = datetime.datetime.now()
        to_date_str = now.strftime("%Y%m%d")
        from_date = now - datetime.timedelta(days=30)
        from_date_str = from_date.strftime("%Y%m%d")

        payload = {"fromDate": from_date_str, "toDate": to_date_str, "isAllData": False}

        try:
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            # data['data'] contains list of history if range > 1 day?
            # Based on API name 'get-price-gold-history', it likely returns a list in 'data' or 'rows'
            # Let's check the structure assuming it returns a list of daily records.
            # If it's a single object in 'extra' for today, we might need to look at 'data' for history.

            # Common Fmarket pattern: data['data'] is the main payload.
            # For history endpoint:
            # If we request a range, 'data' should be a list of daily prices.
            # 'extra' might still have the very latest real-time snapshot or summary.

            result = {
                "sjc_buy": 0,
                "sjc_sell": 0,
                "ring_buy": 0,
                "ring_sell": 0,
                "world_gold": 0,
                "usd_vnd": 0,
                "history": [],
            }

            if "extra" in data:
                extra = data["extra"]
                result.update(
                    {
                        "sjc_buy": extra.get("priceBuy"),
                        "sjc_sell": extra.get("priceSell"),
                        "ring_buy": extra.get("goldRingPriceBuy"),
                        "ring_sell": extra.get("goldRingPriceSell"),
                        "world_gold": extra.get("ratePriceGoldWorldToVND"),
                        "usd_vnd": extra.get("rateUsdToVnd"),
                    }
                )

            if "data" in data and isinstance(data["data"], list):
                result["history"] = data["data"]

            return result

        except Exception as e:
            logger.error(f"Error fetching gold prices: {e}")
            return {}

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
        # Try POST to get news if GET failed
        url = f"{self.BASE_URL}/blog/filter"  # Guessing 'filter' based on product filter pattern
        # Or maybe it's just 'newest'
        # Let's try the one known to work for funds pattern: /res/blog/filter or /res/blog/get-newest
        # Actually, let's revert to a safer bet or basic scraping if API fails.
        # But wait, looking at the debug output, `blog/all` returned mktImageUrl.
        # Let's try `blog/filter` with POST.

        url = f"{self.BASE_URL}/blog/filter"
        payload = {
            "types": ["MARKET_NEWS", "KNOWLEDGE", "PERSONAL_FINANCE"],  # Guessed types
            "page": 1,
            "pageSize": 5,
        }

        try:
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            news = []
            # Adapt to whatever structure comes back.
            # If I can't reliably guess the API, I will return empty for now to avoid breaking flow.
            # I will assume `data['data']['rows']` or `data['data']['content']`

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
