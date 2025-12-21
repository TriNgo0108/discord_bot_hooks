# Discord Bot Hooks

This project contains daily automation scripts that trigger via GitHub Actions and report to Discord.

## Features

1.  **Expense Report**: Summarizes daily expenses from a PostgreSQL database.
2.  **CGV Scraper**: Checks "Now Showing" and "Coming Soon" movies on CGV Vietnam.
3.  **Gmail Summary**: Fetches the last 10 Gmail messages.

## Setup

### Prerequisites

-   Python 3.9+
-   PostgreSQL Database
-   Google Cloud Project (for Gmail)
-   Discord Server (for Webhooks)

### Installation

1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Configuration (Local)

Create a `.env` file for local testing:

```ini
DB_URL=postgresql://user:password@host:port/dbname
DISCORD_WEBHOOK_EXPENSE=your_webhook_url
DISCORD_WEBHOOK_CGV=your_webhook_url
DISCORD_WEBHOOK_GMAIL=your_webhook_url
GMAIL_TOKEN=base64_encoded_token_json_optional
```

## Gmail Setup

To enable the Gmail reader, you need to generate a `token.json` file.

1.  Go to [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a project and enable the **Gmail API**.
3.  Go to **Credentials** -> **Create Credentials** -> **OAuth client ID** (Desktop App).
4.  Download the JSON file and rename it to `credentials.json` in the root of this project.
5.  Run the token generator:
    ```bash
    python generate_gmail_token.py
    ```
6.  Follow the browser prompt to authorize.
7.  A `token.json` file will be created.

**For GitHub Actions**:
-   Open `token.json`, copy the content.
-   Ideally, base64 encode it to avoid JSON parsing issues in secrets (though raw might work if quoted properly, base64 is safer).
-   Add it as a secret named `GMAIL_TOKEN`.

## GitHub Secrets

You must set the following secrets in your GitHub Repository settings:

| Secret Name               | Description                                      |
| ------------------------- | ------------------------------------------------ |
| `DB_URL`                  | PostgreSQL Connection URL                        |
| `DISCORD_WEBHOOK_EXPENSE` | Webhook for Expense Reports                      |
| `DISCORD_WEBHOOK_CGV`     | Webhook for CGV Updates                          |
| `DISCORD_WEBHOOK_GMAIL`   | Webhook for Gmail Summary                        |
| `GMAIL_TOKEN`             | Content of `token.json` (preferably base64)      |

