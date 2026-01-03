import json
import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)


class NewsSummarizer:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = "google/gemma-3-27b-it:free"
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

    def summarize(self, news_items: list[dict[str, Any]]) -> str:
        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY not found. Skipping summarization.")
            return ""

        if not news_items:
            return ""

        # Prepare the input text for the LLM
        news_text = ""
        for i, item in enumerate(news_items, 1):
            news_text += f"{i}. [{item['source']}] {item['title']}: {item['summary']}\n"

        prompt = (
            "You are a professional financial analyst for the Vietnamese market.\n"
            "Analyze the following financial news headlines and summaries.\n"
            "Write a concise, professional daily financial briefing for a Vietnamese investor.\n"
            "Focus on the most important market trends, opportunities, and risks.\n"
            "The output should be in Vietnamese (Tiếng Việt) and formatted as a clear Markdown summary.\n"
            "Do not list every single article, but synthesize the key points.\n\n"
            f"Here is the news data:\n{news_text}"
        )

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "top_p": 1,
            "temperature": 0.7,
            "repetition_penalty": 1,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            # OpenRouter optional headers for rankings
            # "HTTP-Referer": "https://github.com/TriNgo0108/discord_bot_hooks",
            # "X-Title": "Discord Bot Hooks",
        }

        try:
            response = requests.post(self.api_url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            data = response.json()

            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            else:
                logger.error(f"Unexpected API response: {data}")
                return ""

        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return ""
