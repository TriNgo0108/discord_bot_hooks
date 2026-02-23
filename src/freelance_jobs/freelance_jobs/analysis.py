"""Job Analysis module using Z.AI (GLM-4.7)."""

import asyncio
import json
import logging
from typing import TypedDict

import httpx
from bot_common.zai_client import ZaiClient
from pydantic import BaseModel, Field, ValidationError

from freelance_jobs.constants import JOB_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)


class JobInput(TypedDict):
    """Input structure for job analysis."""

    title: str
    content: str
    url: str


class JobAnalysis(BaseModel):
    """Structured analysis of a job."""

    budget: str | None = Field(default=None, description="Budget or rate mentioned")
    skills: list[str] = Field(default_factory=list, description="List of technical skills")
    required_knowledge: list[str] = Field(
        default_factory=list,
        description="Required domain knowledge, qualifications, and experience",
    )
    remote_policy: str | None = Field(default=None, description="Remote work policy")
    duration: str | None = Field(default=None, description="Contract duration")
    posted_date: str | None = Field(default=None, description="Posted date")
    summary: str = Field(..., description="Concise summary of the role")


class JobAnalyzer:
    """Analyzes jobs using LLM."""

    def __init__(self, zai_client: ZaiClient) -> None:
        self.zai_client = zai_client

    async def analyze_jobs(self, jobs: list[JobInput]) -> list[JobAnalysis]:
        """
        Analyze a list of jobs to extract structured data.

        Args:
            jobs: List of job dictionaries with title and content.

        Returns:
            List of JobAnalysis objects matching the input order (if possible).
        """
        if not jobs:
            return []

        async def _analyze_chunk(chunk_jobs: list[JobInput]) -> list[JobAnalysis]:
            # Prepare input for the prompt
            jobs_content = "".join(
                f"\nJob {i + 1}:\nTitle: {job.get('title', 'Unknown')}\nContent: {job.get('content', '')}\n"
                for i, job in enumerate(chunk_jobs)
            )

            prompt = JOB_ANALYSIS_PROMPT.replace("${jobs_content}", jobs_content)

            messages = [
                {"role": "user", "content": prompt},
            ]

            try:
                response = await self.zai_client.chat_completion(
                    messages=messages,
                    temperature=0.1,  # Low temperature for extraction
                    timeout=300.0,  # Increased timeout for chunked job analysis
                )

                # Clean up potential markdown code blocks
                cleaned_response = response.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.startswith("```"):
                    cleaned_response = cleaned_response[3:]
                if cleaned_response.endswith("```"):
                    cleaned_response = cleaned_response[:-3]

                cleaned_response = cleaned_response.strip()

                data = json.loads(cleaned_response)

                # Validate with Pydantic
                analyses = [JobAnalysis(**item) for item in data]

                # Verify that the number of analyses matches chunk size, pad if not
                if len(analyses) < len(chunk_jobs):
                    logger.warning(
                        "Number of analyses (%d) is less than chunk size (%d). Padding.",
                        len(analyses),
                        len(chunk_jobs),
                    )
                    analyses.extend(
                        [
                            JobAnalysis(summary=job.get("content", "")[:100] + "...")
                            for job in chunk_jobs[len(analyses) :]
                        ]
                    )
                elif len(analyses) > len(chunk_jobs):
                    logger.warning("Number of analyses is greater than chunk size. Truncating.")
                    analyses = analyses[: len(chunk_jobs)]

                return analyses

            except (
                json.JSONDecodeError,
                ValidationError,
                httpx.HTTPError,
                httpx.TimeoutException,
            ) as e:
                logger.warning("Failed to process LLM chunk correctly: %s", e)
                # Fallback mapping: return generic summaries
                return [
                    JobAnalysis(summary=job.get("content", "")[:100] + "...") for job in chunk_jobs
                ]

        # Use batching to prevent ReadTimeout on large sets
        chunk_size = 3
        chunks = [jobs[i : i + chunk_size] for i in range(0, len(jobs), chunk_size)]

        logger.info("Analyzing %d jobs with Z.AI in %d chunks...", len(jobs), len(chunks))

        # We can run these concurrently, with gather. Z.AI API should handle a few concurrent requests
        # If rate-limiting becomes an issue, we could process sequentially instead.
        chunk_results = await asyncio.gather(*(_analyze_chunk(chunk) for chunk in chunks))

        all_analyses = [analysis for chunk_result in chunk_results for analysis in chunk_result]

        # Ensure we return exactly len(jobs) element mappings
        if len(all_analyses) > len(jobs):
            all_analyses = all_analyses[: len(jobs)]
        elif len(all_analyses) < len(jobs):
            all_analyses.extend(
                [
                    JobAnalysis(summary=jobs[i].get("content", "")[:100] + "...")
                    for i in range(len(all_analyses), len(jobs))
                ]
            )

        return all_analyses
