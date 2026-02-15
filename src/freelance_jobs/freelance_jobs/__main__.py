"""Main entry point for Freelance Job Search Hook."""

import asyncio
import logging
from datetime import UTC, datetime

from bot_common.tavily_client import TavilyClient
from bot_common.discord_utils import send_discord_embeds

from freelance_jobs.config import Config
from freelance_jobs.constants import EMBED_COLOR
from freelance_jobs.job_finder import JobFinder
from freelance_jobs.keyword_selector import KeywordSelector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run the job finder."""
    config = Config.from_env()

    if not config.DISCORD_WEBHOOK_URL:
        logger.error("DISCORD_WEBHOOK_FREELANCE_JOBS not set. Exiting.")
        return

    # Initialize services
    tavily_client = TavilyClient(api_key=config.TAVILY_API_KEY)
    selector = KeywordSelector()
    finder = JobFinder(tavily_client)

    # 1. Select Keyword
    keyword = selector.get_random_keyword()
    logger.info(f"Selected keyword: {keyword}")

    # 2. Find Jobs
    jobs = await finder.find_jobs(keyword)

    if not jobs:
        logger.info("No jobs found for this keyword.")
        return

    # 3. Format Content
    content = f"### 💼 Remote & Freelance Search: {keyword}\n\n"
    for job in jobs:
        title = job.get("title", "No Title")
        url = job.get("url", "#")
        snippet = job.get("content", "No description available.")
        if len(snippet) > 200:
            snippet = snippet[:200] + "..."
        content += f"**[{title}]({url})**\n> {snippet}\n\n"

    # 4. Publish to Discord
    await send_discord_embeds(
        webhook_url=config.DISCORD_WEBHOOK_URL,
        title_prefix=f"🚀 Remote & Freelance Opportunities: {keyword}",
        content=content,
        color=EMBED_COLOR,
        footer_text=f"Powered by Tavily • {datetime.now(UTC).strftime('%Y-%m-%d')}",
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.exception(f"Unhandled exception in Freelance Jobs Hook: {e}")
