import asyncio
import logging
from typing import Any

from bot_common.tavily_client import TavilyClient

logger = logging.getLogger(__name__)

# Political/Policy news search topics for Vietnam financial markets
POLITICAL_NEWS_TOPICS = [
    # Vietnam Government & Economy
    "Vietnam government economic policy stock market 2025",
    "Vietnam monetary policy interest rate State Bank",
    "Vietnam fiscal policy tax regulations investment",
    "Vietnam Ministry of Finance securities regulations",
    # Stock Market Regulations
    "Vietnam stock market VN-Index policy regulations SSC",
    "HOSE HNX trading regulations new policy",
    "Vietnam foreign investment limit stock market",
    "Vietnam State Securities Commission new rules",
    # Fund & Investment Regulations
    "Vietnam mutual fund regulations management company",
    "Vietnam ETF fund policy investment regulations",
    "Vietnam investment fund tax law changes",
    "DCDS BVFED VESAF fund performance policy impact",
    # Banking & Interest Rates
    "State Bank of Vietnam interest rate decision",
    "Vietnam banking sector regulations new policy",
    "Vietnam credit growth policy bank lending",
    # Trade & Geopolitics
    "Vietnam trade policy US China impact stock",
    "Vietnam FDI foreign direct investment policy",
    "ASEAN Vietnam trade agreement market impact",
]

# Financial news domains to prioritize
FINANCIAL_DOMAINS = [
    "cafef.vn",
    "vietstock.vn",
    "vnexpress.net",
    "bloomberg.com",
    "reuters.com",
    "investing.com",
    "finance.yahoo.com",
    "marketwatch.com",
]


class NewsEnricher:
    """
    Enriches news items with additional context using Tavily Search API.
    Also provides political/policy news search capabilities for stocks and funds.
    """

    def __init__(self, custom_topics: list[str] | None = None):
        """
        Initialize NewsEnricher.

        Args:
            custom_topics: Optional list of custom search topics to add.
        """
        self.tavily = TavilyClient()
        self.search_topics = POLITICAL_NEWS_TOPICS.copy()
        if custom_topics:
            self.search_topics.extend(custom_topics)

    async def search_async(
        self,
        query: str,
        max_results: int = 3,
        include_domains: list[str] | None = None,
    ) -> str:
        """
        Search for a query and return a summarized context string.

        Args:
            query: The search query.
            max_results: Maximum number of results to return.
            include_domains: Optional list of domains to prioritize.
        """
        if not self.tavily.api_key:
            return ""

        return await self.tavily.get_search_context(
            query,
            max_results=max_results,
            search_depth="advanced" if include_domains else "basic",
        )

    async def search_raw_async(
        self,
        query: str,
        max_results: int = 5,
        include_domains: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search and return raw results with full metadata.

        Args:
            query: The search query.
            max_results: Maximum number of results.
            include_domains: Optional domains to include.

        Returns:
            List of search result dictionaries.
        """
        if not self.tavily.api_key:
            return []

        try:
            data = await self.tavily.search(
                query=query,
                max_results=max_results,
                include_domains=include_domains,
                search_depth="advanced",
            )
            return data.get("results", [])
        except Exception as e:
            logger.error(f"Search failed for '{query[:30]}...': {e}")
            return []

    def search(self, query: str, max_results: int = 3) -> str:
        """Synchronous wrapper for search."""
        return asyncio.run(self.search_async(query, max_results=max_results))

    async def search_political_news_async(
        self,
        topics: list[str] | None = None,
        max_results_per_topic: int = 3,
        max_topics: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Search for political/policy news affecting stocks and funds.

        Args:
            topics: Optional custom topics. Uses default POLITICAL_NEWS_TOPICS if None.
            max_results_per_topic: Max results per search topic.
            max_topics: Maximum number of topics to search (to limit API calls).

        Returns:
            List of unique news items with title, url, content, and source.
        """
        if not self.tavily.api_key:
            logger.warning("Tavily API key not set. Political news search disabled.")
            return []

        search_topics = topics or self.search_topics[:max_topics]
        all_results: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        logger.info(f"Searching {len(search_topics)} political news topics...")

        for topic in search_topics:
            logger.debug(f"Searching: {topic[:50]}...")
            results = await self.search_raw_async(
                query=topic,
                max_results=max_results_per_topic,
                include_domains=FINANCIAL_DOMAINS,
            )

            for result in results:
                url = result.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(
                        {
                            "title": result.get("title", ""),
                            "url": url,
                            "content": result.get("content", ""),
                            "source": result.get("url", "").split("/")[2]
                            if "/" in result.get("url", "")
                            else "",
                            "topic": topic,
                            "published_date": result.get("published_date", ""),
                        }
                    )

        logger.info(f"Found {len(all_results)} unique political news items.")
        return all_results

    def search_political_news(
        self,
        topics: list[str] | None = None,
        max_results_per_topic: int = 3,
        max_topics: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Synchronous wrapper for political news search.

        Args:
            topics: Optional custom topics.
            max_results_per_topic: Max results per topic.
            max_topics: Maximum topics to search.

        Returns:
            List of political news items.
        """
        return asyncio.run(
            self.search_political_news_async(
                topics=topics,
                max_results_per_topic=max_results_per_topic,
                max_topics=max_topics,
            )
        )

    def format_political_news_for_summary(
        self,
        news_items: list[dict[str, Any]],
        limit: int = 10,
    ) -> str:
        """
        Format political news items into a summary string for LLM context.

        Args:
            news_items: List of political news items.
            limit: Maximum items to include.

        Returns:
            Formatted string for LLM consumption.
        """
        if not news_items:
            return ""

        lines = ["## Political & Policy News Affecting Markets\n"]

        for i, item in enumerate(news_items[:limit], 1):
            title = item.get("title", "No title")
            source = item.get("source", "Unknown")
            content = item.get("content", "")[:200]  # Truncate content

            lines.append(f"**{i}. {title}**")
            lines.append(f"   Source: {source}")
            if content:
                lines.append(f"   Summary: {content}...")
            lines.append("")

        return "\n".join(lines)

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

    async def get_comprehensive_market_context_async(
        self,
        include_political: bool = True,
        political_topics_limit: int = 5,
        results_per_topic: int = 3,
    ) -> dict[str, Any]:
        """
        Get comprehensive market context including political news.

        Args:
            include_political: Whether to include political news search.
            political_topics_limit: Number of political topics to search.
            results_per_topic: Results per topic.

        Returns:
            Dictionary with political_news and formatted_context.
        """
        result = {
            "political_news": [],
            "formatted_context": "",
        }

        if include_political:
            political_news = await self.search_political_news_async(
                max_topics=political_topics_limit,
                max_results_per_topic=results_per_topic,
            )
            result["political_news"] = political_news
            result["formatted_context"] = self.format_political_news_for_summary(political_news)

        return result

    def get_comprehensive_market_context(
        self,
        include_political: bool = True,
        political_topics_limit: int = 5,
        results_per_topic: int = 3,
    ) -> dict[str, Any]:
        """Synchronous wrapper for comprehensive market context."""
        return asyncio.run(
            self.get_comprehensive_market_context_async(
                include_political=include_political,
                political_topics_limit=political_topics_limit,
                results_per_topic=results_per_topic,
            )
        )
