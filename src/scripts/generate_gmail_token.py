import base64
import os.path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CREDENTIALS_FILE = "../credentials.json"


def main():
    """Generate Gmail OAuth token and output as base64 for GitHub Secrets."""
    if not os.path.exists(CREDENTIALS_FILE):
        print("Error: credentials.json not found. Please download it from Google Cloud Console.")
        return

    auth_flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    credentials = auth_flow.run_local_server(port=0)

    token_json = credentials.to_json()
    token_base64 = base64.b64encode(token_json.encode("utf-8")).decode("utf-8")

    print("\n" + "=" * 60)
    print("Base64-encoded token for GMAIL_TOKEN secret:")
    print("=" * 60)
    print(token_base64)
    print("=" * 60)


if __name__ == "__main__":
    main()
