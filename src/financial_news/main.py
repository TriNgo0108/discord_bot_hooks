import logging
import os

from .feed_manager import FeedManager
from .notifier import send_discord_webhook
from .summarizer import NewsSummarizer

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Configuration
# Users should set these in their .env or environment
VIETNAM_FEED_URLS = [
    "https://cafef.vn/rss/tai-chinh.rss",
    "https://vietstock.vn/rss",
    "https://vnexpress.net/rss/kinh-doanh.rss",
]

GLOBAL_FEED_URLS = [
    "https://finance.yahoo.com/news/rssindex",
    "https://www.investing.com/rss/news.rss",
]


def main():
    webhook_url = os.getenv("DISCORD_WEBHOOK_FINANCE")
    if not webhook_url:
        logger.error("Environment variable DISCORD_WEBHOOK_FINANCE is not set.")
        return

    logger.info("Starting Financial News Fetcher...")

    feed_manager = FeedManager()

    # Fetch Vietnam News
    vn_news = feed_manager.fetch_feeds(VIETNAM_FEED_URLS)
    logger.info(f"Fetched {len(vn_news)} Vietnamese news items.")

    # Fetch Global News
    global_news = feed_manager.fetch_feeds(GLOBAL_FEED_URLS)
    logger.info(f"Fetched {len(global_news)} Global news items.")

    # Combine and Sort (Optional: could keep separate or filter by keywords)
    # For now, let's just take the top 3 from each to send daily/hourly
    # Or maybe filter by time (last 24h) if running daily.

    # Let's assume this runs periodically and we want the absolute latest.
    # A simple strategy is sending the top 5 distinct items from combined list.

    combined_news = vn_news[:5] + global_news[:5]

    if not combined_news:
        logger.info("No news found.")
        return

    logger.info(f"Sending {len(combined_news)} items to Discord...")

    # Generate Summary
    logger.info("Generating AI Summary...")
    summarizer = NewsSummarizer()
    summary_text = summarizer.summarize(combined_news)

    send_discord_webhook(webhook_url, combined_news, summary_text)
    logger.info("Done.")


if __name__ == "__main__":
    main()
