import os
import requests
import json
import time
import re
from bs4 import BeautifulSoup
from ddgs import DDGS

# --- CONFIGURATION ---
MONDAY_API_KEY = os.environ.get("MONDAY_API_KEY", "").strip()
MONDAY_BOARD_ID = os.environ.get("MONDAY_BOARD_ID", "").strip()
API_URL = "https://api.monday.com/v2"

# --- 1. AUTO-DETECT COLUMN IDs ---
def get_column_ids():
    """
    Asks Monday.com for the secret codes (IDs) of your 'Type' and 'Location' columns.
    """
    print(f"🕵️  Inspecting Board {MONDAY_BOARD_ID} to find column codes...")
    
    query = """
    query ($board_id: [ID!]) {
      boards (ids: $board_id) {
        columns {
          id
          title
          type
        }
      }
    }
    """
    
    headers = {"Authorization": MONDAY_API_KEY, "Content-Type": "application/json"}
    
    # Safety check for Board ID
    if not MONDAY_BOARD_ID.isdigit():
        print(f"❌ Error: Board ID '{MONDAY_BOARD_ID}' is not a number. Check GitHub Secrets.")
        return None, None

    data = {'query': query, 'variables': {'board_id': int(MONDAY_BOARD_ID)}}
    
    try:
        response = requests.post(API_URL, json=data, headers=headers)
        if "errors" in response.json():
            print("❌ API Error:", response.json()['errors'][0]['message'])
            return None, None

        columns = response.json()['data']['boards'][0]['columns']
        
        # Default fallbacks
        type_col_id = "status" 
        loc_col_id = "text"   
        
        for col in columns:
            title = col['title'].lower()
            if "type" in title:
                type_col_id = col['id']
                print(f"   ✅ Found 'Type' column: ID = {type_col_id}")
            elif "location" in title:
                loc_col_id = col['id']
                print(f"   ✅ Found 'Location' column: ID = {loc_col_id}")

        return type_col_id, loc_col_id

    except Exception as e:
        print(f"❌ Could not auto-detect columns: {e}")
        return "status", "text"

# --- 2. NAISTAXI INVESTOR SEARCH ---
# These queries are specifically tuned for your niche: Mobility + Female Founders + Nordics
SEARCH_QUERIES = [
    'investors attending Slush 2025 looking for mobility startups',
    'venture capital firms investing in female founders Nordics 2025',
    'active angel investors Finland mobility startups list',
    'EIT Urban Mobility portfolio investors contact',
    'BackingMinds portfolio Nordics investors'
]

BLACKLIST = ["reddit.com", "quora.com", "youtube.com", "g2.com", "facebook.com"]

def search_investors():
    print("\n🔎 Searching for Naistaxi Investors...")
    results = []
    with DDGS() as ddgs:
        for q in SEARCH_QUERIES:
            try:
                # Fetch more results to filter down to the best ones
                hits = [r for r in ddgs.text(q, max_results=5)]
                for hit in hits:
                    if not any(x in hit['href'] for x in BLACKLIST):
                        results.append(hit)
                time.sleep(1) # Be polite to DuckDuckGo
            except Exception as e:
                print(f"   ⚠️ Search Warning: {e}")
                pass
    return results

def get_investor_details(url, snippet):
    """
    Analyzes text to guess Investor Type and Location.
    Also looks for 'Female Founder' focus which is key for Naistaxi.
    """
    text = snippet.lower()
    
    # Guess Type
    inv_type = "VC Firm" # Default
    if "angel" in text: inv_type = "Angel Investor"
    elif "private equity" in text: inv_type = "Private Equity"
    elif "accelerator" in text: inv_type = "Accelerator"
    elif "grant" in text or "funding agency" in text: inv_type = "Grant/Public"

    # Guess Location
    inv_loc = "Global" # Default
    locs = ["helsinki", "finland", "london", "stockholm", "sweden", "berlin", "germany", "usa", "san francisco"]
    for l in locs:
        if l in text:
            inv_loc = l.title()
            break
    
    # Bonus: Add a flag if they focus on female founders
    if "female" in text or "women" in text or "diversity" in text:
        inv_type += " (Female Focus)"

    return inv_type, inv_loc

def scrape_content(url):
    """
    Fetches the website to get a better snippet for the Monday board.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Extract paragraph text
        paragraphs = soup.find_all('p')
        text = " ".join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50])
        
        return text[:800] + "..." if text else "No content found."
    except:
        return "Scrape failed."

# --- 3. UPLOAD TO MONDAY ---
def upload_item(title, url, inv_type, inv_loc, snippet, type_col_id, loc_col_id):
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
    
    # Clean up snippet for JSON
    clean_snippet = snippet.replace('"', "'").replace('\n', ' ')
    
    # Construct Column Data
    vals = {
        type_col_id: {"label": inv_type.split(" (")[0]}, # Try to match exact Status label
        loc_col_id: inv_loc,
        # Try to put the summary/snippet in a 'long_text' column if it exists, 
        # otherwise append it to the location or leave it. 
        # For now, we will assume you might check the link.
    }
    
    variables = {
        "board_id": int(MONDAY_BOARD_ID),
        "item_name": title,
        "column_values": json.dumps(vals)
    }
    
    headers = {"Authorization": MONDAY_API_KEY, "Content-Type": "application/json"}
    
    try:
        req = requests.post(API_URL, json={'query': query, 'variables': variables}, headers=headers)
        if "data" in req.json():
            print(f"   📤 Uploaded: {title} [{inv_type}]")
        else:
            print(f"   ⚠️ Monday Error: {req.json().get('errors', [{}])[0].get('message')}")
    except Exception as e:
        print(f"   ❌ Connection Error: {e}")

# --- MAIN ---
def main():
    if not MONDAY_API_KEY or not MONDAY_BOARD_ID:
        print("❌ Error: Missing MONDAY_API_KEY or MONDAY_BOARD_ID in Secrets.")
        return

    # 1. Auto-detect Columns
    type_id, loc_id = get_column_ids()
    
    if not type_id:
        print("❌ Critical: Could not access board. Check your API Key.")
        return

    # 2. Search
    items = search_investors()
    print(f"   Found {len(items)} potential investors. Processing...")

    # 3. Process & Upload
    count = 0
    for item in items:
        if count >= 5: break # Limit to 5 per run to be safe
        
        title = item['title']
        url = item['href']
        
        # Scrape deeper to get better location/type data
        content = scrape_content(url)
        if len(content) < 50: continue
        
        # Smart Guessing
        i_type, i_loc = get_investor_details(url, content)
        
        # Upload
        upload_item(title, url, i_type, i_loc, content, type_id, loc_id)
        time.sleep(2)
        count += 1

if __name__ == "__main__":
    main()
