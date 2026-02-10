"""Shared Z.AI (GLM-4.7) API Client."""

import logging
import os

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class ZaiClient:
    """Client for Z.AI API (GLM models)."""

    BASE_URL = "https://api.z.ai/api/coding/paas/v4"
    DEFAULT_MODEL = "glm-4.7"

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("ZAI_API_KEY")
        self.model = model or self.DEFAULT_MODEL
        if not self.api_key:
            logger.warning("ZAI_API_KEY not found. AI generation will be disabled.")

    @retry(
        retry=retry_if_exception_type(
            (
                httpx.HTTPStatusError,
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.ReadTimeout,
            )
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        timeout: float = 60.0,
    ) -> str:
        """
        Send a chat completion request to Z.AI.

        Args:
            messages: List of message dicts (role, content).
            temperature: Sampling temperature.
            json_mode: Whether to enforce JSON output (if supported by prompt/model).
            timeout: Request timeout.

        Returns:
            The content of the response message.
        """
        if not self.api_key:
            raise ValueError("ZAI_API_KEY is not set.")

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        # Note: GLM-4.7 might not strictly support "response_format": {"type": "json_object"}
        # in the same way OpenAI does, so we rely on prompt engineering for JSON usually.
        # But if the API supports it, we could add it here. For now, we keep it simple.

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self.BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
