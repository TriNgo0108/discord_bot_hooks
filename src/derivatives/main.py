"""Main entry point for derivatives analysis."""

import argparse
import asyncio
import logging

import httpx
from dotenv import load_dotenv

load_dotenv()

from .config import DERIVATIVES_CONFIG  # noqa: E402
from .data_aggregator import DataAggregator  # noqa: E402
from .research_analyzer import ResearchAnalyzer  # noqa: E402

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def analyze_derivatives(instruments: list[str], send_discord: bool = True):
    """
    Main pipeline execution.
    """
    logger.info("=" * 60)
    logger.info("DERIVATIVES ANALYSIS PIPELINE")
    logger.info("=" * 60)

    # 1. Shared HTTP Client
    async with httpx.AsyncClient(timeout=DERIVATIVES_CONFIG.REQUEST_TIMEOUT) as client:
        # 2. Data Aggregation (VNStock uses internal requests, so no client passed)
        aggregator = DataAggregator()
        try:
            logger.info(f"Step 1: Fetching data for {instruments}...")
            market_data = await aggregator.fetch_all_market_data(instruments)

            futures_count = len(market_data.get("futures", []))
            # market_structure is where VNStock data is currently stored
            struct_count = len(market_data.get("market_structure", []))

            # Add to total counts
            logger.info(f"Fetched: {futures_count} futures, {struct_count} structural reports")

            # Ensure we have at least ONE type of data
            if futures_count == 0 and struct_count == 0:
                logger.warning("No data fetched. Check internet connection or APIs.")
                return

            # 3. Research & Analysis
            logger.info("Step 2: AI Research & Analysis...")
            # Pass shared client
            analyzer = ResearchAnalyzer(http_client=client)
            analysis = await analyzer.analyze(market_data)

            if not analysis:
                logger.error("Analysis failed.")
                return

            # Output results
            print("\n" + "=" * 30)
            print(f"MARKET SENTIMENT: {analysis.market_sentiment}")
            print("=" * 30)
            print("\nTOP FINDINGS:")
            for f in analysis.key_findings:
                print(f"- {f}")

            print("\nRECOMMENDATIONS:")
            for r in analysis.recommendations:
                print(f"- {r.direction} {r.instrument} ({r.confidence}/10): {r.reasoning[:100]}...")

            # 4. Discord Notification
            if send_discord and DERIVATIVES_CONFIG.DISCORD_WEBHOOK_URL:
                logger.info("Step 3: Sending Discord notification...")
                embed = analysis.to_discord_embed()

                await client.post(DERIVATIVES_CONFIG.DISCORD_WEBHOOK_URL, json={"embeds": [embed]})
                logger.info("Notification sent!")
            else:
                logger.info("Discord notification skipped (disabled or no URL configured)")

        finally:
            await aggregator.close()


def main():
    parser = argparse.ArgumentParser(description="Derivatives Market Analyzer")
    parser.add_argument(
        "--instruments",
        type=str,
        default="VN30F1M,VN30F2M",
        help="Comma-separated instruments (e.g. VN30F1M,VN30F2M)",
    )
    parser.add_argument("--no-discord", action="store_true", help="Disable Discord notifications")

    args = parser.parse_args()
    instruments = [i.strip() for i in args.instruments.split(",")]

    asyncio.run(analyze_derivatives(instruments, send_discord=not args.no_discord))


if __name__ == "__main__":
    main()
