import os
import imaplib
import email
from email.header import decode_header
import httpx
import datetime

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

        # Search for emails from the last 24 hours
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime(
            "%d-%b-%Y"
        )
        status, message_ids = mail.search(None, f"(SINCE {yesterday})")

        if status != "OK":
            print("Failed to search emails.")
            return []

        email_ids = message_ids[0].split()
        print(f"Found {len(email_ids)} messages.")

        emails = []

        # Limit to 10 most recent emails
        for email_id in email_ids[-10:]:
            status, msg_data = mail.fetch(email_id, "(RFC822)")

            if status != "OK":
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject = decode_mime_header(msg["Subject"])
            sender = decode_mime_header(msg["From"])

            # Get snippet from body
            snippet = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True)
                        if body:
                            snippet = body.decode("utf-8", errors="ignore")[:150]
                        break
            else:
                body = msg.get_payload(decode=True)
                if body:
                    snippet = body.decode("utf-8", errors="ignore")[:150]

            emails.append(
                {
                    "subject": subject,
                    "from": sender,
                    "snippet": snippet.replace("\n", " ").replace("\r", ""),
                }
            )

        mail.logout()
        return emails

    except Exception as e:
        print(f"IMAP error: {e}")
        return []


def send_discord_webhook(emails):
    """Send email summary to Discord webhook."""
    if not DISCORD_WEBHOOK_URL:
        print("DISCORD_WEBHOOK_GMAIL not set.")
        return

    today_date = datetime.date.today().strftime("%Y-%m-%d")

    if not emails:
        message = f"**Daily Gmail Summary** 📧 ({today_date})\n\nNo new emails in the last 24 hours. ✅"
        httpx.post(DISCORD_WEBHOOK_URL, json={"content": message})
        return

    message = f"**Daily Gmail Summary** 📧 ({today_date})\n\n"

    for email_data in emails:
        email_entry = f"**From:** {email_data['from']}\n**Sub:** {email_data['subject']}\n> {email_data['snippet']}\n\n"

        if len(message) + len(email_entry) > 1900:
            httpx.post(DISCORD_WEBHOOK_URL, json={"content": message})
            message = email_entry
        else:
            message += email_entry

    if message:
        httpx.post(DISCORD_WEBHOOK_URL, json={"content": message})


def main():
    """Main entry point for Gmail reader."""
    print("Fetching emails via IMAP...")
    emails = fetch_recent_emails()
    print(f"Sending {len(emails)} emails to Discord...")
    send_discord_webhook(emails)


if __name__ == "__main__":
    main()
