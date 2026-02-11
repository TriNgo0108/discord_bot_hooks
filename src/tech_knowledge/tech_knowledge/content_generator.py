"""Generates technical knowledge content using GLM-4.7."""

import logging

from bot_common.tavily_client import TavilyClient
from bot_common.zai_client import ZaiClient
from tech_knowledge.constants import KNOWLEDGE_PROMPT

logger = logging.getLogger(__name__)


class ContentGenerator:
    """Generates content using AI with Web Search enhancement."""

    def __init__(self, zai_client: ZaiClient, tavily_client: TavilyClient) -> None:
        self.zai_client = zai_client
        self.tavily_client = tavily_client

    async def generate_knowledge(self, topic: str) -> str:
        """Generate a knowledge article for the given topic."""
        # 1. Fetch Context from Web
        search_query = f"{topic} advanced concepts best practices"
        logger.info(f"Searching web for: {search_query}")

        context = await self.tavily_client.get_search_context(
            query=search_query, search_depth="basic", max_results=3
        )

        if not context:
            context = "No external context available."

        # 2. Generate Content
        prompt = KNOWLEDGE_PROMPT.format(topic=topic, context=context)

        messages = [
            {"role": "system", "content": "You are an expert software engineer."},
            {"role": "user", "content": prompt},
        ]

        logger.info(f"Generating content for topic: {topic}")
        content = await self.zai_client.chat_completion(messages=messages)
        return content
