import datetime
import email
import html
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
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


def summarize_content(text):
    """Summarize text using OpenRouter."""
    if not OPENROUTER_API_KEY:
        print("OPENROUTER_API_KEY not set. Skipping summarization.")
        return None

    try:
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "google/gemma-3-27b-it:free",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that summarizes emails. "
                        "Keep the summary concise and focused on the key information. "
                        "IMPORTANT: You MUST preserve all links from the original text in Markdown format [text](url). "
                        "Do not use other markdown formatting (like italics/headings) other than bolding key terms.",
                    },
                    {"role": "user", "content": f"Summarize this email content:\n\n{text[:10000]}"},
                ],
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Summarization failed: {e}")
        return None


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

    # Noise terms for links (text-based)
    skip_terms = [
        "unsubscribe",
        "preference",
        "view in browser",
        "privacy policy",
        "terms of service",
        "manage subscription",
    ]

    # Tracking URL patterns to filter out
    tracking_patterns = [
        # Email service providers / Marketing platforms
        "click.mailchimp.com",
        "links.email.",
        "track.customer.io",
        "tracking.",
        "t.dripemail2.com",
        "email.mg.",
        "link.mail.",
        "trk.klclick.com",
        "clicks.beehiiv.com",
        "open.substack.com",
        "email.substack.com",
        "mailtrack.",
        "t.sidekickopen",
        "mandrillapp.com/track",
        "list-manage.com/track",
        # Analytics / Tracking services
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "/track/click",
        "/track/open",
        "trk=",
        "mc_cid=",
        "mc_eid=",
        # Generic tracking patterns
        "redirect.",
        "/r/",  # Common redirect pattern
        "click.",
        "go.link",
        "links.e.",
        "elink.",
        "t.co/",  # Twitter shortener often used for tracking
        "bit.ly/",
        # Social / Confirmation / Utility
        "confirm",
        "verify",
    ]

    for url, text in matches:
        text = text.strip()
        if url and not url.startswith("mailto:"):
            # Filter out tracking URLs
            url_lower = url.lower()
            if any(pattern in url_lower for pattern in tracking_patterns):
                continue

            # Clean up the text
            text = re.sub(r"\s+", " ", text)

            # If text is empty or is a URL itself, extract domain as label
            if not text or text.startswith("http://") or text.startswith("https://"):
                # Extract domain from URL for a cleaner label
                domain_match = re.search(r"https?://(?:www\.)?([^/]+)", url)
                text = domain_match.group(1) if domain_match else "Link"

            # Filter out noise links (by text)
            if any(term in text.lower() for term in skip_terms):
                continue

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


def convert_html_to_markdown(html_content):
    """Convert HTML content to Discord Markdown."""
    if not html_content:
        return ""

    # Basic cleanup
    text = re.sub(r"<style[^>]*>.*?</style>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Convert simple tags
    text = re.sub(r"<b>(.*?)</b>", r"**\1**", text, flags=re.IGNORECASE)
    text = re.sub(r"<strong>(.*?)</strong>", r"**\1**", text, flags=re.IGNORECASE)
    text = re.sub(r"<i>(.*?)</i>", r"*\1*", text, flags=re.IGNORECASE)
    text = re.sub(r"<em>(.*?)</em>", r"*\1*", text, flags=re.IGNORECASE)

    # Convert links
    # Convert links
    def replace_link(match):
        url = match.group(1)
        content = match.group(2).strip()

        # Remove tags from the link content to see if it has visible text
        # (e.g., skip links that only contain images or are empty)
        visible_text = re.sub(r"<[^>]+>", "", content).strip()

        if not visible_text:
            return ""

        return f"[{visible_text}]({url})"

    text = re.sub(
        r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', replace_link, text, flags=re.IGNORECASE
    )

    # Convert lists
    text = re.sub(r"<li>", "\n• ", text, flags=re.IGNORECASE)
    text = re.sub(r"</li>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<ul>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</ul>", "\n", text, flags=re.IGNORECASE)

    # Convert <br>, <p>, <div>, <tr>, headers
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</div>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</tr>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</h[1-6]>", "\n\n", text, flags=re.IGNORECASE)

    # Remove remaining tags
    text = re.sub(r"<[^>]+>", "", text)

    return clean_text_content(text)


def clean_text_content(text):
    """Clean up text by decoding entities and removing invisible characters."""
    if not text:
        return ""

    # Decode HTML entities (Robustly) - Loop to handle double encoding
    for _ in range(3):
        new_text = html.unescape(text)
        if new_text == text:
            break
        text = new_text

    # Remove specific noise characters (Soft hyphens, invisible separators, etc.)
    # \u00ad (Soft Hyphen), \u200b (Zero Width Space), \u200c (ZWUJ), \u200d (ZWJ), \u2007 (Figure Space), \u034f (CGJ)
    text = re.sub(r"[\u00ad\u200b\u200c\u200d\u2007\u034f]", "", text)

    # Clean up excessive whitespace created by stripping/decoding
    # Replace non-breaking spaces with normal spaces first
    text = text.replace("\xa0", " ")

    # Collapse multiple spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Fix multiple newlines (limit to 2 max)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

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
        status, message_ids = mail.search(None, f"SINCE {yesterday}")

        if status != "OK":
            print("Failed to search emails.")
            return []

        if not message_ids[0]:
            print("Found 0 messages.")
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

            def get_decoded_payload(message_part):
                """Helper to decode payload with correct charset."""
                payload = message_part.get_payload(decode=True)
                if not payload:
                    return ""
                charset = message_part.get_content_charset() or "utf-8"
                try:
                    return payload.decode(charset, errors="replace")
                except LookupError:
                    # Fallback for unknown encodings
                    return payload.decode("utf-8", errors="replace")

            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain" and not snippet:
                        snippet = get_decoded_payload(part)
                    elif content_type == "text/html" and not html_content:
                        html_content = get_decoded_payload(part)
            else:
                content_type = msg.get_content_type()
                if content_type == "text/html":
                    html_content = get_decoded_payload(msg)
                else:
                    snippet = get_decoded_payload(msg)

            # Extract links and images from HTML
            if html_content:
                links = parse_html_links(html_content)
                images = parse_html_images(html_content)
                snippet = convert_html_to_markdown(html_content)
            elif snippet:
                snippet = clean_text_content(snippet)

            if not snippet:
                snippet = "(No content)"

            print(f"DEBUG: Processing email '{subject[:30]}...' - Body len: {len(snippet)}")

            # Summarize content
            summary = summarize_content(snippet)
            if summary:
                snippet = summary

            emails.append(
                {
                    "subject": subject,
                    "from": sender,
                    "body_text": snippet,
                    "links": links,
                    "images": images,
                }
            )

        mail.logout()
        return emails

    except Exception as e:
        print(f"IMAP error: {e}")
        return []


def split_text_smartly(text, max_length=4000):
    """Split text into chunks, trying to break at newlines to preserve Markdown formatting."""
    chunks = []
    current_pos = 0
    text_len = len(text)

    while current_pos < text_len:
        # If remaining text fits, just add it
        if text_len - current_pos <= max_length:
            chunks.append(text[current_pos:])
            break

        # Get the candidate block
        candidate = text[current_pos : current_pos + max_length]

        # Look for the last newline to split safely
        split_at = -1
        last_newline = candidate.rfind("\n")

        # If we found a newline and it's not too close to the beginning (avoid tiny chunks)
        if last_newline > max_length * 0.2:
            split_at = last_newline + 1  # Include the newline in the current chunk

        # If no good newline, try space
        if split_at == -1:
            last_space = candidate.rfind(" ")
            if last_space > max_length * 0.2:
                split_at = last_space + 1

        # If still no good split point, force hard split
        if split_at == -1:
            split_at = max_length

        chunks.append(text[current_pos : current_pos + split_at])
        current_pos += split_at

    return chunks


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
        body_text = email_data.get("body_text", "") or "No content"
        subject = email_data.get("subject", "No Subject")[:256]
        sender = email_data.get("from", "Unknown")[:256]

        # Cleanup: Remove redundant Subject/Sender from the start of the body
        # Many newsletters repeat this info in the pre-header or top HTML
        lines = body_text.split("\n")
        skip_index = 0

        # Prepare checks
        checks = [subject.strip().lower(), sender.strip().lower()]
        noise_phrases = [
            "email from substack",
            "view in browser",
            "unsubscribe",
            "manage your subscription",
            "confirm subscription",  # Often repeated title
            "please confirm your subscription",
        ]

        # Check the first 10 non-empty lines
        checked_lines = 0
        for i, line in enumerate(lines):
            clean_line = line.strip().lower()
            if not clean_line:
                continue

            # Stop if we've checked too many lines
            if checked_lines >= 10:
                break

            is_noise = False
            # Check for Sender/Subject overlapping
            if any(c in clean_line or clean_line in c for c in checks if c) or any(
                phrase in clean_line for phrase in noise_phrases
            ):
                is_noise = True

            if is_noise:
                skip_index = i + 1
            else:
                # If we hit a substantial line that isn't noise, we stop stripping
                break
            checked_lines += 1

        if skip_index > 0:
            body_text = "\n".join(lines[skip_index:]).strip()

        # Chunk the body text smartly
        chunks = split_text_smartly(body_text, max_length=4000)

        if not chunks:
            chunks = ["(No content)"]

        for i, chunk in enumerate(chunks):
            description = chunk

            # If last chunk, append links
            if i == len(chunks) - 1 and email_data["links"]:
                description += "\n\n**🔗 Links:**\n"
                for text, url in email_data["links"]:
                    link_line = f"• [{text}]({url})\n"
                    # Prevent overflowing 4096
                    if len(description) + len(link_line) < 4090:
                        description += link_line

            # Embed Title logic
            if i == 0:
                title = subject
                author_field = {"name": sender}
            else:
                title = f"{subject} (Part {i + 1})"
                # Don't repeat author for subsequent parts to save space/cleanliness, or keep it?
                # Let's keep it empty to show it's a continuation
                author_field = {}

            embed = {
                "title": title,
                "description": description,
                "color": 0x4285F4,  # Google blue
            }

            if author_field:
                embed["author"] = author_field

            # Add image to first chunk only
            if i == 0 and email_data["images"]:
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
