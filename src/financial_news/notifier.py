import json
from typing import Any

import httpx


def send_discord_webhook(
    webhook_url: str, news_items: list[dict[str, Any]], summary: str = ""
) -> None:
    if not news_items:
        return

    # Discord webhooks have limits (10 embeds per message, total size limits).
    # We'll send them in chunks or just the latest ones.
    # Let's limit to top 5 to avoid spam for now.

    # Send Summary First (if exists)
    if summary:
        try:
            # Check length limit
            if len(summary) > 1900:
                summary = summary[:1900] + "...\n(Truncated)"

            payload = {
                "username": "Financial News Bot",
                "content": f"**Daily Financial Briefing**\n\n{summary}\n\n**Latest News:**",
            }
            response = httpx.post(
                webhook_url,
                content=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
        except Exception as e:
            print(f"Failed to send summary: {e}")

    chunk_size = 5
    for i in range(0, len(news_items), chunk_size):
        chunk = news_items[i : i + chunk_size]

        embeds = []
        for item in chunk:
            embed = {
                "title": item["title"][:250],
                "url": item["link"],
                "description": item["summary"][:500] + "..."
                if len(item["summary"]) > 500
                else item["summary"],
                "color": 3447003,  # Blueish
                "footer": {
                    "text": f"{item['source']} • {item['published_at'].strftime('%Y-%m-%d %H:%M')}"
                },
            }
            embeds.append(embed)

        payload = {"username": "Financial News Bot", "embeds": embeds}

        try:
            response = httpx.post(
                webhook_url,
                content=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
        except Exception as e:
            print(f"Failed to send webhook chunk {i}: {e}")
