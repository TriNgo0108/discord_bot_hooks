"""AI Summarizer for Emails."""

import logging
from typing import Optional

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .config import CONFIG, AIConfig

logger = logging.getLogger(__name__)

GMAIL_SUMMARY_PROMPT = """You are an executive assistant extracting decision-critical info from emails.

## Rules
1. NO FLUFF - Never write "The email says" or "In conclusion"
2. START immediately with TL;DR
3. PRESERVE important links as [text](url)
4. Use SPECIFIC numbers, dates, names - no vague language
5. If no action required, state "FYI only"

## Email Content
{email_content}
"""


class AISummarizer:
    """Uses LLM to summarize email content asynchronously."""

    def __init__(self, config: Optional[AIConfig] = None):
        self.config = config or CONFIG.ai

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=False,  # Don't crash main loop on AI fail, just return None
    )
    async def summarize(self, text: str) -> Optional[str]:
        """Summarize text using configured AI model."""
        if not self.config.api_key:
            logger.warning("AI_API_KEY not set. Skipping summarization.")
            return None

        prompt = GMAIL_SUMMARY_PROMPT.format(email_content=text)

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.config.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.config.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are an executive assistant extracting decision-critical info from emails. Be concise and actionable.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.3,
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.warning(f"AI summarization failed: {e}")
            raise  # Let tenacity handle retry

        return None
