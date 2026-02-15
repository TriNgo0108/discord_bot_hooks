"""Generates tech news content using GLM-4.7 and Tavily."""

import asyncio
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
        # 1. Search for news (Parallel Execution)
        today = datetime.now(UTC).strftime("%Y-%m-%d")

        # Query 1: General Tech News
        general_query = f"latest technology news software engineering AI development {today}"

        # Query 2: Framework & Library Updates
        framework_query = (
            f"latest software releases popular frameworks libraries database changelog {today}"
        )

        logger.info(f"Searching web for: {general_query} AND {framework_query}")

        general_context_task = self.tavily_client.get_search_context(
            query=general_query, search_depth="advanced", max_results=5
        )
        framework_context_task = self.tavily_client.get_search_context(
            query=framework_query, search_depth="advanced", max_results=5
        )

        results = await asyncio.gather(
            general_context_task, framework_context_task, return_exceptions=True
        )

        # Process results
        general_context = results[0] if isinstance(results[0], str) else ""
        framework_context = results[1] if isinstance(results[1], str) else ""

        full_context = (
            f"--- General Tech News ---\n{general_context}\n\n"
            f"--- Framework & Library Updates ---\n{framework_context}"
        )

        if not general_context and not framework_context:
            return "Unable to fetch tech news at this time. Network or API issue."

        # 2. Generate Summary
        prompt = NEWS_PROMPT.substitute(date=today, context=full_context)

        messages = [
            {"role": "system", "content": "You are a helpful tech news assistant."},
            {"role": "user", "content": prompt},
        ]

        logger.info("Generating news summary...")
        content = await self.zai_client.chat_completion(messages=messages)
        return content
