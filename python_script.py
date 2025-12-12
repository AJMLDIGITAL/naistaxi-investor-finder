import os
import requests
import json
import time
from bs4 import BeautifulSoup
from ddgs import DDGS

# --- CONFIGURATION ---
MONDAY_API_KEY = os.environ["MONDAY_API_KEY"]
BOARD_ID = os.environ["BOARD_ID"]
API_URL = "https://api.monday.com/v2"

# --- SEARCH CONFIGURATION ---
# We use more specific terms to get better results
SEARCH_QUERIES = [
    '"monday.com" competitor features 2025',
    '"monday.com" vs "asana" vs "clickup" pricing',
    'project management software trends 2025'
]

# Domains to skip (often low quality or paywalled)
BLACKLIST_DOMAINS = ["reddit.com", "quora.com", "g2.com", "capterra.com", "youtube.com"]

def search_web(query):
    print(f"🔎 Searching for: '{query}'...")
    clean_results = []
    
    with DDGS() as ddgs:
        # Fetch more results initially (10) so we can filter down to the best 3
        results = [r for r in ddgs.text(query, max_results=10)]

    for res in results:
        link = res['href']
        # 1. Skip if link is in blacklist
        if any(bad_domain in link for bad_domain in BLACKLIST_DOMAINS):
            continue
            
        # 2. Skip PDF files
        if link.endswith(".pdf"):
            continue
            
        clean_results.append(res)
        if len(clean_results) >= 3: # Stop once we have 3 good links
            break
            
    return clean_results

def scrape_content(url):
    print(f"   ⬇️  Fetching: {url}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # IMPROVEMENT: Try to find the "main" article content specifically
        # This checks for common tag IDs used for main articles
        article = soup.find('article') or soup.find('main') or soup.find(id='content')
        
        if article:
            paragraphs = article.find_all('p')
        else:
            # Fallback to body if no main article tag found
            paragraphs = soup.find('body').find_all('p')
            
        # Get text, filter out very short sentences (often menu items)
        text_list = [p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50]
        full_text = " ".join(text_list)
        
        # Return a cleaner, longer snippet (800 chars)
        return full_text[:800] + "..." if full_text else "No substantial content found."

    except Exception as e:
        return f"Scrape Error: {e}"

def upload_to_monday(title, url, snippet):
    # Ensure special characters don't break JSON
    clean_snippet = snippet.replace('"', "'").replace('\n', ' ')
    
    query = """
    mutation ($board_id: ID!, $item_name: String!, $column_values: JSON!) {
      create_item (
        board_id: $board_id,
        item_name: $item_name,
        column_values: $column_values
      ) {
        id
      }
    }
    """
    
    # ADJUST THIS: Ensure "text" matches your actual Monday column ID for text/link
    column_vals = json.dumps({
        "text": f"{url} --- {clean_snippet}"
    })

    variables = {
        "board_id": int(BOARD_ID),
        "item_name": title,
        "column_values": column_vals
    }

    headers = {"Authorization": MONDAY_API_KEY, "Content-Type": "application/json"}
    
    try:
        requests.post(API_URL, json={'query': query, 'variables': variables}, headers=headers)
        print(f"   ✅ Sent to Monday: {title}")
    except Exception as e:
        print(f"   ❌ Monday Error: {e}")

def main():
    print("--- STARTING DAILY SEARCH ---")
    
    for query in SEARCH_QUERIES:
        good_links = search_web(query)
        
        for item in good_links:
            title = item['title']
            url = item['href']
            
            # Scrape
            content = scrape_content(url)
            
            # Skip if content is empty or failed
            if "Scrape Error" in content or len(content) < 50:
                print(f"   ⚠️ Skipping {title} (Low quality content)")
                continue

            # Upload
            upload_to_monday(title, url, content)
            
            # Wait to avoid blocking
            time.sleep(2)

if __name__ == "__main__":
    main()
