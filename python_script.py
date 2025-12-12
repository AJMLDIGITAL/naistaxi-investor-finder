import os
import requests
import json
import time
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
    data = {'query': query, 'variables': {'board_id': int(MONDAY_BOARD_ID)}}
    
    try:
        response = requests.post(API_URL, json=data, headers=headers)
        if "errors" in response.json():
            print("❌ API Error:", response.json()['errors'][0]['message'])
            return None, None

        columns = response.json()['data']['boards'][0]['columns']
        
        # Find the specific IDs we need
        type_col_id = "status" # default fallback
        loc_col_id = "text"    # default fallback
        
        for col in columns:
            title = col['title'].lower()
            if "type" in title:
                type_col_id = col['id']
                print(f"   ✅ Found 'Type' column: ID = {type_col_id} (Type: {col['type']})")
            elif "location" in title:
                loc_col_id = col['id']
                print(f"   ✅ Found 'Location' column: ID = {loc_col_id} (Type: {col['type']})")

        return type_col_id, loc_col_id

    except Exception as e:
        print(f"❌ Could not auto-detect columns: {e}")
        return "status", "text"

# --- 2. SEARCH & SCRAPE ---
SEARCH_QUERIES = [
    'top seed venture capital firms Europe 2025 list',
    'active angel investors SaaS USA 2025 contact',
    'venture capital funds investing in AI startups 2025'
]

BLACKLIST = ["reddit.com", "quora.com", "youtube.com", "g2.com"]

def search_investors():
    print("\n🔎 Searching for Investors...")
    results = []
    with DDGS() as ddgs:
        for q in SEARCH_QUERIES:
            try:
                # Get 3 results per query
                hits = [r for r in ddgs.text(q, max_results=3)]
                for hit in hits:
                    if not any(x in hit['href'] for x in BLACKLIST):
                        results.append(hit)
            except:
                pass
    return results

def get_investor_details(url, snippet):
    """
    Guesses the Investor Type and Location based on text keywords.
    """
    text = snippet.lower()
    
    # Guess Type
    inv_type = "VC Firm" # Default
    if "angel" in text: inv_type = "Angel Investor"
    elif "private equity" in text: inv_type = "Private Equity"
    elif "accelerator" in text: inv_type = "Accelerator"

    # Guess Location
    inv_loc = "Global" # Default
    locs = ["london", "san francisco", "new york", "berlin", "paris", "canada", "usa", "europe", "uk"]
    for l in locs:
        if l in text:
            inv_loc = l.title()
            break
            
    return inv_type, inv_loc

# --- 3. UPLOAD ---
def upload_item(title, url, inv_type, inv_loc, type_col_id, loc_col_id):
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
    
    # Prepare data for columns
    # We use "label" for status columns and simple strings for text columns
    vals = {
        type_col_id: {"label": inv_type}, 
        loc_col_id: inv_loc
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
            print(f"   📤 Uploaded: {title}")
        else:
            print(f"   ⚠️ Upload Error for {title}: {req.text}")
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
    print(f"   Found {len(items)} potential investors.")

    # 3. Process & Upload
    for item in items:
        title = item['title']
        url = item['href']
        snippet = item['body']
        
        # Smart Guessing
        i_type, i_loc = get_investor_details(url, snippet)
        
        # Upload
        upload_item(title, url, i_type, i_loc, type_id, loc_id)
        time.sleep(1)

if __name__ == "__main__":
    main()
