import os.path
import base64
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def main():
    creds = None
    
    if not os.path.exists('../credentials.json'):
        print("Error: credentials.json not found. Please download it from Google Cloud Console.")
        return
    flow = InstalledAppFlow.from_client_secrets_file(
            '../credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
        
    token_json = creds.to_json()
    
    token_base64 = base64.b64encode(token_json.encode('utf-8')).decode('utf-8')
    print("\n" + "="*60)
    print("Base64-encoded token for GMAIL_TOKEN secret:")
    print("="*60)
    print(token_base64)
    print("="*60)

if __name__ == '__main__':
    main()
