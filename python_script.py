"""
Naistaixi Multi-Source Investor Hunter
Searches Crunchbase, AngelList, LinkedIn, and OpenVC via DuckDuckGo.
"""

import requests
import json
import os
import re
import time
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
# We use "site:" commands to force the search engine to look INSIDE these databases
TARGET_SOURCES = [
    {"name": "Crunchbase", "query": 'site:crunchbase.com/organization "pre-seed" "SaaS" "US" "investor"'},
    {"name": "AngelList",  "query": 'site:wellfound.com/company "venture capital" "SaaS" "US"'},
    {"name": "LinkedIn",   "query": 'site:linkedin.com/company "venture capital" "SaaS" "US"'},
    {"name": "OpenVC",     "query": 'site:openvc.app "SaaS" "investor"'},
    {"name": "FiBAN",      "query": 'site:fiban.org "investor"'}
]

MAX_RESULTS_PER_SOURCE = 5  # 5 results from EACH source (Total ~25 leads)

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

def get_real_investors():
    all_results = []
    
    with DDGS() as ddgs:
        for source in TARGET_SOURCES:
            print(f"🔎 X-Ray Searching {source['name']}...")
            try:
                # Search using the specific "site:" query
                search_results = list(ddgs.text(source['query'], max_results=MAX_RESULTS_PER_SOURCE))
                
                for result in search_results:
                    title = result.get('title', 'Unknown')
                    link = result.get('href', '')
                    body = result.get('body', '')
                    
                    # CLEANUP: Remove " | Crunchbase" or " | LinkedIn" from names
                    name = title.split("|")[0].split("-")[0].split("—")[0].strip()
                    
                    investor = {
                        "name": name,
                        "website": link,
                        "score": 85,  # Higher score because these are verified DBs
                        "location": "US",
                        "type": "VC",
                        "source": f"Scraped from {source['name']}",
                        "notes": f"Found via {source['name']}: {body}",
                        "email": "" # We won't hunt emails on LinkedIn/CB to avoid banning
                    }
                    all_results.append(investor)
                    
                time.sleep(2) # Pause between sources
                
            except Exception as e:
                print(f"⚠️ Could not search {source['name']}: {e}")
                
    return all_results

def push_to_monday(investor):
    url = "https://api.monday.com/v2"
    headers = {"Authorization": MONDAY_API_KEY, "Content-Type": "application/json"}
    
    column_values = {
        MONDAY_COLUMN_IDS["status_id"]: {"label": "New Lead"},
        MONDAY_COLUMN_IDS["type_id"]: {"label": investor["type"]},
        MONDAY_COLUMN_IDS["website_id"]: {"url": investor["website"], "text": investor["source"]},
        MONDAY_COLUMN_IDS["score_id"]: investor["score"],
        MONDAY_COLUMN_IDS["location_id"]: investor["location"],
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
            print(f"✅ Added {investor['source']} Lead: {investor['name']}")
        else:
            print(f"❌ Failed: {investor['name']}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    investors = get_real_investors()
    print(f"📊 Found {len(investors)} total leads across all sources.")
    for inv in investors:
        push_to_monday(inv)
