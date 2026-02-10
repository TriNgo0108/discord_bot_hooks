import argparse
import logging
import sys

from .db import fetch_incomplete_improvements
from .notifier import format_improvement_message, send_discord_webhook

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Run improvement notifier.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print message instead of sending to Discord"
    )
    args = parser.parse_args()

    try:
        logger.info("Fetching incomplete improvements...")
        improvements = fetch_incomplete_improvements()
        logger.info(f"Found {len(improvements)} incomplete improvements.")

        message = format_improvement_message(improvements)

        if args.dry_run:
            logger.info("DRY RUN MODE. Message output:")
            print("-" * 40)
            print(message)
            print("-" * 40)
        else:
            send_discord_webhook(message)

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
