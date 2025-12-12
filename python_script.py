import os
import requests
import json
import time
from bs4 import BeautifulSoup
from ddgs import DDGS

# --- CONFIGURATION & VALIDATION ---
# NOW LOOKING FOR "MONDAY_BOARD_ID"
MONDAY_API_KEY = os.environ.get("MONDAY_API_KEY", "").strip()
BOARD_ID = os.environ.get("MONDAY_BOARD_ID", "").strip() 

# 1. Validate Credentials
if not MONDAY_API_KEY:
    print("❌ Error: MONDAY_API_KEY is missing.")
    exit(1)

if not BOARD_ID:
    print("❌ Error: MONDAY_BOARD_ID is missing.")
    exit(1)

if not BOARD_ID.isdigit():
    print(f"❌ Error: MONDAY_BOARD_ID must be a number. You provided: '{BOARD_ID}'")
    exit(1)

API_URL = "https://api.monday.com/v2"

# --- SEARCH CONFIGURATION ---
SEARCH_QUERIES = [
    '"monday.com" competitor features 2025',
    'project management software trends 2025'
]

BLACKLIST_DOMAINS = ["reddit.com", "quora.com", "g2.com", "capterra.com", "youtube.com"]

def search_web(query):
    print(f"🔎 Searching for: '{query}'...")
    clean_results = []
    
    with DDGS() as ddgs:
        try:
            results = [r for r in ddgs.text(query, max_results=5)]
        except Exception as e:
            print(f"   ⚠️ Search Error: {e}")
            return []

    for res in results:
        link = res.get('href', '')
        if any(bad in link for bad in BLACKLIST_DOMAINS):
            continue
        clean_results.append(res)
        if len(clean_results) >= 2: 
            break
            
    return clean_results

def scrape_content(url):
    print(f"   ⬇️  Fetching: {url}")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/115.0.0.0 Safari/537.36"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        paragraphs = soup.find_all('p')
        text_list = [p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50]
        full_text = " ".join(text_list)
        
        return full_text[:800] + "..." if full_text else "No substantial content found."

    except Exception as e:
        return f"Scrape Error: {e}"

def upload_to_monday(title, url, snippet):
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
        r = requests.post(API_URL, json={'query': query, 'variables': variables}, headers=headers)
        if r.status_code == 200 and "errors" not in r.json():
            print(f"   ✅ Sent to Monday: {title}")
        else:
            print(f"   ❌ Monday API Error: {r.text}")
    except Exception as e:
        print(f"   ❌ Connection Error: {e}")

def main():
    print("--- STARTING DAILY SEARCH ---")
    for query in SEARCH_QUERIES:
        good_links = search_web(query)
        for item in good_links:
            title = item.get('title', 'No Title')
            url = item.get('href', '')
            content = scrape_content(url)
            
            if "Scrape Error" in content or len(content) < 50:
                print(f"   ⚠️ Skipping {title} (Low quality)")
                continue

            upload_to_monday(title, url, content)
            time.sleep(2)

if __name__ == "__main__":
    main()
