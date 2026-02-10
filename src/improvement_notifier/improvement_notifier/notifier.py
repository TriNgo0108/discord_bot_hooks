import logging
from datetime import datetime

import httpx

from .config import settings
from .models import Improvement

logger = logging.getLogger(__name__)


def format_improvement_message(improvements: list[Improvement]) -> str:
    """Format improvements into a Discord message."""
    if not improvements:
        return "You're all set! No incomplete improvements. 🚀"

    total_count = len(improvements)
    today_date = datetime.now().strftime("%Y-%m-%d")

    message = f"**Incomplete Improvements** 🛠️ ({today_date})\n"
    message += f"**Total Pending: {total_count}**\n\n"

    for imp in improvements:
        # Use a bullet point or checkbox style
        # Truncate content if it's extremely long, though Discord has a limit handled by sender
        content_preview = imp.content
        if len(content_preview) > 100:
            content_preview = content_preview[:97] + "..."

        message += f"☐ `[{imp.id}]` {content_preview} _({imp.created_at.strftime('%Y-%m-%d')})_\n"

    return message.strip()


def send_discord_webhook(message: str) -> None:
    """Send message to Discord webhook with chunking."""
    if not settings.DISCORD_WEBHOOK_IMPROVEMENT:
        logger.warning("DISCORD_WEBHOOK_IMPROVEMENT not set. Skipping sending.")
        return

    # Discord limit is 2000 characters
    LIMIT = 2000

    if len(message) <= LIMIT:
        _send_chunk(message)
    else:
        # Split message
        parts = []
        while len(message) > 0:
            if len(message) <= LIMIT:
                parts.append(message)
                break

            # Find closest newline before limit
            split_at = message.rfind("\n", 0, LIMIT)
            if split_at == -1:
                split_at = LIMIT  # Hard split if no newline

            parts.append(message[:split_at])
            message = message[split_at:]

        for part in parts:
            _send_chunk(part)


def _send_chunk(content: str) -> None:
    """Helper to send a single chunk."""
    try:
        response = httpx.post(
            settings.DISCORD_WEBHOOK_IMPROVEMENT, json={"content": content}, timeout=10.0
        )
        response.raise_for_status()
        logger.info("Message sent to Discord successfully.")
    except httpx.HTTPError as e:
        logger.error(f"Failed to send webhook: {e}")
        raise
