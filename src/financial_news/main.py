import logging
import os

from .feed_manager import FeedManager
from .fmarket_client import FmarketClient
from .market_enricher import MarketEnricher
from .news_enricher import NewsEnricher
from .notifier import send_discord_webhook
from .stock_client import StockClient
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
    top_funds = fmarket_client.get_top_funds(limit=20, include_holdings=True)
    watchlist_funds = fmarket_client.get_funds_by_codes(
        ["DCDS", "DCDE", "BVFED", "VESAF", "SSISCA", "E1VFVN30"]
    )
    logger.info(f"Fetched {len(watchlist_funds)} watchlist funds.")

    gold_prices = fmarket_client.get_gold_prices()
    bank_rates = fmarket_client.get_bank_rates()

    # Fetch VN30 Stock Data
    logger.info("Fetching VN30 data...")
    stock_client = StockClient(source="VCI")
    vn30_index = stock_client.get_vn30_index_history(days=7)
    vn30_current = stock_client.get_vn30_index()
    vn30_symbols = list(stock_client.get_vn30_symbols())
    vn30_top_movers = stock_client.get_vn30_top_movers(limit=5)

    logger.info(
        f"VN30 Index: {vn30_current.get('current', 'N/A')} ({vn30_current.get('change_percent', 0):+.2f}%)"
    )

    # Fetch Political/Policy News
    logger.info("Fetching political/policy news about stocks and funds...")
    enricher = NewsEnricher()
    political_news = enricher.search_political_news(
        max_topics=5,  # Search top 5 topics
        max_results_per_topic=3,
    )
    logger.info(f"Fetched {len(political_news)} political news items.")

    # Combine News (including political news)
    combined_news = fmarket_news + vn_news[:5] + global_news[:5]

    if not combined_news and not political_news:
        logger.info("No news found.")
        return

    # Enrich News (Top 3 items)
    logger.info("Enriching top news with Web Context...")
    combined_news = enricher.enrich_news_items(combined_news, limit=3)

    # Build initial market stats
    political_context = enricher.format_political_news_for_summary(political_news, limit=10)
    market_stats = {
        "top_funds": top_funds,
        "watchlist_funds": watchlist_funds,
        "gold_prices": gold_prices,
        "bank_rates": bank_rates,
        "vn30_index": vn30_index,
        "vn30_current": vn30_current,
        "vn30_symbols": vn30_symbols,
        "top_movers": vn30_top_movers,
        "political_news": political_news,
        "political_context": political_context,
    }

    # Enrich Market Data with Perplexity
    logger.info("Enriching market data with Perplexity...")
    market_enricher = MarketEnricher()
    perplexity_context = market_enricher.enrich_market_stats(market_stats)

    # Add Perplexity context to market_stats for summarizer
    market_stats["perplexity_context"] = perplexity_context

    logger.info(f"Sending {len(combined_news)} items to Discord...")

    # Generate Summary
    logger.info("Generating AI Summary...")
    summarizer = NewsSummarizer()

    summary_text = summarizer.summarize(combined_news, market_stats)

    send_discord_webhook(webhook_url, combined_news, summary_text)
    logger.info("Done.")


if __name__ == "__main__":
    main()
