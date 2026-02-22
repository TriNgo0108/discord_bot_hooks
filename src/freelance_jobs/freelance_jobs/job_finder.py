"""Finds freelance jobs using Tavily."""

import logging
from typing import TypedDict

from bot_common.tavily_client import TavilyClient

from freelance_jobs.analysis import JobAnalysis, JobAnalyzer, JobInput
from freelance_jobs.constants import JOB_SEARCH_QUERY_TEMPLATE, JOB_SITES

logger = logging.getLogger(__name__)


class Job(TypedDict):
    title: str
    url: str
    content: str
    score: float
    analysis: JobAnalysis | None


class JobFinder:
    """Finds jobs using Web Search."""

    def __init__(self, tavily_client: TavilyClient, analyzer: JobAnalyzer) -> None:
        self.tavily_client = tavily_client
        self.analyzer = analyzer

    async def find_jobs(self, keyword: str) -> list[Job]:
        """Find and analyze recent freelance jobs for the given keyword."""
        search_query = JOB_SEARCH_QUERY_TEMPLATE.format(keyword=keyword)
        logger.info("Searching web for: %s", search_query)

        try:
            # We use 'news' or 'advanced' depth to get recent results
            response = await self.tavily_client.search(
                query=search_query,
                search_depth="advanced",
                max_results=5,
                include_domains=list(JOB_SITES),
            )

            raw_results = response.get("results", [])
            if not raw_results:
                return []

            # Prepare for analysis
            job_inputs: list[JobInput] = [
                {
                    "title": r.get("title", ""),
                    "content": r.get("content", ""),
                    "url": r.get("url", ""),
                }
                for r in raw_results
            ]

            # Analyze using LLM
            analyses = await self.analyzer.analyze_jobs(job_inputs)

            # Merge results
            enriched_jobs: list[Job] = []
            for i, raw in enumerate(raw_results):
                job: Job = {
                    "title": raw.get("title", ""),
                    "url": raw.get("url", ""),
                    "content": raw.get("content", ""),
                    "score": raw.get("score", 0.0),
                    "analysis": analyses[i] if i < len(analyses) else None,
                }
                enriched_jobs.append(job)

            return enriched_jobs

        except Exception as e:
            logger.error("Job search failed: %s", e)
            return []
