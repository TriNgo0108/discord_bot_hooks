"""Job Analysis module using Z.AI (GLM-4.7)."""

import json
import logging
from typing import TypedDict

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

        # Prepare input for the prompt
        jobs_content = ""
        for i, job in enumerate(jobs):
            jobs_content += f"\nJob {i + 1}:\nTitle: {job['title']}\nContent: {job['content']}\n"

        prompt = JOB_ANALYSIS_PROMPT.replace("${jobs_content}", jobs_content)

        messages = [
            {"role": "user", "content": prompt},
        ]

        logger.info("Analyzing %d jobs with Z.AI...", len(jobs))

        try:
            response = await self.zai_client.chat_completion(
                messages=messages,
                temperature=0.1,  # Low temperature for extraction
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
            return analyses

        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning("Failed to parse LLM response: %s", e)
            return [JobAnalysis(summary=job.get("content", "")[:100] + "...") for job in jobs]
        except Exception as e:
            logger.exception("Unexpected error analyzing jobs: %r", e)
            raise
