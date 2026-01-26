"""Discord Webhook Client for Gmail Reader."""

import datetime
import logging
from typing import Any, Optional

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .config import CONFIG, DiscordConfig
from .utils import split_text_smartly

logger = logging.getLogger(__name__)


class DiscordClient:
    """Async Client for sending notifications to Discord."""

    def __init__(self, config: Optional[DiscordConfig] = None):
        self.config = config or CONFIG.discord

    async def send_summary(self, emails: list[dict[str, Any]]):
        """Send email summary to Discord."""
        if not self.config.webhook_url:
            logger.error("DISCORD_WEBHOOK_GMAIL not set.")
            return

        today_date = datetime.date.today().strftime("%Y-%m-%d")

        if not emails:
            await self._send_text(
                f"**Daily Gmail Summary** 📧 ({today_date})\n\nNo new emails in the last 24 hours. ✅"
            )
            return

        # Send header
        await self._send_embed(
            {
                "title": "📧 Daily Gmail Summary",
                "description": f"{len(emails)} emails received",
                "color": 0xEA4335,  # Gmail red
                "footer": {"text": today_date},
            }
        )

        # Send emails
        for email_data in emails:
            await self._send_email_embed(email_data)

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _send_text(self, content: str):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.config.webhook_url, json={"content": content})
                resp.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send Discord text: {e}")

    @retry(
        retry=retry_if_exception_type(httpx.HTTPError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _send_embed(self, embed: dict[str, Any]):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.config.webhook_url, json={"embeds": [embed]})
                resp.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to send Discord embed: {e}")

    async def _send_email_embed(self, email_data: dict[str, Any]):
        body_text = email_data.get("body_text", "") or "No content"
        subject = email_data.get("subject", "No Subject")[:256]
        sender = email_data.get("from", "Unknown")[:256]

        # Strip header noise
        lines = body_text.split("\n")
        clean_body = body_text

        chunks = split_text_smartly(clean_body)
        if not chunks:
            chunks = ["(No content)"]

        for i, chunk in enumerate(chunks):
            description = chunk
            # Append links to last chunk
            if i == len(chunks) - 1 and email_data.get("links"):
                description += "\n\n**🔗 Links:**\n"
                for text, url in email_data["links"]:
                    link_line = f"• [{text}]({url})\n"
                    # Ensure we don't exceed 4096 limit
                    if len(description) + len(link_line) < 4090:
                        description += link_line

            # Title logic
            if i == 0:
                title = subject
                author = {"name": sender}
            else:
                title = f"{subject} (Part {i + 1})"
                author = {}

            embed = {
                "title": title,
                "description": description,
                "color": 0x4285F4,
            }
            if author:
                embed["author"] = author

            if i == 0 and email_data.get("images"):
                embed["image"] = {"url": email_data["images"][0]}

            await self._send_embed(embed)
