"""Shared WebSearchAPI.ai Client."""

import logging
import os
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class WebSearchApiClient:
    """Client for WebSearchAPI.ai."""

    BASE_URL = "https://api.websearchapi.ai/ai-search"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("WEBSEARCHAPI_KEY")
        if not self.api_key:
            logger.warning("WEBSEARCHAPI_KEY not found. Search will be disabled.")

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def search(
        self,
        query: str,
        max_results: int = 5,
        include_content: bool = True,
        include_answer: bool = False,
        days: int | None = None,
    ) -> dict[str, Any]:
        """
        Perform a search using WebSearchAPI.ai.

        Args:
            query: The search query.
            max_results: Maximum number of results.
            include_content: Whether to include content.
            include_answer: Whether to include an AI answer.
            days: Number of days to filter results (maps to timeframe).

        Returns:
            JSON response from API, normalized to match Tavily structure:
            {"results": [{"title": ..., "url": ..., "content": ..., "published_date": ...}]}
        """
        if not self.api_key:
            return {"results": []}

        # Map days to timeframe
        timeframe = "any"
        if days:
            if days <= 1:
                timeframe = "day"
            elif days <= 7:
                timeframe = "week"
            elif days <= 31:
                timeframe = "month"
            else:
                timeframe = "year"

        payload = {
            "query": query,
            "maxResults": max_results,
            "includeContent": include_content,
            "includeAnswer": include_answer,
            "timeframe": timeframe,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.BASE_URL, headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()
            data = response.json()

            # Normalize output to match Tavily structure for easier swapping
            # WebSearchAPI returns "organic" list
            organic = data.get("organic", [])
            normalized_results = []
            for item in organic:
                normalized_results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", item.get("description", "")),
                        "published_date": item.get("date", ""),
                    }
                )

            return {
                "results": normalized_results,
                "answer": data.get("answer", ""),
                "response_time": data.get("responseTime"),
            }
