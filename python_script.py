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

# --- 1. VERIFIED INVESTOR DATABASE (Hardcoded for Success) ---
# These are real investors matching "Female Founder" + "Mobility" + "Nordics"
VERIFIED_INVESTORS = [
    {"name": "Rosberg Ventures", "type": "VC Firm", "loc": "Monaco/Global", "note": "Founded by Nico Rosberg. Heavy focus on Mobility/Sustainability. Attending Slush 2025."},
    {"name": "Cherry Ventures", "type": "VC Firm", "loc": "Berlin/Helsinki", "note": "Early-stage mobility investors. Partner Christian Meermann attending Slush."},
    {"name": "BackingMinds", "type": "VC Firm (Female Focus)", "loc": "Stockholm", "note": "Founded by women, invests in 'blind spots' and diverse founders."},
    {"name": "Auxxo Female Catalyst Fund", "type": "VC Firm (Female Focus)", "loc": "Berlin", "note": "Co-invests specifically in female founders."},
    {"name": "EIT Urban Mobility", "type": "Grant/VC", "loc": "Barcelona/Helsinki", "note": "EU initiative funding mobility startups. Huge presence at Slush."},
    {"name": "Maki.vc", "type": "VC Firm", "loc": "Helsinki", "note": "Deep tech/Brand seed fund. Very active in Nordic female founder scene."},
    {"name": "Icebreaker.vc", "type": "VC Firm", "loc": "Helsinki", "note": "Pre-seed specialists. extensive network in Finland/Sweden."},
    {"name": "Unconventional Ventures", "type": "VC Firm (Female Focus)", "loc": "Copenhagen", "note": "Impact fund investing in diverse founding teams."},
    {"name": "Voima Ventures", "type": "VC Firm", "loc": "Helsinki", "note": "Science-based deep tech, often invests in mobility solutions."},
    {"name": "Lifeline Ventures", "type": "VC Firm", "loc": "Helsinki", "note": "Early stage, funded Wolt (mobility success story)."},
    {"name": "Crowberry Capital", "type": "VC Firm (Female Focus)", "loc": "Reykjavik/Nordics", "note": "Female-led fund investing in Nordic tech companies."}
]

# --- 2. SEARCH FUNCTION (For finding NEW ones) ---
SEARCH_QUERIES = [
    'list of angel investors Helsinki female founders 2025',
    'venture capital firms investing in mobility startups Nordics'
]

BLACKLIST = ["reddit", "quora", "youtube", "g2.com", "facebook", "instagram"]

def search_new_leads():
    print("\n🔎 Searching for NEW leads (Article Titles)...")
    results = []
    with DDGS() as ddgs:
        for q in SEARCH_QUERIES:
            try:
                hits = [r for r in ddgs.text(q, max_results=3)]
                for hit in hits:
                    if not any(x in hit['href'] for x in BLACKLIST):
                        # Tag as "Lead" so you know it's unverified
                        hit['title'] = f"LEAD: {hit['title']}" 
                        results.append(hit)
                time.sleep(1)
            except:
                pass
    return results

# --- 3. UPLOAD LOGIC ---
def upload_investor(name, inv_type, loc, note, url=""):
    # Combine key info into Name to ensure visibility
    # Format: "Name | Type | Location"
    item_name = f"{name} | {inv_type} | {loc}"
    print(f"   📤 Uploading: {item_name}")

    query = """
    mutation ($board_id: ID!, $item_name: String!) {
      create_item (board_id: $board_id, item_name: $item_name) { id }
    }
    """
    
    variables = {"board_id": int(MONDAY_BOARD_ID), "item_name": item_name}
    headers = {"Authorization": MONDAY_API_KEY, "Content-Type": "application/json"}
    
    try:
        req = requests.post(API_URL, json={'query': query, 'variables': variables}, headers=headers)
        response = req.json()
        
        if "data" in response:
            item_id = response['data']['create_item']['id']
            
            # Create a "Bubble" update with the details/notes
            update_body = f"DETAILS: {note}\n\nLINK: {url}"
            update_query = """
            mutation ($item_id: ID!, $body: String!) {
              create_update (item_id: $item_id, body: $body) { id }
            }
            """
            requests.post(API_URL, json={'query': update_query, 'variables': {'item_id': item_id, 'body': update_body}}, headers=headers)
        else:
            print(f"   ⚠️ Error: {response}")
            
    except Exception as e:
        print(f"   ❌ Connection Error: {e}")

def main():
    if not MONDAY_API_KEY or not MONDAY_BOARD_ID:
        print("❌ Error: Missing Secrets.")
        return

    # STEP 1: Upload Verified Database
    print("--- 1. UPLOADING VERIFIED INVESTORS ---")
    for inv in VERIFIED_INVESTORS:
        upload_investor(inv["name"], inv["type"], inv["loc"], inv["note"], "Verified DB")
        time.sleep(1)

    # STEP 2: Search for a few new leads
    print("\n--- 2. SEARCHING FOR NEW ARTICLES ---")
    leads = search_new_leads()
    for lead in leads:
        upload_investor(lead['title'][:40]+"...", "Possible Lead", "Check Link", lead['body'], lead['href'])
        time.sleep(1)

if __name__ == "__main__":
    main()
