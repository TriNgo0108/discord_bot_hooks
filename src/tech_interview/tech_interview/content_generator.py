"""Generates English grammar content using GLM-4.7."""

import logging

from bot_common.tavily_client import TavilyClient
from bot_common.zai_client import ZaiClient

from tech_interview.constants import GRAMMAR_PROMPT, SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class ContentGenerator:
    """Generates grammar learning content using AI with web search enhancement."""

    def __init__(self, zai_client: ZaiClient, tavily_client: TavilyClient) -> None:
        self.zai_client = zai_client
        self.tavily_client = tavily_client

    async def generate_grammar_lesson(self, topic: str) -> str:
        """Generate a grammar lesson for the given topic."""
        # 1. Fetch context from web
        search_query = topic
        logger.info("Searching web for: %s", search_query)

        context = await self.tavily_client.get_search_context(
            query=search_query, search_depth="basic", max_results=3
        )

        if not context:
            context = "No external context available."

        # 2. Build prompt with instruction hierarchy
        user_prompt = GRAMMAR_PROMPT.format(topic=topic, context=context)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        logger.info("Generating grammar lesson for topic: %s", topic)
        content = await self.zai_client.chat_completion(messages=messages)
        return content
