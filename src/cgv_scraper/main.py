import os
import re
import httpx
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
        response = httpx.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except httpx.HTTPStatusError:
        response = httpx.get(url, headers=headers, verify=False, timeout=10)
        
    soup = BeautifulSoup(response.content, 'html.parser')
    
    movies = []
    
    # Try to find the movie grid
    # CGV structure usually: .products-grid > .item > .product-info
    items = soup.select('.products-grid .item')
    
    for item in items:
        title_element = item.select_one('.product-name a')
        if not title_element:
            continue
            
        title = title_element.get_text(strip=True)
        link = title_element['href']
        
        # Release date often in .movie-date or part of text info
        release_date = "N/A"
        date_element = item.select_one('.cgv-movie-date')
        
        # If specific class not found, try finding text with "Khởi chiếu" (Released)
        if not date_element:
            item_text = item.get_text()
            if "Khởi chiếu:" in item_text:
                date_match = re.search(r'Khởi chiếu:\s*([\d/]+)', item_text)
                if date_match:
                    release_date = date_match.group(1)
        else:
            release_date = date_element.get_text(strip=True)

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
    
    lines = [f"**{section_name}** 🎬"]
    
    for movie in movies:
        movie_line = f"- [{movie['title']}]({movie['link']})"
        if movie['release_date'] != "N/A":
            movie_line += f" (Start: {movie['release_date']})"
        lines.append(movie_line)
        
    message = "\n".join(lines)
    
    # Split message into chunks (Discord has 2000 char limit)
    message_chunks = []
    current_message = ""
    
    for line in lines:
        if len(current_message) + len(line) + 1 > 1900:
            message_chunks.append(current_message)
            current_message = line
        else:
            current_message = current_message + "\n" + line if current_message else line
    
    message_chunks.append(current_message)
    
    for message_chunk in message_chunks:
        httpx.post(DISCORD_WEBHOOK_URL, json={'content': message_chunk})

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
