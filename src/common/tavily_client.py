"""Shared Tavily API Client."""

import logging
import os
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class TavilyClient:
    """Client for Tavily Search API."""

    BASE_URL = "https://api.tavily.com/search"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            logger.warning("TAVILY_API_KEY not found. Search will be disabled.")

    @retry(
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def search(
        self,
        query: str,
        search_depth: str = "basic",
        max_results: int = 5,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        include_answer: bool = False,
        include_raw_content: bool = False,
        include_images: bool = False,
    ) -> dict[str, Any]:
        """
        Perform a search using Tavily API.

        Args:
            query: The search query.
            search_depth: "basic" or "advanced".
            max_results: Maximum number of results.
            include_domains: List of domains to include.
            exclude_domains: List of domains to exclude.
            include_answer: Whether to include a short answer.
            include_raw_content: Whether to include raw content.
            include_images: Whether to include images.

        Returns:
            JSON response from Tavily API.
        """
        if not self.api_key:
            return {"results": []}

        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": search_depth,
            "max_results": max_results,
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
            "include_images": include_images,
        }

        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains

        async with httpx.AsyncClient() as client:
            response = await client.post(self.BASE_URL, json=payload, timeout=30.0)
            response.raise_for_status()
            return response.json()

    async def get_search_context(
        self,
        query: str,
        search_depth: str = "basic",
        max_results: int = 5,
        max_tokens: int = 4000,
    ) -> str:
        """
        Get a context string suitable for LLM injection.
        """
        if not self.api_key:
            return ""

        try:
            data = await self.search(
                query=query,
                search_depth=search_depth,
                max_results=max_results,
            )

            results = data.get("results", [])
            if not results:
                return ""

            context_parts = []
            for i, result in enumerate(results, 1):
                part = f"Source {i}: {result['title']}\nURL: {result['url']}\nContent: {result['content']}"
                context_parts.append(part)

            return "\n\n".join(context_parts)

        except Exception as e:
            logger.error(f"Tavily search context failed: {e}")
            return ""
