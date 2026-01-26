import datetime
import time
from typing import Any

import feedparser
import httpx
from bs4 import BeautifulSoup


class FeedManager:
    def __init__(self):
        pass

    def fetch_feeds(self, feed_urls: list[str]) -> list[dict[str, Any]]:
        all_news = []
        for url in feed_urls:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                response = httpx.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()

                feed = feedparser.parse(response.content)
                if feed.bozo:
                    # Ignore bozo errors which are just warnings usually
                    pass
                    # print(f"Error parsing feed {url}: {feed.bozo_exception}")
                    # continue

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

            raw_summary = entry.get("summary", "")
            summary = self._clean_html(raw_summary)

            return {
                "title": entry.get("title", "No Title"),
                "link": entry.get("link", ""),
                "summary": summary,
                "source": source_name,
                "published_at": published_at,
                "id": entry.get("id", entry.get("link", "")),
            }
        except Exception as e:
            print(f"Error parsing entry: {e}")
            return None

    def _clean_html(self, html_content: str) -> str:
        if not html_content:
            return ""

        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # Remove images
            for img in soup.find_all("img"):
                img.decompose()

            # Convert links to Markdown
            for a in soup.find_all("a", href=True):
                text = a.get_text(strip=True)
                if text:
                    a.replace_with(f"[{text}]({a['href']})")

            # Get text and clean up whitespace
            text = soup.get_text(separator=" ", strip=True)
            return text
        except Exception:
            return html_content
