import os
import requests
import json
import time
from ddgs import DDGS
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
MONDAY_API_KEY = os.environ.get("MONDAY_API_KEY", "").strip()
MONDAY_BOARD_ID = os.environ.get("MONDAY_BOARD_ID", "").strip()
API_URL = "https://api.monday.com/v2"

# --- SEARCH QUERIES ---
SEARCH_QUERIES = [
    'investors attending Slush 2025 looking for mobility startups',
    'venture capital firms investing in female founders Nordics 2025',
    'active angel investors Finland mobility startups list',
    'EIT Urban Mobility portfolio investors contact'
]

BLACKLIST = ["reddit.com", "quora.com", "youtube.com", "g2.com"]

def search_investors():
    print("\n🔎 Searching for Naistaxi Investors...")
    results = []
    with DDGS() as ddgs:
        for q in SEARCH_QUERIES:
            try:
                hits = [r for r in ddgs.text(q, max_results=4)]
                for hit in hits:
                    if not any(x in hit['href'] for x in BLACKLIST):
                        results.append(hit)
                time.sleep(1)
            except Exception as e:
                pass
    return results

def get_investor_details(snippet):
    text = snippet.lower()
    inv_type = "VC"
    if "angel" in text: inv_type = "Angel"
    elif "grant" in text: inv_type = "Grant"
    
    inv_loc = "Global"
    for loc in ["helsinki", "finland", "usa", "sweden", "london"]:
        if loc in text: 
            inv_loc = loc.title()
            break
            
    return inv_type, inv_loc

def scrape_content(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(resp.text, 'html.parser')
        paragraphs = soup.find_all('p')
        text = " ".join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50])
        return text[:600] if text else "No content found."
    except:
        return "Scrape failed."

def upload_item(title, url, inv_type, inv_loc, snippet):
    # --- THE FIX ---
    # We combine everything into the NAME so it cannot be hidden by column issues.
    combined_name = f"{title} | {inv_type} | {inv_loc}"
    
    print(f"   📤 Uploading: {combined_name}")
    
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
    
    # We deliberately send NO column data for Type/Location to avoid errors.
    # We only send the Link.
    vals = json.dumps({
        "link": {"url": url, "text": "Website"}
    })

    variables = {
        "board_id": int(MONDAY_BOARD_ID),
        "item_name": combined_name,
        "column_values": vals
    }
    
    headers = {"Authorization": MONDAY_API_KEY, "Content-Type": "application/json"}
    
    try:
        req = requests.post(API_URL, json={'query': query, 'variables': variables}, headers=headers)
        if "data" in req.json():
            # Create an Update (Bubble) with the snippet so you can read it
            item_id = req.json()['data']['create_item']['id']
            create_update(item_id, f"SOURCE: {url}\n\nCONTENT: {snippet}")
        else:
            print(f"   ⚠️ Error: {req.text}")
    except Exception as e:
        print(f"   ❌ Connection Error: {e}")

def create_update(item_id, text):
    query = """
    mutation ($item_id: ID!, $body: String!) {
      create_update (item_id: $item_id, body: $body) { id }
    }
    """
    requests.post(API_URL, json={'query': query, 'variables': {'item_id': item_id, 'body': text}}, headers={"Authorization": MONDAY_API_KEY})

def main():
    if not MONDAY_API_KEY or not MONDAY_BOARD_ID:
        print("❌ Error: Missing Secrets.")
        return

    items = search_investors()
    print(f"   Found {len(items)} investors.")

    for item in items:
        title = item['title']
        url = item['href']
        content = scrape_content(url)
        if len(content) < 50: continue
        
        i_type, i_loc = get_investor_details(content)
        
        # Upload using the new "Force Visible" method
        upload_item(title, url, i_type, i_loc, content)
        time.sleep(1)

if __name__ == "__main__":
    main()
