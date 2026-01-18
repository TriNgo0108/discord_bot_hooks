import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class NewsEnricher:
    """
    Enriches news items with additional context using WebSearchAPI.ai.
    """

    BASE_URL = "https://api.websearchapi.ai/ai-search"

    def __init__(self):
        self.api_key = os.getenv("WEBSEARCH_API_KEY")
        if not self.api_key:
            logger.warning("WEBSEARCH_API_KEY not found. Enrichment will be disabled.")

    def search(self, query: str) -> str:
        """
        Search for a query and return a summarized context string.
        """
        if not self.api_key:
            return ""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Using 'vn' as requested
        payload = {
            "query": query,
            "maxResults": 3,
            "includeContent": False,
            "includeAnswer": False,
            "country": "vn",
        }

        try:
            response = httpx.post(self.BASE_URL, headers=headers, json=payload, timeout=20.0)

            if response.status_code == 401:
                logger.error("WebSearchAPI Unauthorized. Check your key.")
                return ""
            if response.status_code == 403:  # Quota or Forbidden
                logger.warning("WebSearchAPI Forbidden/Quota Exceeded.")
                return ""

            response.raise_for_status()
            data = response.json()

            context = ""
            if "results" in data:
                for res in data["results"]:
                    title = res.get("title", "")
                    snippet = res.get("snippet", res.get("description", ""))
                    context += f"- [Web] {title}: {snippet}\n"

            return context.strip()

        except Exception as e:
            logger.error(f"Error enriching news for '{query}': {e}")
            return ""

    def enrich_news_items(
        self, news_items: list[dict[str, Any]], limit: int = 3
    ) -> list[dict[str, Any]]:
        """
        Enriches the top N news items with web search context.
        Modifies the items in-place (or returns list of enriched items).
        """
        if not self.api_key:
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
