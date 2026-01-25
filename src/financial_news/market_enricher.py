"""
Market Enricher using Perplexity Search API (search-only, no LLM).
Returns raw web search results for VN30, stocks, and funds.
"""

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class MarketEnricher:
    """
    Enriches market data with web search results using Perplexity Search API.

    Uses search-only endpoint (no LLM) to fetch raw web results.
    """

    BASE_URL = "https://api.perplexity.ai"

    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            logger.warning("PERPLEXITY_API_KEY not found. Market enrichment will be disabled.")

    def _search(self, query: str, max_results: int = 5, timeout: int = 30) -> list[dict[str, str]]:
        """
        Search using Perplexity Search API (no LLM).

        Args:
            query: Search query
            max_results: Maximum number of results to return
            timeout: Request timeout in seconds

        Returns:
            List of search results with title, url, snippet, date
        """
        if not self.api_key:
            return []

        try:
            response = httpx.post(
                f"{self.BASE_URL}/search",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "query": query,
                    "max_results": max_results,
                },
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("results", []):
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("snippet", ""),
                        "date": item.get("date", ""),
                    }
                )

            logger.info(f"Found {len(results)} search results for: {query[:50]}...")
            return results

        except httpx.HTTPError as e:
            logger.error(f"Perplexity Search API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def _format_results(self, results: list[dict[str, str]]) -> str:
        """Format search results into a readable string."""
        if not results:
            return ""

        formatted = []
        for r in results:
            line = f"- [{r.get('title', 'N/A')}]({r.get('url', '')})"
            if r.get("snippet"):
                line += f": {r['snippet'][:150]}"
            if r.get("date"):
                line += f" ({r['date']})"
            formatted.append(line)

        return "\n".join(formatted)

    def search_vn30_context(self, vn30_data: dict[str, Any]) -> str:
        """
        Search for VN30 index news and analysis.

        Returns:
            Formatted search results string.
        """
        if not self.api_key or not vn30_data:
            return ""

        change = vn30_data.get("change_percent", 0)
        direction = "tăng" if change >= 0 else "giảm"

        query = f"VN30 index Vietnam stock market {direction} today news analysis"

        logger.info("Searching VN30 context via Perplexity...")
        results = self._search(query, max_results=3)
        return self._format_results(results)

    def search_top_stocks_context(self, top_movers: dict[str, list]) -> str:
        """
        Search for news about top gaining/losing stocks.

        Returns:
            Formatted search results string.
        """
        if not self.api_key or not top_movers:
            return ""

        gainers = top_movers.get("gainers", [])[:3]
        losers = top_movers.get("losers", [])[:3]

        symbols = [g["symbol"] for g in gainers if g.get("symbol")]
        symbols += [l["symbol"] for l in losers if l.get("symbol")]

        if not symbols:
            return ""

        query = f"Vietnam stock {' '.join(symbols[:4])} news analysis today"

        logger.info("Searching top stocks context via Perplexity...")
        results = self._search(query, max_results=3)
        return self._format_results(results)

    def search_fund_context(self, top_funds: list[dict[str, Any]]) -> str:
        """
        Search for fund performance and market sector news.

        Returns:
            Formatted search results string.
        """
        if not self.api_key or not top_funds:
            return ""

        # Extract top holdings for search
        all_holdings = []
        for fund in top_funds[:3]:
            holdings = fund.get("top_holdings", [])
            for h in holdings[:2]:
                if h.get("stock_code"):
                    all_holdings.append(h["stock_code"])

        unique_holdings = list(set(all_holdings))[:4]

        if not unique_holdings:
            return ""

        query = f"Vietnam stock fund investment {' '.join(unique_holdings)} performance outlook"

        logger.info("Searching fund context via Perplexity...")
        results = self._search(query, max_results=3)
        return self._format_results(results)

    def enrich_market_stats(self, market_stats: dict[str, Any]) -> dict[str, str]:
        """
        Enrich all market data with Perplexity search results.

        Args:
            market_stats: Dictionary containing vn30_current, top_movers, top_funds, etc.

        Returns:
            Dictionary with search result strings:
            - vn30_context: Search results about VN30 index
            - stocks_context: Search results about top movers
            - funds_context: Search results about funds/holdings
        """
        enrichments = {
            "vn30_context": "",
            "stocks_context": "",
            "funds_context": "",
        }

        if not self.api_key:
            logger.warning("Skipping market enrichment - no API key")
            return enrichments

        # Search VN30 context
        vn30_current = market_stats.get("vn30_current", {})
        if vn30_current:
            enrichments["vn30_context"] = self.search_vn30_context(vn30_current)

        # Search top stocks context
        top_movers = market_stats.get("top_movers", {})
        if top_movers:
            enrichments["stocks_context"] = self.search_top_stocks_context(top_movers)

        # Search fund context
        top_funds = market_stats.get("top_funds", [])
        if top_funds:
            enrichments["funds_context"] = self.search_fund_context(top_funds)

        return enrichments
