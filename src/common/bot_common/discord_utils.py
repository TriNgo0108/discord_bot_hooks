"""Utilities for Discord interactions."""

import asyncio
import logging

from discord_webhook import DiscordEmbed, DiscordWebhook


def split_message(message: str, limit: int = 4000) -> list[str]:
    """
    Split a message into chunks within the character limit.
    Tries to split at newlines to preserve formatting.
    """
    if limit <= 0:
        raise ValueError("Limit must be greater than 0")

    if len(message) <= limit:
        return [message]

    chunks = []
    while message:
        if len(message) <= limit:
            chunks.append(message)
            break

        # Find the best split point
        # Try to find a newline within the last 1000 characters of the limit
        search_range_start = max(0, limit - 1000)
        search_range_end = limit

        # Look for the last newline in the safe zone
        last_newline = message.rfind("\n", search_range_start, search_range_end)

        split_index = last_newline + 1 if last_newline != -1 else limit

        # Append chunk and remove from message
        chunks.append(message[:split_index])
        message = message[split_index:]

    return chunks


async def send_discord_embeds(
    webhook_url: str,
    title_prefix: str,
    content: str,
    color: str,
    footer_text: str,
    logger_name: str = "discord_utils",
    split_limit: int = 4000,
) -> None:
    """
    Split content and send as Discord embeds via webhook.
    """

    logger = logging.getLogger(logger_name)
    webhook = DiscordWebhook(url=webhook_url)

    chunks = split_message(content, limit=split_limit)

    for i, chunk in enumerate(chunks):
        title = title_prefix
        if len(chunks) > 1:
            title += f" ({i + 1}/{len(chunks)})"

        # Create Embed
        embed = DiscordEmbed(
            title=title,
            description=chunk,
            color=color,
        )
        embed.set_footer(text=footer_text)

        webhook.add_embed(embed)

        # Execute in thread to avoid blocking async loop
        response = await asyncio.to_thread(webhook.execute)

        if response.status_code == 200:
            logger.info(f"Successfully sent chunk {i + 1}/{len(chunks)} to Discord.")
        else:
            logger.error(
                f"Failed to send chunk {i + 1} to Discord: {response.status_code} {response.text}"
            )

        # Clear embeds for next chunk
        webhook.remove_embeds()
