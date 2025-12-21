import os
import psycopg2
import requests
import datetime
from collections import defaultdict

# Only load .env for local development
if os.getenv('ENV') != 'production':
    from dotenv import load_dotenv
    load_dotenv()

DB_URL = os.getenv('DB_URL')
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_EXPENSE')

def get_db_connection():
    if not DB_URL:
        raise ValueError("DB_URL environment variable is not set")
    return psycopg2.connect(DB_URL)

def fetch_expense_data():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Query for daily expense summary
    # Assuming we want 'today' based on server time, or we can look back 24h.
    # Using CURRENT_DATE from Postgres matches 'today' in DB timezone.
    query = """
        SELECT SUM(amount) as total, category, sub_category
        FROM public.transaction_read_model
        WHERE transaction_date::date = CURRENT_DATE
        AND type = 'expense'
        GROUP BY category, sub_category
        ORDER BY category, sub_category;
    """
    
    cur.execute(query)
    rows = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return rows

def format_message(rows):
    if not rows:
        return "No expenses recorded for today so far. \u2705"

    total_expense = sum(row[0] for row in rows)
    
    # Organize data
    categories = defaultdict(lambda: {'total': 0, 'subs': []})
    
    for total, cat, sub in rows:
        categories[cat]['total'] += float(total)
        categories[cat]['subs'].append((sub, float(total)))
    
    # Build Message
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    message = f"**Daily Expense Report** \U0001F4C8 ({today_str})\n"
    message += f"**Total: ${total_expense:,.2f}**\n\n"
    
    for cat, data in categories.items():
        message += f"**{cat}**: ${data['total']:,.2f}\n"
        for sub, amount in data['subs']:
            message += f" - {sub}: ${amount:,.2f}\n"
        message += "\n"
        
    return message.strip()

def send_discord_webhook(message):
    if not DISCORD_WEBHOOK_URL:
        raise ValueError("DISCORD_WEBHOOK_EXPENSE environment variable is not set")
    
    data = {
        "content": message
    }
    
    response = requests.post(DISCORD_WEBHOOK_URL, json=data)
    response.raise_for_status()
    print(f"Sent message to Discord. Status: {response.status_code}")

def main():
    try:
        print("Fetching expense data...")
        rows = fetch_expense_data()
        print(f"Found {len(rows)} entries.")
        
        msg = format_message(rows)
        print("Formatted message:\n", msg)
        
        send_discord_webhook(msg)
        
    except Exception as e:
        print(f"Error: {e}")
        # Optionally send error to Discord too, but might loop if webhook is broken.
        raise e

if __name__ == "__main__":
    main()
