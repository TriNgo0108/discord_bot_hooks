"""Finds freelance jobs using Tavily."""

import logging
from typing import TypedDict

from bot_common.tavily_client import TavilyClient

from freelance_jobs.constants import JOB_SEARCH_QUERY_TEMPLATE

logger = logging.getLogger(__name__)


class Job(TypedDict):
    title: str
    url: str
    content: str
    score: float


class JobFinder:
    """Finds jobs using Web Search."""

    def __init__(self, tavily_client: TavilyClient) -> None:
        self.tavily_client = tavily_client

    async def find_jobs(self, keyword: str) -> list[Job]:
        """Find recent freelance jobs for the given keyword."""
        search_query = JOB_SEARCH_QUERY_TEMPLATE.format(keyword=keyword)
        logger.info(f"Searching web for: {search_query}")

        try:
            # We use 'news' or 'advanced' depth to get recent results
            response = await self.tavily_client.search(
                query=search_query,
                search_depth="advanced",
                max_results=5,
                include_domains=None,  # We want broad search but maybe exclude saturated platforms later
                days=3,  # Fresh content only
            )
            # Cast results to Job TypedDict
            results: list[Job] = response.get("results", [])
            return results
        except Exception as e:
            logger.error(f"Job search failed: {e}")
            return []
