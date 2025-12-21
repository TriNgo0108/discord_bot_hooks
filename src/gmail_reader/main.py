import datetime
import email
import imaplib
import os
import re
from email.header import decode_header

import httpx

# Only load .env for local development
if os.getenv("ENV") != "production":
    from dotenv import load_dotenv

    load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_GMAIL")
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")


def decode_mime_header(header_value):
    """Decode MIME encoded header to string."""
    if not header_value:
        return "(No Value)"

    decoded_parts = decode_header(header_value)
    result = ""
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            result += part.decode(encoding or "utf-8", errors="ignore")
        else:
            result += part
    return result


def parse_html_links(html_content):
    """Parse HTML content and extract clickable links as (label, url) tuples."""
    links = []
    # Match <a href="url">text</a> patterns
    link_pattern = r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>([^<]*)</a>'
    matches = re.findall(link_pattern, html_content, re.IGNORECASE)
    for url, text in matches:
        text = text.strip()
        if url and not url.startswith("mailto:"):
            # Clean up the text
            text = re.sub(r"\s+", " ", text)

            # If text is empty or is a URL itself, extract domain as label
            if not text or text.startswith("http://") or text.startswith("https://"):
                # Extract domain from URL for a cleaner label
                domain_match = re.search(r"https?://(?:www\.)?([^/]+)", url)
                text = domain_match.group(1) if domain_match else "Link"

            if len(text) > 50:
                text = text[:47] + "..."
            links.append((text, url))
    return links[:5]  # Limit to 5 links per email


def parse_html_images(html_content):
    """Parse HTML content and extract valid image URLs, filtering out tracking pixels."""
    images = []
    # Match <img src="url"> patterns
    img_pattern = r'<img[^>]*src=["\']([^"\']+)["\'][^>]*>'
    matches = re.findall(img_pattern, html_content, re.IGNORECASE)
    for url in matches:
        # Skip tracking pixels and tiny images, keep actual content images
        if (
            url
            and not any(
                skip in url.lower() for skip in ["tracking", "pixel", "1x1", "spacer", "blank"]
            )
            and url.startswith(("http://", "https://"))
        ):
            images.append(url)
    return images[:1]  # Return only first image to avoid spam


def convert_html_to_plain_text(html_content):
    """Convert HTML content to readable plain text, preserving basic formatting."""
    # Remove style and script tags
    text = re.sub(r"<style[^>]*>.*?</style>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Convert <br> and <p> to newlines
    text = re.sub(r"<br[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    # Remove all other HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode HTML entities
    text = (
        text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    )
    # Clean up whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    return text.strip()


def strip_urls_from_text(text):
    """Remove raw HTTP/HTTPS URLs from text and clean up leftover artifacts."""
    # Remove URLs (http, https)
    text = re.sub(r"https?://[^\s<>\"']+", "", text)
    # Clean up leftover punctuation and whitespace
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\(\s*\)", "", text)  # Remove empty parentheses
    text = re.sub(r"\[\s*\]", "", text)  # Remove empty brackets
    return text.strip()


def fetch_recent_emails():
    """Fetch emails from the last 24 hours using IMAP."""
    if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
        print("GMAIL_ADDRESS or GMAIL_APP_PASSWORD not set.")
        return []

    try:
        # Connect to Gmail IMAP
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        mail.select("INBOX")

        # Search for unread emails from the last 24 hours
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%d-%b-%Y")
        status, message_ids = mail.search(None, f"(UNSEEN SINCE {yesterday})")

        if status != "OK":
            print("Failed to search emails.")
            return []

        email_ids = message_ids[0].split()
        print(f"Found {len(email_ids)} messages.")

        emails = []

        # Process all emails
        for email_id in email_ids:
            status, msg_data = mail.fetch(email_id, "(RFC822)")

            if status != "OK":
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject = decode_mime_header(msg["Subject"])
            sender = decode_mime_header(msg["From"])

            # Get content from body
            snippet = ""
            html_content = ""
            links = []
            images = []

            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain" and not snippet:
                        body = part.get_payload(decode=True)
                        if body:
                            snippet = body.decode("utf-8", errors="ignore")[:800]
                    elif content_type == "text/html" and not html_content:
                        body = part.get_payload(decode=True)
                        if body:
                            html_content = body.decode("utf-8", errors="ignore")
            else:
                body = msg.get_payload(decode=True)
                if body:
                    content_type = msg.get_content_type()
                    if content_type == "text/html":
                        html_content = body.decode("utf-8", errors="ignore")
                    else:
                        snippet = body.decode("utf-8", errors="ignore")[:800]

            # Extract links and images from HTML
            if html_content:
                links = parse_html_links(html_content)
                images = parse_html_images(html_content)
                # If no plain text, convert HTML to text
                if not snippet:
                    snippet = convert_html_to_plain_text(html_content)[:800]

            emails.append(
                {
                    "subject": subject,
                    "from": sender,
                    "snippet": strip_urls_from_text(snippet.replace("\n", " ").replace("\r", "")),
                    "links": links,
                    "images": images,
                }
            )

        mail.logout()
        return emails

    except Exception as e:
        print(f"IMAP error: {e}")
        return []


def send_discord_webhook(emails):
    """Send email summary to Discord webhook using embeds."""
    if not DISCORD_WEBHOOK_URL:
        print("DISCORD_WEBHOOK_GMAIL not set.")
        return

    today_date = datetime.date.today().strftime("%Y-%m-%d")

    if not emails:
        message = (
            f"**Daily Gmail Summary** 📧 ({today_date})\n\nNo new emails in the last 24 hours. ✅"
        )
        httpx.post(DISCORD_WEBHOOK_URL, json={"content": message})
        return

    # Send header
    header_embed = {
        "title": "📧 Daily Gmail Summary",
        "description": f"{len(emails)} emails received",
        "color": 0xEA4335,  # Gmail red
        "footer": {"text": today_date},
    }
    httpx.post(DISCORD_WEBHOOK_URL, json={"embeds": [header_embed]})

    # Send each email as an embed
    for email_data in emails:
        # Build description with snippet
        description = email_data["snippet"][:500] if email_data["snippet"] else "No content preview"

        # Add formatted links
        if email_data["links"]:
            description += "\n\n**🔗 Links:**\n"
            for text, url in email_data["links"]:
                description += f"• [{text}]({url})\n"

        embed = {
            "title": email_data["subject"][:256],  # Discord title limit
            "description": description[:4096],  # Discord description limit
            "color": 0x4285F4,  # Google blue
            "author": {"name": email_data["from"][:256]},
        }

        # Add image if available
        if email_data["images"]:
            embed["image"] = {"url": email_data["images"][0]}

        httpx.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]})


def main():
    """Main entry point for Gmail reader."""
    print("Fetching emails via IMAP...")
    emails = fetch_recent_emails()
    print(f"Sending {len(emails)} emails to Discord...")
    send_discord_webhook(emails)


if __name__ == "__main__":
    main()
