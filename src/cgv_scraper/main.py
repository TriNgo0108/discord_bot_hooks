import datetime
import logging
import os
import re

import httpx
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Only load .env for local development
if os.getenv("ENV") != "production":
    from dotenv import load_dotenv

    load_dotenv()

# Configuration from environment variables
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_CGV")

# Scraping Configuration
CGV_NOW_SHOWING_URL = os.getenv(
    "CGV_NOW_SHOWING_URL", "https://www.cgv.vn/default/movies/now-showing.html"
)
CGV_COMING_SOON_URL = os.getenv(
    "CGV_COMING_SOON_URL", "https://www.cgv.vn/default/movies/coming-soon-1.html"
)

URLS = {
    "Now Showing": CGV_NOW_SHOWING_URL,
    "Coming Soon": CGV_COMING_SOON_URL,
}

# Timeout Configuration (in milliseconds for Playwright, seconds for httpx)
PAGE_LOAD_TIMEOUT = int(os.getenv("PAGE_LOAD_TIMEOUT_MS", "120000"))
SELECTOR_TIMEOUT = int(os.getenv("SELECTOR_TIMEOUT_MS", "45000"))
RENDER_DELAY = int(os.getenv("RENDER_DELAY_MS", "5000"))
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT_SECONDS", "30"))

# Browser Configuration
USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
)
VIEWPORT_WIDTH = int(os.getenv("VIEWPORT_WIDTH", "1280"))
VIEWPORT_HEIGHT = int(os.getenv("VIEWPORT_HEIGHT", "720"))


def get_movies(url):
    """Scrape movie information from CGV website using Playwright."""
    logger.info("Scraping %s", url)

    with sync_playwright() as playwright_instance:
        launch_args = {
            "headless": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        }

        logger.debug("Launching browser...")
        browser = playwright_instance.chromium.launch(**launch_args)

        context = browser.new_context(
            user_agent=USER_AGENT,
            locale="vi-VN",
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
        )
        page = context.new_page()

        try:
            # Navigate and wait for content to load
            logger.debug("Navigating to page...")
            page.goto(url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)

            # Wait for movie grid to appear
            logger.debug("Waiting for selector...")
            page.wait_for_selector(".products-grid .item", timeout=SELECTOR_TIMEOUT)

            # Small delay to ensure dynamic content is fully rendered
            page.wait_for_timeout(RENDER_DELAY)

            html_content = page.content()
            logger.info("Successfully retrieved content (Length: %d)", len(html_content))

        except Exception as e:
            logger.error("Playwright error: %s", e)
            html_content = ""
        finally:
            browser.close()

    # Parse the HTML content
    soup = BeautifulSoup(html_content, "html.parser")
    movies = []
    items = soup.select(".products-grid .item")

    if not items:
        logger.warning("No items found.")
        return []

    for item in items:
        title_element = item.select_one(".product-name a")
        if not title_element:
            continue

        title = title_element.get_text(strip=True)
        link = title_element["href"]

        # Extract movie poster image (try to get highest quality)
        image_url = None
        img_element = item.select_one("img")
        if img_element:
            # Try different attributes for best quality
            image_url = (
                img_element.get("data-original")
                or img_element.get("data-src")
                or img_element.get("src")
            )
            # CGV often has resized images, try to get full size
            if image_url:
                # Remove common resize parameters
                image_url = re.sub(r"/resize/\d+x\d+/", "/", image_url)
                image_url = re.sub(r"\?.*$", "", image_url)  # Remove query params

        # Release date extraction
        release_date = "N/A"
        date_element = item.select_one(".cgv-movie-date")

        if not date_element:
            item_text = item.get_text()
            # Try to match various date formats
            date_patterns = [
                r"Khởi chiếu:\s*([\d/]+(?:/\d+)?(?:/\d+)?)",  # dd/mm/yyyy
                r"(\d{1,2}/\d{1,2}/\d{4})",  # Full date format
                r"(\d{1,2}/\d{1,2})",  # dd/mm format
            ]
            for pattern in date_patterns:
                date_match = re.search(pattern, item_text)
                if date_match:
                    release_date = date_match.group(1)
                    break
        else:
            release_date = date_element.get_text(strip=True)

        movies.append(
            {
                "title": title,
                "link": link,
                "release_date": release_date,
                "image": image_url,
            }
        )

    return movies


def send_discord_message(section_name, movies):
    """Send movie list to Discord webhook with embeds."""
    if not DISCORD_WEBHOOK_URL:
        logger.warning("DISCORD_WEBHOOK_CGV not set, skipping Discord send.")
        return

    if not movies:
        return

    today = datetime.date.today()

    # Create embeds for each movie (Discord allows max 10 embeds per message)
    embeds = []

    for movie in movies:
        release_date = movie["release_date"]

        # Format date if only day number
        if release_date != "N/A" and release_date.isdigit():
            day = int(release_date)
            if day < today.day:
                next_month = today.month + 1 if today.month < 12 else 1
                release_date = f"{day:02d}/{next_month:02d}"
            else:
                release_date = f"{day:02d}/{today.month:02d}"

        # Different colors for sections
        section_color = (
            0x00D166 if "Now" in section_name else 0xFFA500
        )  # Green for Now Showing, Orange for Coming Soon

        embed = {
            "title": movie["title"],
            "url": movie["link"],
            "color": section_color,
        }

        if release_date != "N/A":
            embed["footer"] = {"text": f"📅 {release_date}"}

        if movie.get("image"):
            embed["thumbnail"] = {"url": movie["image"]}

        embeds.append(embed)

    # Send header as a larger embed first
    header_color = (
        0x00D166 if "Now" in section_name else 0xFFA500
    )  # Green for Now Showing, Orange for Coming Soon
    header_embed = {
        "title": f"🎬 {section_name}",
        "color": header_color,
        "description": f"{len(embeds)} movies",
    }
    httpx.post(DISCORD_WEBHOOK_URL, json={"embeds": [header_embed]}, timeout=HTTP_TIMEOUT)

    # Send movies in batches of 10 (Discord limit)
    for i in range(0, len(embeds), 10):
        batch = embeds[i : i + 10]
        httpx.post(DISCORD_WEBHOOK_URL, json={"embeds": batch}, timeout=HTTP_TIMEOUT)


def main():
    for name, url in URLS.items():
        logger.info("Scraping %s...", name)
        try:
            movies = get_movies(url)
            logger.info("Found %d movies.", len(movies))
            send_discord_message(name, movies)
        except Exception as e:
            logger.error("Error scraping %s: %s", name, e)


if __name__ == "__main__":
    main()
