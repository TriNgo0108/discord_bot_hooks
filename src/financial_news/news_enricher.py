import logging
from typing import Any

from src.common.tavily_client import TavilyClient

logger = logging.getLogger(__name__)


class NewsEnricher:
    """
    Enriches news items with additional context using Tavily Search API.
    """

    def __init__(self):
        self.tavily = TavilyClient()

    async def search_async(self, query: str) -> str:
        """
        Search for a query and return a summarized context string.
        """
        if not self.tavily.api_key:
            return ""

        return await self.tavily.get_search_context(query, max_results=3)

    def search(self, query: str) -> str:
        """Synchronous wrapper for search."""
        import asyncio

        return asyncio.run(self.search_async(query))

    def enrich_news_items(
        self, news_items: list[dict[str, Any]], limit: int = 3
    ) -> list[dict[str, Any]]:
        """
        Enriches the top N news items with web search context.
        Modifies the items in-place (or returns list of enriched items).
        """
        if not self.tavily.api_key:
            return news_items

        count = 0
        for item in news_items:
            if count >= limit:
                break

            query = item.get("title", "")
            if not query:
                continue

            logger.info(f"Enriching: {query[:30]}...")
            context = self.search(query)

            if context:
                # Append context to summary
                item["summary"] = item.get("summary", "") + "\n\n**Web Context:**\n" + context
                count += 1

        return news_items
