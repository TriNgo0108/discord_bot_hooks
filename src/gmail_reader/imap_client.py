"""IMAP Client for fetching emails from Gmail."""

import datetime
import email
import imaplib
import logging
from typing import Any

from .config import CONFIG, GmailConfig
from .utils import (
    clean_text_content,
    convert_html_to_markdown,
    decode_mime_header,
    parse_html_images,
    parse_html_links,
)

logger = logging.getLogger(__name__)


class GmailClient:
    """Client for interacting with Gmail via IMAP."""

    def __init__(self, config: GmailConfig | None = None):
        self.config = config or CONFIG.gmail
        self.mail: imaplib.IMAP4_SSL | None = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def connect(self):
        """Connect to Gmail IMAP server."""
        if not self.config.validate():
            raise ValueError("Gmail configuration is invalid.")

        try:
            logger.info(f"Connecting to {self.config.imap_server}...")
            self.mail = imaplib.IMAP4_SSL(self.config.imap_server)
            self.mail.login(self.config.email_address, self.config.app_password)
            self.mail.select(self.config.email_folder)
            logger.info("Connected to Gmail.")
        except Exception as e:
            logger.error(f"Failed to connect to Gmail: {e}")
            raise

    def disconnect(self):
        """Logout and close connection."""
        if self.mail:
            try:
                self.mail.close()
                self.mail.logout()
                logger.info("Disconnected from Gmail.")
            except Exception as e:
                logger.warning(f"Error disconnecting: {e}")
            finally:
                self.mail = None

    def fetch_recent_emails(self, days: int = 1) -> list[dict[str, Any]]:
        """Fetch emails from the last N days."""
        if not self.mail:
            logger.warning("Not connected to Gmail.")
            return []

        try:
            since_date = (datetime.date.today() - datetime.timedelta(days=days)).strftime(
                "%d-%b-%Y"
            )
            # Searching might be slow, but usually fast enough for sync.
            # If this becomes a bottleneck, we can wrap in run_in_executor in main.
            status, message_ids = self.mail.search(None, f"SINCE {since_date}")

            if status != "OK" or not message_ids[0]:
                logger.info("No emails found.")
                return []

            email_ids = message_ids[0].split()
            logger.info(f"Found {len(email_ids)} emails.")

            emails = []
            for email_id in email_ids:
                data = self._fetch_single_email(email_id)
                if data:
                    emails.append(data)

            return emails

        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return []

    def _fetch_single_email(self, email_id: bytes) -> dict[str, Any] | None:
        """Fetch and process a single email by ID."""
        try:
            status, msg_data = self.mail.fetch(email_id, "(RFC822)")
            if status != "OK":
                return None

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject = decode_mime_header(msg.get("Subject"))
            sender = decode_mime_header(msg.get("From"))

            snippet, links, images = self._extract_content(msg)

            if not snippet:
                snippet = "(No content)"

            return {
                "id": email_id.decode(),
                "subject": subject,
                "from": sender,
                "body_text": snippet,
                "links": links,
                "images": images,
            }
        except Exception as e:
            logger.error(f"Error fetching email {email_id}: {e}")
            return None

    def _extract_content(self, msg) -> tuple[str, list, list]:
        """Extract body text, links, and images from email message."""
        snippet = ""
        html_content = ""
        links = []
        images = []

        def get_decoded_payload(part):
            payload = part.get_payload(decode=True)
            if not payload:
                return ""
            charset = part.get_content_charset() or "utf-8"
            try:
                return payload.decode(charset, errors="replace")
            except LookupError:
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

        if html_content:
            links = parse_html_links(html_content)
            images = parse_html_images(html_content)
            snippet = convert_html_to_markdown(html_content)
        elif snippet:
            snippet = clean_text_content(snippet)

        return snippet, links, images
