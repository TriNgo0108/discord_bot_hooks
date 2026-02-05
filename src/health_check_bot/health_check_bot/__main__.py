import asyncio
import logging
import os

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def check_health():
    urls_env = os.getenv("HEALTH_CHECK_URLS")
    if not urls_env:
        logger.warning("HEALTH_CHECK_URLS environment variable is not set.")
        return

    urls = [url.strip() for url in urls_env.split(",") if url.strip()]

    if not urls:
        logger.warning("No URLs found in HEALTH_CHECK_URLS.")
        return

    async with httpx.AsyncClient() as client:
        for url in urls:
            logger.info(f"Checking {url}...")
            client.get(url, timeout=10.0)


if __name__ == "__main__":
    asyncio.run(check_health())
