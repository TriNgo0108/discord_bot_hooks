"""Main entry point for Freelance Job Search Hook."""

import asyncio
import logging
from datetime import UTC, datetime

from bot_common.tavily_client import TavilyClient
from bot_common.zai_client import ZaiClient

from freelance_jobs.analysis import JobAnalyzer
from freelance_jobs.config import Config
from freelance_jobs.constants import EMBED_COLOR
from freelance_jobs.job_finder import JobFinder
from freelance_jobs.keyword_selector import KeywordSelector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Run the job finder."""
    config = Config.from_env()

    if not config.DISCORD_WEBHOOK_URL:
        logger.error("DISCORD_WEBHOOK_FREELANCE_JOBS not set. Exiting.")
        return

    # Initialize services
    tavily_client = TavilyClient(api_key=config.TAVILY_API_KEY)
    zai_client = ZaiClient(api_key=config.ZAI_API_KEY)
    selector = KeywordSelector()
    analyzer = JobAnalyzer(zai_client)
    finder = JobFinder(tavily_client, analyzer)

    # 1. Select Keyword
    keyword = selector.get_random_keyword()
    logger.info("Selected keyword: %s", keyword)

    # 2. Find Jobs
    jobs = await finder.find_jobs(keyword)

    if not jobs:
        logger.info("No jobs found for this keyword.")
        return

    # 3. Publish to Discord using individual embeds
    from discord_webhook import DiscordEmbed, DiscordWebhook

    logger.info("Publishing %d jobs to Discord...", len(jobs))
    chunk_size = 10
    job_chunks = [jobs[i : i + chunk_size] for i in range(0, len(jobs), chunk_size)]

    for i, chunk in enumerate(job_chunks):
        webhook = DiscordWebhook(url=config.DISCORD_WEBHOOK_URL)

        if i == 0:
            webhook.content = f"### 💼 Remote & Freelance Search: **{keyword}**"

        for job in chunk:
            title = job.get("title", "No Title")
            url = job.get("url", "#")
            analysis = job.get("analysis")

            embed = DiscordEmbed(
                title=title[:256],
                url=url,
                color=EMBED_COLOR,
            )

            if analysis:
                embed.description = analysis.summary

                budget = analysis.budget or "N/A"
                duration = analysis.duration or "N/A"
                embed.add_embed_field(name="💰 Budget", value=budget, inline=True)
                embed.add_embed_field(name="⏳ Duration", value=duration, inline=True)

                remote = analysis.remote_policy or "N/A"
                skills = ", ".join(analysis.skills) if analysis.skills else "N/A"
                if len(skills) > 1024:
                    skills = skills[:1020] + "..."
                embed.add_embed_field(name="🏠 Remote", value=remote, inline=True)
                embed.add_embed_field(name="🛠 Skills", value=skills, inline=False)

                knowledge = (
                    ", ".join(analysis.required_knowledge) if analysis.required_knowledge else "N/A"
                )
                if len(knowledge) > 1024:
                    knowledge = knowledge[:1020] + "..."
                if knowledge != "N/A":
                    embed.add_embed_field(name="📚 Knowledge", value=knowledge, inline=False)
            else:
                snippet = job.get("content", "No description available.")
                if len(snippet) > 2048:
                    snippet = snippet[:2045] + "..."
                embed.description = snippet

            embed.set_footer(
                text=f"Powered by Tavily & GLM-4.7 • {datetime.now(UTC).strftime('%Y-%m-%d')}"
            )
            webhook.add_embed(embed)

        # Execute in thread to avoid blocking async loop
        response = await asyncio.to_thread(webhook.execute)
        if response.status_code in (200, 204):
            logger.info("Successfully sent chunk %d/%d to Discord.", i + 1, len(job_chunks))
        else:
            logger.error(
                "Failed to send chunk %d to Discord: %s %s",
                i + 1,
                response.status_code,
                response.text,
            )

        if i < len(job_chunks) - 1:
            await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.exception(f"Unhandled exception in Freelance Jobs Hook: {e}")
