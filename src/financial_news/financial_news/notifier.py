import json
from typing import Any

import httpx


def send_discord_webhook(
    webhook_url: str, news_items: list[dict[str, Any]], summary: str = ""
) -> None:
    if not news_items:
        return

    with httpx.Client() as client:
        # Discord webhooks have limits (10 embeds per message, total size limits).
        # We'll send them in chunks or just the latest ones.
        # Let's limit to top 5 to avoid spam for now.

        # Send Summary First (if exists)
        if summary:
            try:
                # Split summary into chunks of 1900 characters to be safe (Discord limit 2000)
                # We split by newlines where possible to avoid breaking markdown
                header = ":flag_vn: **BẢN TIN TÀI CHÍNH HÀNG NGÀY**\n\n"
                current_message = header

                parts = summary.split("\n")

                for part in parts:
                    if len(current_message) + len(part) + 1 > 1900:
                        # Send current bucket
                        payload = {"content": current_message}
                        _post_to_discord(client, webhook_url, payload)
                        current_message = part + "\n"
                    else:
                        current_message += part + "\n"

                # Send remaining
                if current_message.strip():
                    if current_message == header:
                        pass
                    else:
                        payload = {"content": current_message}
                        _post_to_discord(client, webhook_url, payload)

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

            payload = {"embeds": embeds}

            try:
                _post_to_discord(client, webhook_url, payload)
            except Exception as e:
                print(f"Failed to send webhook chunk {i}: {e}")


def _post_to_discord(client: httpx.Client, webhook_url: str, payload: dict[str, Any]) -> None:
    response = client.post(
        webhook_url,
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    response.raise_for_status()
