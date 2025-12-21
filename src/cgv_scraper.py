import os
import re
import requests
from bs4 import BeautifulSoup

# Only load .env for local development
if os.getenv('ENV') != 'production':
    from dotenv import load_dotenv
    load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_CGV')

URLS = {
    "Now Showing": "https://www.cgv.vn/default/movies/now-showing.html",
    "Coming Soon": "https://www.cgv.vn/default/movies/coming-soon-1.html"
}

def get_movies(url):
    # Some sites block python-requests, so we add a user-agent
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.exceptions.SSLError:
        # Fallback for SSL issues if needed, though rarely recommended
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        
    soup = BeautifulSoup(response.content, 'html.parser')
    
    movies = []
    
    # Try to find the movie grid
    # CGV structure usually: .products-grid > .item > .product-info
    items = soup.select('.products-grid .item')
    
    for item in items:
        title_el = item.select_one('.product-name a')
        if not title_el:
            continue
            
        title = title_el.get_text(strip=True)
        link = title_el['href']
        
        # Release date often in .movie-date or part of text info
        release_date = "N/A"
        date_el = item.select_one('.cgv-movie-date') # Hypothetical class, will try to find generic if fails
        
        # If specific class not found, try finding text with "Khởi chiếu" (Released)
        if not date_el:
             # Basic text search in the item
             text_content = item.get_text()
             if "Khởi chiếu:" in text_content:
                 # simple extraction attempt
                 match = re.search(r'Khởi chiếu:\s*([\d/]+)', text_content)
                 if match:
                     release_date = match.group(1)
        else:
            release_date = date_el.get_text(strip=True)

        movies.append({
            'title': title,
            'link': link,
            'release_date': release_date
        })
        
    return movies

def send_discord_message(section_name, movies):
    if not DISCORD_WEBHOOK_URL:
        print("DISCORD_WEBHOOK_CGV not set, skipping Discord send.")
        return

    if not movies:
        return

    # Discord has 2000 char limit. Split if necessary.
    # We'll just send a simplified lists.
    
    lines = [
        f"# 🎬 CGV Vietnam — {section_name}",
        "---",
        ""
    ]
    
    for m in movies:
        line = f"🎥 [{m['title']}]({m['link']})"
        if m['release_date'] != "N/A":
            line += f" — 📅 {m['release_date']}"
        lines.append(line)
    
    lines.append("")
    
    # Chunking
    chunks = []
    current_chunk = ""
    for line in lines:
        if len(current_chunk) + len(line) + 1 > 1900:
            chunks.append(current_chunk)
            current_chunk = line
        else:
            if current_chunk:
                current_chunk += "\n" + line
            else:
                current_chunk = line
    chunks.append(current_chunk)
    
    for chunk in chunks:
        requests.post(DISCORD_WEBHOOK_URL, json={'content': chunk})

def main():
    for name, url in URLS.items():
        print(f"Scraping {name}...")
        try:
            movies = get_movies(url)
            print(f"Found {len(movies)} movies.")
            send_discord_message(name, movies)
        except Exception as e:
            print(f"Error scraping {name}: {e}")

if __name__ == "__main__":
    main()
