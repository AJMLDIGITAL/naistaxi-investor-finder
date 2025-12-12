"""
Naistaixi High-Precision Investor Hunter
Optimized for ACCURACY: Filters out agencies, crypto, and real estate.
"""

import requests
import json
import os
import time
import csv
from datetime import datetime

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        print("❌ Critical Error: Could not import duckduckgo_search or ddgs.")
        exit(1)

# --- CONFIGURATION ---
# More specific queries to find FIRMS, not blog posts
TARGET_SOURCES = [
    {"name": "Signal NFX",      "query": 'site:signal.nfx.com "SaaS" "Pre-Seed" "United States"'},
    {"name": "OpenVC Directory","query": 'site:openvc.app "SaaS" "United States" "Standard"'},
    {"name": "TechCrunch Lists","query": '"active pre-seed investors" SaaS "contact" 2024 2025'},
    {"name": "VC Portfolio",    "query": 'San Francisco pre-seed VC "our portfolio" SaaS B2B'}
]

MAX_RESULTS_PER_SOURCE = 10 
MIN_SCORE_TO_KEEP = 50  # <--- Raised to 50 for better quality

MONDAY_COLUMN_IDS = {
    "status_id": "color_mkyj5j54",
    "type_id": "color_mkyjzz25",
    "website_id": "link_mkyj3m1e",
    "linkedin_id": "link_mkyjpc2z",
    "score_id": "numeric_mkyjx5h6",
    "location_id": "text_mkyjfhyc",
    "notes_id": "long_text_mkyjra9c",
    "source_id": "text_mkyjcxqn",
    "email_id": "email_mkyjbej4"
}

MONDAY_API_KEY = os.environ.get('MONDAY_API_KEY')
MONDAY_BOARD_ID = os.environ.get('MONDAY_BOARD_ID')

def calculate_smart_score(text):
    """Gives points for SaaS/VC terms and PENALTIES for junk"""
    score = 50 
    text = text.lower()
    
    # --- POSITIVE SIGNALS (Things we want) ---
    if "saas" in text: score += 15
    if "b2b" in text: score += 10
    if "portfolio" in text: score += 15     # Good sign it's a firm
    if "ticket size" in text: score += 15   # Very good sign
    if "partners" in text: score += 10
    
    # --- NEGATIVE SIGNALS (Things to remove) ---
    if "consulting" in text: score -= 30    # Remove consultants
    if "agency" in text: score -= 30        # Remove agencies
    if "hiring" in text: score -= 10        # Remove job ads
    if "real estate" in text: score -= 40   # Wrong industry
    if "crypto" in text: score -= 20        # Wrong industry
    if "course" in text: score -= 30        # Remove "How to pitch" courses
    
    return min(score, 100)

def get_real_investors():
    all_results = []
    print(f"🚀 Starting High-Precision Search (Min Score: {MIN_SCORE_TO_KEEP})...")
    
    with DDGS() as ddgs:
        for source in TARGET_SOURCES:
            print(f"🔎 Searching: {source['name']}...")
            try:
                search_results = list(ddgs.text(source['query'], max_results=MAX_RESULTS_PER_SOURCE))
                
                print(f"   👉 Raw results: {len(search_results)}")
                
                for result in search_results:
                    title = result.get('title', 'Unknown')
                    link = result.get('href', '')
                    body = result.get('body', '')
                    
                    smart_score = calculate_smart_score(body + " " + title)
                    
                    if smart_score < MIN_SCORE_TO_KEEP:
                        continue 

                    name = title.split("-")[0].split("|")[0].strip()
                    if len(name) > 40: name = name[:40] + "..."
                    
                    investor = {
                        "name": name,
                        "website": link,
                        "score": smart_score, 
                        "location": "US",
                        "type": "VC",
                        "source": source['name'],
                        "notes": f"Score: {smart_score}. Snippet: {body}",
                        "email": "" 
                    }
                    all_results.append(investor)
                    
                time.sleep(2) 
                
            except Exception as e:
                print(f"⚠️ Error searching {source['name']}: {e}")
                
    return all_results

def push_to_monday(investor):
    url = "https://api.monday.com/v2"
    headers = {"Authorization": MONDAY_API_KEY, "Content-Type": "application/json"}
    
    column_values = {
        MONDAY_COLUMN_IDS["status_id"]: {"label": "New Lead"},
        MONDAY_COLUMN_IDS["type_id"]: {"label": "VC"},
        MONDAY_COLUMN_IDS["website_id"]: {"url": investor["website"], "text": "Link"},
        MONDAY_COLUMN_IDS["score_id"]: investor["score"],
        MONDAY_COLUMN_IDS["source_id"]: investor["source"],
        MONDAY_COLUMN_IDS["notes_id"]: investor["notes"]
    }
    
    query = '''
    mutation ($boardId: ID!, $itemName: String!, $columnValues: JSON!) {
      create_item(board_id: $boardId, item_name: $itemName, column_values: $columnValues) {
        id
      }
    }
    '''
    
    variables = {
        "boardId": MONDAY_BOARD_ID, 
        "itemName": investor["name"], 
        "columnValues": json.dumps(column_values)
    }
    
    try:
        response = requests.post(url, headers=headers, json={"query": query, "variables": variables})
        if response.status_code == 200 and "data" in response.json():
            print(f"✅ Pushed: {investor['name']}")
        else:
            print(f"❌ Failed to Push: {investor['name']} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

def save_to_csv(investors):
    if not investors: return
    filename = f"investors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    try:
        keys = investors[0].keys()
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(investors)
        print(f"💾 CSV Backup saved: {filename}")
    except Exception as e:
        print(f"❌ CSV Error: {e}")

if __name__ == "__main__":
    investors = get_real_investors()
    print(f"\n📊 QUALIFIED LEADS FOUND: {len(investors)}")
    
    if len(investors) > 0:
        save_to_csv(investors)
        for inv in investors:
            push_to_monday(inv)
    else:
        print("❌ 0 leads found. This might mean we were too strict or got blocked. Try running again later.")
