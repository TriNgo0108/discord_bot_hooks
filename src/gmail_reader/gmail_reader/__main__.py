"""Main entry point for Gmail Reader."""

import asyncio
import logging

from .config import CONFIG
from .discord_client import DiscordClient
from .imap_client import GmailClient
from .summarizer import AISummarizer

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def fetch_emails_sync() -> list:
    """Wrapper to run blocking IMAP operations in a thread."""

    def _fetch():
        with GmailClient(CONFIG.gmail) as client:
            return client.fetch_recent_emails(days=1)

    return await asyncio.to_thread(_fetch)


async def main():
    """Fetch, summarize, and notify about recent emails."""
    logger.info("Starting Gmail Reader (Async)...")

    # Initialize components with Dependency Injection
    summarizer = AISummarizer(CONFIG.ai)
    discord = DiscordClient(CONFIG.discord)

    # 1. Fetch Emails (Blocking I/O isolated in thread)
    logger.info("Fetching emails...")
    emails = await fetch_emails_sync()

    if not emails:
        logger.info("No new emails found.")
        await discord.send_summary([])
        return

    logger.info(f"Processing {len(emails)} emails...")

    # 2. Summarize Emails (Async I/O)
    # We process them sequentially or in small batches to preserve order/logging clearity
    # and avoid 429s on the AI API if it has strict limits.
    for i, email_data in enumerate(emails, 1):
        logger.info(f"[{i}/{len(emails)}] Summarizing: {email_data['subject'][:50]}...")
        summary = await summarizer.summarize(email_data["body_text"])
        if summary:
            email_data["body_text"] = summary

    # 3. Notify Discord (Async I/O)
    logger.info("Sending notifications to Discord...")
    await discord.send_summary(emails)
    logger.info("Done.")


if __name__ == "__main__":
    asyncio.run(main())
