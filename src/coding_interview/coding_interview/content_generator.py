"""Generates tech interview content using GLM-4.7."""

import logging

from bot_common.tavily_client import TavilyClient
from bot_common.zai_client import ZaiClient
from tech_interview.constants import CODING_QUESTION_PROMPT, INTERVIEW_PROMPT

logger = logging.getLogger(__name__)


class ContentGenerator:
    """Generates content using AI with Web Search enhancement."""

    def __init__(self, zai_client: ZaiClient, tavily_client: TavilyClient) -> None:
        self.zai_client = zai_client
        self.tavily_client = tavily_client

    async def generate_interview_question(self, topic: str, topic_type: str = "general") -> str:
        """Generate an interview question and answer for the given topic."""
        # 1. Fetch Context from Web
        search_query = f"tech interview question {topic} best answer"
        logger.info(f"Searching web for: {search_query}")

        context = await self.tavily_client.get_search_context(
            query=search_query, search_depth="basic", max_results=3
        )

        if not context:
            context = "No external context available."

        # 2. Select Prompt based on type
        if topic_type == "coding":
            template = CODING_QUESTION_PROMPT
            system_role = "You are a Senior Technical Interviewer specializing in Algorithms."
        else:
            template = INTERVIEW_PROMPT
            system_role = "You are an expert technical interviewer."

        prompt = template.format(topic=topic, context=context)

        messages = [
            {"role": "system", "content": system_role},
            {"role": "user", "content": prompt},
        ]

        logger.info(f"Generating content for topic: {topic} ({topic_type})")
        content = await self.zai_client.chat_completion(messages=messages)
        return content
