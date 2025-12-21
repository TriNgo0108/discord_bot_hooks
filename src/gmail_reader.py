import os
import json
import base64
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import datetime

# Only load .env for local development
if os.getenv('ENV') != 'production':
    from dotenv import load_dotenv
    load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_GMAIL')

def get_credentials():
    """Load credentials from base64-encoded GMAIL_TOKEN environment variable."""
    env_token = os.getenv('GMAIL_TOKEN')
    
    if not env_token:
        return None
    
    token_json = base64.b64decode(env_token).decode('utf-8')
    info = json.loads(token_json)
    return Credentials.from_authorized_user_info(info)

def get_emails():
    creds = get_credentials()
    if not creds:
        print("No valid credentials found (GMAIL_TOKEN or token.json).")
        return []

    try:
        service = build('gmail', 'v1', credentials=creds)

        # Get messages from the last day, or just input for now -> query "newer_than:1d"
        # The user said "read my read gmail" -> maybe just "in:inbox" ?
        # I'll stick to 'newer_than:1d' to avoid spamming old stuff daily.
        results = service.users().messages().list(userId='me', q='newer_than:1d').execute()
        messages = results.get('messages', [])

        email_data = []
        
        if not messages:
            print('No new messages.')
            return []

        print(f"Found {len(messages)} messages.")
        for message in messages[:10]: # Limit to 10 to avoid hitting limits
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            
            headers = msg['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No Subject)')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '(Unknown Sender)')
            snippet = msg.get('snippet', '')
            
            email_data.append({
                'subject': subject,
                'from': sender,
                'snippet': snippet
            })
            
        return email_data

    except HttpError as error:
        print(f'An error occurred: {error}')
        return []

def send_discord_webhook(emails):
    if not DISCORD_WEBHOOK_URL:
        print("DISCORD_WEBHOOK_GMAIL not set.")
        return

    today_str = datetime.date.today().strftime('%Y-%m-%d')
        
    if not emails:
        message = (
            f"# 📧 Daily Gmail Summary\n"
            f"📅 **Date:** {today_str}\n\n"
            f"✅ No new emails in the last 24 hours."
        )
        requests.post(DISCORD_WEBHOOK_URL, json={'content': message})
        return

    header = (
        f"# 📧 Daily Gmail Summary\n"
        f"📅 **Date:** {today_str}\n"
        f"📬 **New emails:** {len(emails)}\n\n"
        f"---\n\n"
    )
    
    message = header
    
    for i, email in enumerate(emails, 1):
        entry = (
            f"**{i}. {email['subject']}**\n"
            f"👤 {email['from']}\n"
            f"> {email['snippet']}\n\n"
        )
        
        if len(message) + len(entry) > 1900:
            requests.post(DISCORD_WEBHOOK_URL, json={'content': message})
            message = entry
        else:
            message += entry
            
    if message:
        requests.post(DISCORD_WEBHOOK_URL, json={'content': message})

def main():
    print("Fetching emails...")
    emails = get_emails()
    print(f"Sending {len(emails)} emails to Discord...")
    send_discord_webhook(emails)

if __name__ == "__main__":
    main()
