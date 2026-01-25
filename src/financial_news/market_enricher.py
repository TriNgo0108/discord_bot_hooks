"""
Market Enricher using Perplexity Search API (search-only, no LLM).
Returns raw web search results for VN30, stocks, and funds.
"""

import asyncio
import logging
from typing import Any

from src.common.tavily_client import TavilyClient

logger = logging.getLogger(__name__)


class MarketEnricher:
    """
    Enriches market data with web search results using Tavily Search API.
    """

    def __init__(self):
        self.tavily = TavilyClient()

    def _search(self, query: str, max_results: int = 5, timeout: int = 30) -> list[dict[str, str]]:
        """
        Search using Tavily Search API.

        Args:
            query: Search query
            max_results: Maximum number of results to return
            timeout: Request timeout in seconds

        Returns:
            List of search results with title, url, snippet, date
        """
        try:
            results = asyncio.run(self.tavily.search(query=query, max_results=max_results))

            return [
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", "")[:300],
                    "date": "",  # Tavily might not return date easily in basic search
                }
                for item in results.get("results", [])
            ]

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
        if not self.tavily.api_key or not vn30_data:
            return ""

        change = vn30_data.get("change_percent", 0)
        direction = "tăng" if change >= 0 else "giảm"

        query = f"VN30 index Vietnam stock market {direction} today news analysis"

        logger.info("Searching VN30 context via Tavily...")
        results = self._search(query, max_results=3)
        return self._format_results(results)

    def search_top_stocks_context(self, top_movers: dict[str, list]) -> str:
        """
        Search for news about top gaining/losing stocks.

        Returns:
            Formatted search results string.
        """
        if not self.tavily.api_key or not top_movers:
            return ""

        gainers = top_movers.get("gainers", [])[:3]
        losers = top_movers.get("losers", [])[:3]

        symbols = [g["symbol"] for g in gainers if g.get("symbol")]
        symbols += [l["symbol"] for l in losers if l.get("symbol")]

        if not symbols:
            return ""

        query = f"Vietnam stock {' '.join(symbols[:4])} news analysis today"

        logger.info("Searching top stocks context via Tavily...")
        results = self._search(query, max_results=3)
        return self._format_results(results)

    def search_fund_context(self, market_stats: dict[str, Any]) -> str:
        """
        Search for fund performance and market sector news.

        Returns:
            Formatted search results string.
        """
        top_funds = market_stats.get("top_funds", [])
        # Extract top holdings for search from both top_funds and watchlist_funds
        all_funds = (market_stats.get("watchlist_funds") or []) + top_funds

        all_holdings = []
        for fund in all_funds[:5]:  # Check first 5 funds
            holdings = fund.get("top_holdings", [])
            for h in holdings[:2]:
                if h.get("stock_code"):
                    all_holdings.append(h["stock_code"])

        unique_holdings = list(set(all_holdings))[:4]

        if not unique_holdings:
            return ""

        query = f"Vietnam stock fund investment {' '.join(unique_holdings)} performance outlook"

        logger.info("Searching fund context via Tavily...")
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

        if not self.tavily.api_key:
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
        watchlist_funds = market_stats.get("watchlist_funds", [])

        if top_funds or watchlist_funds:
            enrichments["funds_context"] = self.search_fund_context(market_stats)

        return enrichments
