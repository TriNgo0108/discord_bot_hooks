"""Utility functions for Gmail Reader."""

import html
import re
from email.header import decode_header


def decode_mime_header(header_value: str | None) -> str:
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


def parse_html_links(html_content: str) -> list[tuple[str, str]]:
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
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "/track/click",
        "/track/open",
        "trk=",
        "mc_cid=",
        "mc_eid=",
        "redirect.",
        "/r/",
        "click.",
        "go.link",
        "links.e.",
        "elink.",
        "t.co/",
        "bit.ly/",
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
                domain_match = re.search(r"https?://(?:www\.)?([^/]+)", url)
                text = domain_match.group(1) if domain_match else "Link"

            # Filter out noise links (by text)
            if any(term in text.lower() for term in skip_terms):
                continue

            if len(text) > 50:
                text = text[:47] + "..."
            links.append((text, url))
    return links[:5]  # Limit to 5 links per email


def parse_html_images(html_content: str) -> list[str]:
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


def clean_text_content(text: str) -> str:
    """Clean up text by decoding entities and removing invisible characters."""
    if not text:
        return ""

    # Decode HTML entities (Robustly) - Loop to handle double encoding
    for _ in range(3):
        new_text = html.unescape(text)
        if new_text == text:
            break
        text = new_text

    # Remove specific noise characters
    text = re.sub(r"[\u00ad\u200b\u200c\u200d\u2007\u034f]", "", text)

    # Clean up excessive whitespace
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

    return text.strip()


def convert_html_to_markdown(html_content: str) -> str:
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
    def replace_link(match):
        url = match.group(1)
        content = match.group(2).strip()
        visible_text = re.sub(r"<[^>]+>", "", content).strip()
        if not visible_text:
            return ""
        return f"[{visible_text}]({url})"

    text = re.sub(
        r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', replace_link, text, flags=re.IGNORECASE
    )

    # Convert lists and blocks
    text = re.sub(r"<li>", "\n• ", text, flags=re.IGNORECASE)
    text = re.sub(r"</li>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<ul>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</ul>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</div>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</tr>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</h[1-6]>", "\n\n", text, flags=re.IGNORECASE)

    # Remove remaining tags
    text = re.sub(r"<[^>]+>", "", text)

    return clean_text_content(text)


def split_text_smartly(text: str, max_length: int = 4000) -> list[str]:
    """Split text into chunks, trying to break at newlines to preserve Markdown formatting."""
    chunks = []
    current_pos = 0
    text_len = len(text)

    while current_pos < text_len:
        if text_len - current_pos <= max_length:
            chunks.append(text[current_pos:])
            break

        candidate = text[current_pos : current_pos + max_length]

        # Priority: Newline > Space > Hard
        split_at = -1
        last_newline = candidate.rfind("\n")

        if last_newline > max_length * 0.2:
            split_at = last_newline + 1

        if split_at == -1:
            last_space = candidate.rfind(" ")
            if last_space > max_length * 0.2:
                split_at = last_space + 1

        if split_at == -1:
            split_at = max_length

        chunks.append(text[current_pos : current_pos + split_at])
        current_pos += split_at

    return chunks
