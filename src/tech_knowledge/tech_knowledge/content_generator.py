"""Generates technical knowledge content using GLM-4.7."""

import logging

from bot_common.tavily_client import TavilyClient
from bot_common.zai_client import ZaiClient

logger = logging.getLogger(__name__)

KNOWLEDGE_PROMPT = """
# ROLE
You are a Senior Staff Engineer and Technical Mentor.
Your goal is to provide a "Knowledge Drop" on a specific technical topic for software engineers.

# TOPIC
Please explain: **{topic}**

# CONTEXT (Web Search Results)
{context}

# INSTRUCTIONS
1.  **Language**: Strictly **English**.
2.  **Tone**: Professional, technical, yet concise and insightful.
3.  **Audience**: Mid-to-Senior level engineers. (Don't explain variables or loops, focus on concepts/patterns).
4.  **Structure**:
    *   **💡 Core Concept**: Brief definition.
    *   **⚙️ How it works**: Technical details/internals.
    *   **✅ Best Practices**: When to use it? How to use it right?
    *   **❌ Anti-Patterns**: What to avoid?
    *   **💻 Code Snippet**: A small, idiomatic example (if applicable).

# FORMATTING
-   Use Markdown.
-   Use syntax highlighting for code blocks (e.g., ```python ... ```).
-   **Do not** output any pre-text or post-text.

# OUTPUT
"""


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
