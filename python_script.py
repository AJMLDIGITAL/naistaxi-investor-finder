"""
Naistaixi Smart Investor Hunter
Searches broadly, SCORES the results, and only pushes QUALIFIED leads (>60).
"""

import requests
import json
import os
import time
from duckduckgo_search import DDGS

# --- CONFIGURATION ---
TARGET_SOURCES = [
    {"name": "Crunchbase List", "query": "top 20 SaaS pre-seed VC investors US Crunchbase"},
    {"name": "AngelList",       "query": "active SaaS VCs AngelList Wellfound US"},
    {"name": "General Search",  "query": "best B2B SaaS pre-seed investors United States contact"},
    {"name": "OpenVC",          "query": "OpenVC list SaaS investors US"}
]

MAX_RESULTS_PER_SOURCE = 10 
MIN_SCORE_TO_KEEP = 60  # <--- The Filter is Back!

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
    if "saas" in text: score += 20
    if "b2b" in text: score += 15
    if "software" in text: score += 10
    if "pre-seed" in text or "early stage" in text: score += 15
    if "venture" in text or "capital" in text: score += 10
    
    # Negative Keywords (Things we don't want)
    if "private equity" in text: score -= 20
    if "real estate" in text: score -= 30
    if "crypto" in text: score -= 10
    
    return min(score, 100) # Max score is 100

def get_real_investors():
    all_results = []
    print("🚀 Starting Smart Search...")
    
    with DDGS() as ddgs:
        for source in TARGET_SOURCES:
            print(f"🔎 Searching: {source['query']}...")
            try:
                search_results = list(ddgs.text(source['query'], max_results=MAX_RESULTS_PER_SOURCE))
                
                for result in search_results:
                    title = result.get('title', 'Unknown')
                    link = result.get('href', '')
                    body = result.get('body', '')
                    
                    # Calculate Score based on the text snippet
                    smart_score = calculate_smart_score(body + " " + title)
                    
                    # FILTER: Skip if score is too low
                    if smart_score < MIN_SCORE_TO_KEEP:
                        continue 

                    name = title.split("-")[0].split("|")[0].strip()
                    if len(name) > 30: name = name[:30] + "..."
                    
                    investor = {
                        "name": name,
                        "website": link,
                        "score": smart_score, 
                        "location": "US",
                        "type": "VC",
                        "source": source['name'],
                        "notes": f"Score: {smart_score}/100. Snippet: {body}",
                        "email": "" 
                    }
                    all_results.append(investor)
                    
                time.sleep(1)
                
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
            print(f"✅ Pushed (Score {investor['score']}): {investor['name']}")
        else:
            print(f"❌ Failed to Push: {investor['name']}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    investors = get_real_investors()
    print(f"\n📊 QUALIFIED LEADS FOUND (>60 pts): {len(investors)}")
    
    if len(investors) == 0:
        print("❌ No leads met the criteria. Try lowering the score threshold.")
    else:
        for inv in investors:
            push_to_monday(inv)
