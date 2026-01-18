import logging
import os

from .feed_manager import FeedManager
from .fmarket_client import FmarketClient
from .news_enricher import NewsEnricher
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
    fmarket_client = FmarketClient()

    # Fetch Vietnam News
    vn_news = feed_manager.fetch_feeds(VIETNAM_FEED_URLS)
    logger.info(f"Fetched {len(vn_news)} Vietnamese news items.")

    # Fetch Global News
    global_news = feed_manager.fetch_feeds(GLOBAL_FEED_URLS)
    logger.info(f"Fetched {len(global_news)} Global news items.")

    # Fetch Fmarket News
    fmarket_news = fmarket_client.get_market_news()
    logger.info(f"Fetched {len(fmarket_news)} Fmarket news items.")

    # Fetch Market Data
    top_funds = fmarket_client.get_top_funds(limit=10)
    gold_prices = fmarket_client.get_gold_prices()
    bank_rates = fmarket_client.get_bank_rates()

    # Combine News
    combined_news = fmarket_news + vn_news[:5] + global_news[:5]

    if not combined_news:
        logger.info("No news found.")
        return

    # Enrich News (Top 3 items)
    logger.info("Enriching top news with Web Context...")
    enricher = NewsEnricher()
    # Prioritize enriching the most critical or diverse items if possible,
    # but for now, just the top 3 of the combined list.
    combined_news = enricher.enrich_news_items(combined_news, limit=3)

    logger.info(f"Sending {len(combined_news)} items to Discord...")

    # Generate Summary
    logger.info("Generating AI Summary...")
    summarizer = NewsSummarizer()

    market_stats = {"top_funds": top_funds, "gold_prices": gold_prices, "bank_rates": bank_rates}

    summary_text = summarizer.summarize(combined_news, market_stats)

    send_discord_webhook(webhook_url, combined_news, summary_text)
    logger.info("Done.")


if __name__ == "__main__":
    main()
