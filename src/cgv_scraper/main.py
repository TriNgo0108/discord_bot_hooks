import os
import re

import httpx
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Only load .env for local development
if os.getenv("ENV") != "production":
    from dotenv import load_dotenv

    load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_CGV")

URLS = {
    "Now Showing": "https://www.cgv.vn/default/movies/now-showing.html",
    "Coming Soon": "https://www.cgv.vn/default/movies/coming-soon-1.html",
}


def get_movies(url):
    """Scrape movie information from CGV website using Playwright."""
    print(f"DEBUG: Launching browser for {url}...")
    with sync_playwright() as playwright_instance:
        # Launch headless browser with anti-bot args
        browser = playwright_instance.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="vi-VN",
            viewport={"width": 1280, "height": 720},
        )
        page = context.new_page()

        try:
            # Navigate and wait for content to load
            print("DEBUG: Navigating to page...")
            page.goto(url, wait_until="domcontentloaded", timeout=90000)  # Increased timeout

            # Wait for movie grid to appear (longer timeout for CI environments)
            print("DEBUG: Waiting for selector...")
            page.wait_for_selector(".products-grid .item", timeout=60000)  # Increased timeout

            # Small delay to ensure dynamic content is fully rendered
            page.wait_for_timeout(5000)  # Increased delay

            html_content = page.content()
            print(f"DEBUG: Successfully retrieved content (Length: {len(html_content)})")

        except Exception as e:
            print(f"ERROR: Playwright error: {e}")
            html_content = ""
        finally:
            browser.close()

    soup = BeautifulSoup(html_content, "html.parser")
    movies = []

    items = soup.select(".products-grid .item")

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
        print("DISCORD_WEBHOOK_CGV not set, skipping Discord send.")
        return

    if not movies:
        return

    import datetime

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
    httpx.post(DISCORD_WEBHOOK_URL, json={"embeds": [header_embed]})

    # Send movies in batches of 10 (Discord limit)
    for i in range(0, len(embeds), 10):
        batch = embeds[i : i + 10]
        httpx.post(DISCORD_WEBHOOK_URL, json={"embeds": batch})


def main():
    for name, url in URLS.items():
        print(f"Scraping {name}...")
        try:
            movies = get_movies(url)
            print(f"Found {len(movies)} movies.")
            send_discord_message(name, movies)
        except Exception as e:
            print(f"Error scraping {name}: {e}")


if __name__ == "__main__":
    main()
