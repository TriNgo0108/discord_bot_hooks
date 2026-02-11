"""Generates tech news content using GLM-4.7 and Tavily."""

import logging
from datetime import UTC, datetime

from bot_common.tavily_client import TavilyClient
from bot_common.zai_client import ZaiClient

from tech_news.constants import NEWS_PROMPT

logger = logging.getLogger(__name__)


class ContentGenerator:
    """Generates tech news content."""

    def __init__(self, zai_client: ZaiClient, tavily_client: TavilyClient) -> None:
        self.zai_client = zai_client
        self.tavily_client = tavily_client

    async def generate_news(self) -> str:
        """Generate a tech news summary."""
        # 1. Search for news
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        search_query = f"latest technology news software engineering AI development {today}"
        logger.info(f"Searching web for: {search_query}")

        context = await self.tavily_client.get_search_context(
            query=search_query, search_depth="advanced", max_results=7
        )

        if not context:
            return "Unable to fetch tech news at this time. Network or API issue."

        # 2. Generate Summary
        prompt = NEWS_PROMPT.substitute(date=today, context=context)

        messages = [
            {"role": "system", "content": "You are a helpful tech news assistant."},
            {"role": "user", "content": prompt},
        ]

        logger.info("Generating news summary...")
        content = await self.zai_client.chat_completion(messages=messages)
        return content
