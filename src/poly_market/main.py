"""Main orchestrator for Polymarket analysis pipeline."""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime

from .config import AIConfig, POLYMARKET_CONFIG
from .models import PolymarketEvent, TradingSuggestion
from .polymarket_client import PolymarketClient
from .research_analyzer import ResearchAnalyzer
from .suggestion_engine import SuggestionEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def analyze_polymarket(
    max_events: int = 10,
    max_markets: int = 3,
    min_confidence: int = 5,
    min_edge: float = 0.10,
    output_file: str | None = None,
) -> list[TradingSuggestion]:
    """
    Main entry point for Polymarket analysis.

    Pipeline:
    1. Fetch top active events from Polymarket
    2. Research each market topic with Perplexity API
    3. Analyze with Z.AI for probability assessment
    4. Generate ranked suggestions

    Args:
        max_events: Maximum number of events to analyze
        max_markets: Maximum markets per event to analyze
        min_confidence: Minimum confidence score for suggestions
        min_edge: Minimum edge percentage for suggestions
        output_file: Optional path to save JSON results

    Returns:
        List of TradingSuggestion objects
    """
    logger.info("=" * 60)
    logger.info("POLYMARKET ANALYSIS PIPELINE")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    # Initialize components
    ai_config = AIConfig.from_env()
    analyzer = ResearchAnalyzer(ai_config)
    engine = SuggestionEngine(min_confidence=min_confidence, min_edge=min_edge)

    # Step 1: Fetch events
    logger.info("Step 1: Fetching events from Polymarket...")
    async with PolymarketClient() as client:
        events = await client.fetch_events(limit=max_events)
        logger.info(f"Fetched {len(events)} events")

    if not events:
        logger.warning("No events found. Exiting.")
        return []

    # Step 2 & 3: Research and analyze each market
    logger.info("Step 2-3: Researching and analyzing markets...")
    all_results = []

    for event in events:
        # Limit markets per event
        markets = event.markets[:max_markets]

        for market in markets:
            logger.info(f"Processing: {market.question[:50]}...")

            try:
                research, analysis = await analyzer.research_and_analyze(market)

                if research and analysis:
                    all_results.append((event, market, research, analysis))
                    logger.info(
                        f"  → {analysis.recommendation.value} "
                        f"(edge: {analysis.edge_percentage:.1f}%, "
                        f"confidence: {analysis.confidence}/10)"
                    )

            except Exception as e:
                logger.error(f"Failed to process market {market.id}: {e}")
                continue

            # Rate limiting delay
            await asyncio.sleep(2)

    # Step 4: Generate suggestions
    logger.info("Step 4: Generating trading suggestions...")
    suggestions = engine.generate_suggestions_batch(all_results)

    # Output results
    logger.info("=" * 60)
    logger.info(f"RESULTS: {len(suggestions)} actionable suggestions")
    logger.info("=" * 60)

    if suggestions:
        print("\n" + engine.format_suggestions_report(suggestions))

        # Save to file if requested
        if output_file:
            save_results(suggestions, output_file)

    return suggestions


def save_results(
    suggestions: list[TradingSuggestion],
    output_file: str,
) -> None:
    """Save suggestions to JSON file."""
    try:
        data = {
            "timestamp": datetime.now().isoformat(),
            "total_suggestions": len(suggestions),
            "suggestions": [s.to_dict() for s in suggestions],
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved to: {output_file}")

    except Exception as e:
        logger.error(f"Failed to save results: {e}")


async def send_discord_notification(
    suggestions: list[TradingSuggestion],
    webhook_url: str | None = None,
) -> None:
    """Send suggestions to Discord webhook."""
    webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")

    if not webhook_url:
        logger.warning("No Discord webhook URL configured")
        return

    if not suggestions:
        logger.info("No suggestions to send")
        return

    import httpx

    # Format message
    embeds = []
    for s in suggestions[:5]:  # Limit to top 5
        color = 0x00FF00 if s.recommendation.value == "LONG" else 0xFF0000
        embeds.append(
            {
                "title": f"{s.recommendation.value}: {s.market_question[:100]}",
                "description": s.reasoning[:500],
                "color": color,
                "fields": [
                    {"name": "Current Odds", "value": f"{s.current_odds:.1%}", "inline": True},
                    {
                        "name": "Est. Probability",
                        "value": f"{s.estimated_probability:.1%}",
                        "inline": True,
                    },
                    {"name": "Edge", "value": f"{s.edge:.1%}", "inline": True},
                    {"name": "Confidence", "value": f"{s.confidence}/10", "inline": True},
                ],
                "footer": {"text": f"Event: {s.event_title}"},
            }
        )

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                webhook_url,
                json={
                    "content": "📊 **Polymarket Trading Suggestions**",
                    "embeds": embeds,
                },
            )
            logger.info("Discord notification sent")

    except Exception as e:
        logger.error(f"Failed to send Discord notification: {e}")


def main() -> None:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze Polymarket prediction markets")
    parser.add_argument(
        "--events",
        type=int,
        default=10,
        help="Maximum events to analyze",
    )
    parser.add_argument(
        "--markets",
        type=int,
        default=3,
        help="Maximum markets per event",
    )
    parser.add_argument(
        "--confidence",
        type=int,
        default=5,
        help="Minimum confidence score (1-10)",
    )
    parser.add_argument(
        "--edge",
        type=float,
        default=0.10,
        help="Minimum edge percentage (0.10 = 10%%)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON file path",
    )
    parser.add_argument(
        "--discord",
        action="store_true",
        help="Send results to Discord webhook",
    )

    args = parser.parse_args()

    # Run analysis
    suggestions = asyncio.run(
        analyze_polymarket(
            max_events=args.events,
            max_markets=args.markets,
            min_confidence=args.confidence,
            min_edge=args.edge,
            output_file=args.output,
        )
    )

    # Send Discord notification if requested
    if args.discord and suggestions:
        asyncio.run(send_discord_notification(suggestions))

    # Exit with appropriate code
    sys.exit(0 if suggestions else 1)


if __name__ == "__main__":
    main()
