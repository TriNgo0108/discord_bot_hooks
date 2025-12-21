import os
import json
import base64
import httpx
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import datetime

# Only load .env for local development
if os.getenv('ENV') != 'production':
    from dotenv import load_dotenv
    load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_GMAIL')

from google.auth.transport.requests import Request

def get_credentials():
    """Load and refresh Gmail credentials from base64-encoded GMAIL_TOKEN env variable."""
    gmail_token_base64 = os.getenv('GMAIL_TOKEN')
    
    if not gmail_token_base64:
        return None
    
    token_json = base64.b64decode(gmail_token_base64).decode('utf-8')
    token_info = json.loads(token_json)
    credentials = Credentials.from_authorized_user_info(token_info)
    
    # Auto-refresh expired access tokens using refresh_token
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    
    return credentials

def fetch_recent_emails():
    """Fetch emails from the last 24 hours."""
    credentials = get_credentials()
    if not credentials:
        print("No valid credentials found (GMAIL_TOKEN not set).")
        return []

    try:
        gmail_service = build('gmail', 'v1', credentials=credentials)
        
        results = gmail_service.users().messages().list(
            userId='me', 
            q='newer_than:1d'
        ).execute()
        message_ids = results.get('messages', [])

        emails = []
        
        if not message_ids:
            print('No new messages.')
            return []

        print(f"Found {len(message_ids)} messages.")
        
        for message_ref in message_ids[:10]:  # Limit to 10 to avoid rate limits
            email_data = gmail_service.users().messages().get(
                userId='me', 
                id=message_ref['id']
            ).execute()
            
            headers = email_data['payload']['headers']
            subject = next(
                (h['value'] for h in headers if h['name'] == 'Subject'), 
                '(No Subject)'
            )
            sender = next(
                (h['value'] for h in headers if h['name'] == 'From'), 
                '(Unknown Sender)'
            )
            snippet = email_data.get('snippet', '')
            
            emails.append({
                'subject': subject,
                'from': sender,
                'snippet': snippet
            })
            
        return emails

    except HttpError as error:
        print(f'Gmail API error: {error}')
        return []

def send_discord_webhook(emails):
    """Send email summary to Discord webhook."""
    if not DISCORD_WEBHOOK_URL:
        print("DISCORD_WEBHOOK_GMAIL not set.")
        return

    today_date = datetime.date.today().strftime('%Y-%m-%d')
        
    if not emails:
        message = f"**Daily Gmail Summary** 📧 ({today_date})\n\nNo new emails in the last 24 hours. ✅"
        httpx.post(DISCORD_WEBHOOK_URL, json={'content': message})
        return

    message = f"**Daily Gmail Summary** 📧 ({today_date})\n\n"
    
    for email in emails:
        email_entry = f"**From:** {email['from']}\n**Sub:** {email['subject']}\n> {email['snippet']}\n\n"
        
        if len(message) + len(email_entry) > 1900:
            requests.post(DISCORD_WEBHOOK_URL, json={'content': message})
            message = email_entry
        else:
            message += email_entry
            
    if message:
        requests.post(DISCORD_WEBHOOK_URL, json={'content': message})

def main():
    """Main entry point for Gmail reader."""
    print("Fetching emails...")
    emails = fetch_recent_emails()
    print(f"Sending {len(emails)} emails to Discord...")
    send_discord_webhook(emails)

if __name__ == "__main__":
    main()
