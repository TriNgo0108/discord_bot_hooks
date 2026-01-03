import datetime
import time
from typing import Any

import feedparser


class FeedManager:
    def __init__(self):
        pass

    def fetch_feeds(self, feed_urls: list[str]) -> list[dict[str, Any]]:
        all_news = []
        for url in feed_urls:
            try:
                feed = feedparser.parse(url)
                if feed.bozo:
                    print(f"Error parsing feed {url}: {feed.bozo_exception}")
                    continue

                for entry in feed.entries:
                    news_item = self._parse_entry(entry, feed.feed.get("title", "Unknown Source"))
                    if news_item:
                        all_news.append(news_item)
            except Exception as e:
                print(f"Error fetching {url}: {e}")

        # Sort by published date, newest first
        all_news.sort(key=lambda x: x["published_at"], reverse=True)
        return all_news

    def _parse_entry(self, entry: Any, source_name: str) -> dict[str, Any] | None:
        try:
            # Handle different date formats
            published_at = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published_at = datetime.datetime.fromtimestamp(time.mktime(entry.published_parsed))
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                published_at = datetime.datetime.fromtimestamp(time.mktime(entry.updated_parsed))
            else:
                published_at = datetime.datetime.now()  # Fallback

            return {
                "title": entry.get("title", "No Title"),
                "link": entry.get("link", ""),
                "summary": entry.get("summary", "")[:200] + "..."
                if len(entry.get("summary", "")) > 200
                else entry.get("summary", ""),
                "source": source_name,
                "published_at": published_at,
                "id": entry.get("id", entry.get("link", "")),
            }
        except Exception as e:
            print(f"Error parsing entry: {e}")
            return None
