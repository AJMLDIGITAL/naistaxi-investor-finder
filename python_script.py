"""
Naistaixi Robust Investor Hunter
Debug Mode: Lower thresholds and better error reporting.
"""

import requests
import json
import os
import time
import csv
from datetime import datetime

# Try importing the search tool (handling both old and new names)
try:
    from duckduckgo_search import DDGS
except ImportError:
    try:
        from ddgs import DDGS
    except ImportError:
        print("❌ Critical Error: Could not import duckduckgo_search or ddgs.")
        exit(1)

# --- CONFIGURATION ---
# We use broader queries to ensure we get ANY results
TARGET_SOURCES = [
    {"name": "Crunchbase List", "query": "top SaaS pre-seed VC investors US Crunchbase"},
    {"name": "AngelList",       "query": "active SaaS VCs AngelList Wellfound US"},
    {"name": "General Search",  "query": "B2B SaaS pre-seed investors United States contact email"},
    {"name": "OpenVC",          "query": "OpenVC list SaaS investors US"}
]

MAX_RESULTS_PER_SOURCE = 10 
MIN_SCORE_TO_KEEP = 30  # <--- LOWERED TO 30 to ensure data flows!

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
    """Gives points based on keywords found in the description"""
    score = 50 # Start with a base score
    text = text.lower()
    
    # Positive Keywords
    if "saas" in text: score += 10
    if "b2b" in text: score += 10
    if "investor" in text or "venture" in text: score += 10
    if "pre-seed" in text: score += 10
    if "usa" in text or "united states" in text: score += 10
    
    return min(score, 100)

def get_real_investors():
    all_results = []
    print("🚀 Starting Search (Threshold: 30 pts)...")
    
    with DDGS() as ddgs:
        for source in TARGET_SOURCES:
            print(f"🔎 Searching: {source['query']}...")
            try:
                # We search for text results
                search_results = list(ddgs.text(source['query'], max_results=MAX_RESULTS_PER_SOURCE))
                
                # DEBUG PRINT: How many raw results did we get?
                print(f"   👉 Raw results found: {len(search_results)}")
                
                for result in search_results:
                    title = result.get('title', 'Unknown')
                    link = result.get('href', '')
                    body = result.get('body', '')
                    
                    smart_score = calculate_smart_score(body + " " + title)
                    
                    # Log discarded items to see why we are losing them
                    if smart_score < MIN_SCORE_TO_KEEP:
                        # print(f"      🗑️ Discarded '{title[:15]}...' (Score: {smart_score})")
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
                    
                time.sleep(2) # Increased pause to avoid blocking
                
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
        print("❌ Still 0 leads? This usually means GitHub IP is being blocked by DuckDuckGo.")
