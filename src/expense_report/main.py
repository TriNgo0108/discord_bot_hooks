import os
import psycopg2
import httpx
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

def fetch_daily_expenses():
    """Fetch today's expenses grouped by category and subcategory."""
    connection = get_db_connection()
    cursor = connection.cursor()
    
    query = """
        SELECT SUM(amount) as total, category, sub_category
        FROM public.transaction_read_model
        WHERE transaction_date::date = CURRENT_DATE
        AND type = 'expense'
        GROUP BY category, sub_category
        ORDER BY category, sub_category;
    """
    
    cursor.execute(query)
    expense_rows = cursor.fetchall()
    
    cursor.close()
    connection.close()
    
    return expense_rows

def format_expense_message(expense_rows):
    """Format expense data into a Discord-friendly message."""
    if not expense_rows:
        return "No expenses recorded for today so far. ✅"

    total_expense = sum(row[0] for row in expense_rows)
    
    # Organize expenses by category
    categories = defaultdict(lambda: {'total': 0, 'subcategories': []})
    
    for amount, category_name, subcategory_name in expense_rows:
        categories[category_name]['total'] += float(amount)
        categories[category_name]['subcategories'].append((subcategory_name, float(amount)))
    
    # Build message
    today_date = datetime.date.today().strftime('%Y-%m-%d')
    message = f"**Daily Expense Report** 📈 ({today_date})\n"
    message += f"**Total: ${total_expense:,.2f}**\n\n"
    
    for category_name, category_data in categories.items():
        message += f"**{category_name}**: ${category_data['total']:,.2f}\n"
        for subcategory_name, amount in category_data['subcategories']:
            message += f" - {subcategory_name}: ${amount:,.2f}\n"
        message += "\n"
        
    return message.strip()

def send_discord_webhook(message):
    if not DISCORD_WEBHOOK_URL:
        raise ValueError("DISCORD_WEBHOOK_EXPENSE environment variable is not set")
    
    data = {
        "content": message
    }
    
    response = httpx.post(DISCORD_WEBHOOK_URL, json=data)
    response.raise_for_status()
    print(f"Sent message to Discord. Status: {response.status_code}")

def main():
    try:
        print("Fetching expense data...")
        expense_rows = fetch_daily_expenses()
        print(f"Found {len(expense_rows)} entries.")
        
        formatted_message = format_expense_message(expense_rows)
        print("Formatted message:\n", formatted_message)
        
        send_discord_webhook(formatted_message)
        
    except Exception as e:
        print(f"Error: {e}")
        # Optionally send error to Discord too, but might loop if webhook is broken.
        raise e

if __name__ == "__main__":
    main()
