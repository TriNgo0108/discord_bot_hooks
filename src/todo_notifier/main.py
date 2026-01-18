import datetime
import os
from collections import defaultdict

import httpx
import psycopg2

# Only load .env for local development
if os.getenv("ENV") != "production":
    from dotenv import load_dotenv

    load_dotenv()

DB_URL = os.getenv("DB_URL")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_TODO")


def get_db_connection():
    if not DB_URL:
        raise ValueError("DB_URL environment variable is not set")
    return psycopg2.connect(DB_URL)


def fetch_incomplete_todos():
    """Fetch all incomplete todos."""
    connection = get_db_connection()
    cursor = connection.cursor()

    # Query todo_read_model for incomplete items
    query = """
        SELECT id, content, priority, created_at
        FROM public.todo_read_model
        WHERE completed = false
        ORDER BY 
            CASE priority
                WHEN 'High' THEN 1
                WHEN 'Medium' THEN 2
                WHEN 'Low' THEN 3
                ELSE 4
            END,
            created_at DESC;
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    cursor.close()
    connection.close()
    return rows


def format_todo_message(rows):
    """Format todos into a Discord message."""
    if not rows:
        return "You're all caught up! No incomplete todos. 🎉"

    total_count = len(rows)
    todos_by_priority = defaultdict(list)

    for todo_id, content, priority, _ in rows:
        todos_by_priority[priority].append((todo_id, content))

    today_date = datetime.date.today().strftime("%Y-%m-%d")
    message = f"**Pending Todos** 📝 ({today_date})\n"
    message += f"**Total Outstanding: {total_count}**\n\n"

    # Priority Order
    priorities = ["High", "Medium", "Low"]

    for priority in priorities:
        if priority in todos_by_priority:
            message += f"**{priority} Priority**\n"
            for todo_id, content in todos_by_priority[priority]:
                message += f"☐ `[{todo_id}]` {content}\n"
            message += "\n"

    # Handle any other priorities if they exist
    for priority, todo_list in todos_by_priority.items():
        if priority not in priorities:
            message += f"**{priority} Priority**\n"
            for todo_id, content in todo_list:
                message += f"☐ `[{todo_id}]` {content}\n"
            message += "\n"

    return message.strip()


def send_discord_webhook(message):
    if not DISCORD_WEBHOOK_URL:
        print("DISCORD_WEBHOOK_TODO environment variable is not set. Printing to console instead.")
        print(message)
        return

    # Check length limits for Discord (2000 chars)
    if len(message) > 2000:
        # Simple splitting strategy if too long
        parts = []
        while len(message) > 2000:
            split_at = message.rfind("\n", 0, 2000)
            if split_at == -1:
                split_at = 2000
            parts.append(message[:split_at])
            message = message[split_at:]
        parts.append(message)

        for part in parts:
            httpx.post(DISCORD_WEBHOOK_URL, json={"content": part})
    else:
        httpx.post(DISCORD_WEBHOOK_URL, json={"content": message})


def main():
    try:
        print("Fetching incomplete todos...")
        todos = fetch_incomplete_todos()
        print(f"Found {len(todos)} incomplete todos.")

        message = format_todo_message(todos)
        send_discord_webhook(message)
        print("Notification sent successfully.")

    except Exception as e:
        print(f"Error: {e}")
        # Only raise if we want to fail the workflow
        raise e


if __name__ == "__main__":
    main()
