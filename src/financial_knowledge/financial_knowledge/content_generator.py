"""Generates financial knowledge content using GLM-4.7."""

import logging

from bot_common.tavily_client import TavilyClient
from bot_common.zai_client import ZaiClient

logger = logging.getLogger(__name__)

KNOWLEDGE_PROMPT = """
# ROLE
You are a wise and experienced Financial Mentor for Vietnamese investors. 
Your goal is to explain complex financial concepts in a simple, engaging, and actionable way.

# TOPIC
Please explain the concept: **{topic}**

# CONTEXT (Web Search Results)
{context}

# INSTRUCTIONS
1.  **Language**: Strictly **Vietnamese** (Tiếng Việt).
2.  **Tone**: Professional, encouraging, educational, and easy to understand (bình dân học vụ).
3.  **Structure**:
    *   **🎯 Định nghĩa (Definition)**: What is it? (Simple explanation).
    *   **🔍 Tại sao quan trọng? (Why it matters)**: How does it affect an investor's wallet?
    *   **💡 Ví dụ thực tế (Real-world Example)**: Give a concrete example (use VND numbers or relatable scenarios).
    *   **⚠️ Lưu ý/Rủi ro (Watch out)**: Common mistakes or misconceptions.
    *   **🚀 Hành động (Actionable Tip)**: Quick tip for the reader.

# FORMATTING
-   Use Markdown.
-   Use clear headings.
-   Use bullet points for readability.
-   **Do not** output any pre-text or post-text (no "Here is your response").

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
        search_query = f"{topic} financial concept definition example"
        logger.info(f"Searching web for: {search_query}")

        context = await self.tavily_client.get_search_context(
            query=search_query, search_depth="basic", max_results=3
        )

        if not context:
            context = "No external context available."

        # 2. Generate Content
        prompt = KNOWLEDGE_PROMPT.format(topic=topic, context=context)

        messages = [
            {"role": "system", "content": "You are a helpful financial AI assistant."},
            {"role": "user", "content": prompt},
        ]

        logger.info(f"Generating content for topic: {topic}")
        content = await self.zai_client.chat_completion(messages=messages)
        return content
