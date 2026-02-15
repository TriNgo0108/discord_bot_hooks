import json
import unittest
from unittest.mock import AsyncMock, MagicMock
from freelance_jobs.analysis import JobAnalysis, JobAnalyzer, JobInput
from freelance_jobs.job_finder import JobFinder


class TestFreelanceJobFinder(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_zai_client = MagicMock()
        self.mock_zai_client.chat_completion = AsyncMock()

        self.mock_tavily_client = MagicMock()
        self.mock_tavily_client.search = AsyncMock()

        self.job_analyzer = JobAnalyzer(self.mock_zai_client)
        self.job_finder = JobFinder(self.mock_tavily_client, self.job_analyzer)

    async def test_job_analyzer_success(self):
        jobs = [
            {
                "title": "Python Dev",
                "content": "Remote Python job. Budget $50/hr.",
                "url": "http://example.com/1",
            },
        ]

        mock_response = json.dumps(
            [
                {
                    "budget": "$50/hr",
                    "skills": ["Python"],
                    "remote_policy": "Remote",
                    "duration": None,
                    "posted_date": None,
                    "summary": "Python job summary",
                }
            ]
        )

        self.mock_zai_client.chat_completion.return_value = mock_response

        analyses = await self.job_analyzer.analyze_jobs(jobs)

        self.assertEqual(len(analyses), 1)
        self.assertEqual(analyses[0].budget, "$50/hr")
        self.assertEqual(analyses[0].skills, ["Python"])
        self.assertEqual(analyses[0].summary, "Python job summary")

        # Verify prompt construction (partial check)
        call_args = self.mock_zai_client.chat_completion.call_args[1]
        self.assertIn("Remote Python job", call_args["messages"][0]["content"])

    async def test_job_analyzer_empty(self):
        analyses = await self.job_analyzer.analyze_jobs([])
        self.assertEqual(analyses, [])
        self.mock_zai_client.chat_completion.assert_not_called()

    async def test_job_analyzer_failure(self):
        jobs = [{"title": "Job 1", "content": "Content 1", "url": "http://1"}]

        self.mock_zai_client.chat_completion.side_effect = Exception("API Error")

        analyses = await self.job_analyzer.analyze_jobs(jobs)

        # Should fallback to basic summary
        self.assertEqual(len(analyses), 1)
        self.assertIn("Content 1", analyses[0].summary)

    async def test_job_finder_integration(self):
        # Mock Tavily response
        self.mock_tavily_client.search.return_value = {
            "results": [{"title": "Job A", "url": "http://a", "content": "Content A", "score": 0.9}]
        }

        # Mock Zai response
        mock_zai_response = json.dumps(
            [
                {
                    "budget": "$100",
                    "skills": ["Skill A"],
                    "remote_policy": "Hybrid",
                    "duration": "1 week",
                    "posted_date": "Today",
                    "summary": "Summary A",
                }
            ]
        )
        self.mock_zai_client.chat_completion.return_value = mock_zai_response

        enriched_jobs = await self.job_finder.find_jobs("keyword")

        self.assertEqual(len(enriched_jobs), 1)
        job = enriched_jobs[0]
        self.assertEqual(job["title"], "Job A")
        self.assertIsNotNone(job["analysis"])
        self.assertEqual(job["analysis"].budget, "$100")
