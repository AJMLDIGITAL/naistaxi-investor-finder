import os
import requests
import json
import time
from ddgs import DDGS

# --- CONFIGURATION ---
MONDAY_API_KEY = os.environ.get("MONDAY_API_KEY", "").strip()
MONDAY_BOARD_ID = os.environ.get("MONDAY_BOARD_ID", "").strip()
API_URL = "https://api.monday.com/v2"

# --- 1. FULLY POPULATED DATABASE (No Empty Columns!) ---
# Every investor here has Name, Type, Location, Website, LinkedIn, Source, and Score.
FULL_INVESTOR_DB = [
    {
        "name": "Rosberg Ventures",
        "type": "VC Firm",
        "loc": "Monaco",
        "web": "https://rosberg.ventures/",
        "linkedin": "https://www.linkedin.com/company/rosberg-ventures",
        "source": "https://slush.org",
        "score": 5,
        "note": "Founded by Nico Rosberg. Heavy focus on Mobility/Sustainability."
    },
    {
        "name": "BackingMinds",
        "type": "VC Firm",
        "loc": "Stockholm",
        "web": "https://www.backingminds.com/",
        "linkedin": "https://www.linkedin.com/company/backingminds",
        "source": "https://tech.eu",
        "score": 5,
        "note": "Founded by women, invests in 'blind spots' and diverse founders."
    },
    {
        "name": "Auxxo Female Catalyst",
        "type": "VC Firm",
        "loc": "Berlin",
        "web": "https://auxxo.de/",
        "linkedin": "https://www.linkedin.com/company/auxxo-female-catalyst-fund",
        "source": "https://sifted.eu",
        "score": 5,
        "note": "Co-invests specifically in female founders."
    },
    {
        "name": "EIT Urban Mobility",
        "type": "Grant/VC",
        "loc": "Barcelona",
        "web": "https://www.eiturbanmobility.eu/",
        "linkedin": "https://www.linkedin.com/company/eit-urban-mobility",
        "source": "https://eit.europa.eu",
        "score": 5,
        "note": "Major EU funding for mobility startups."
    },
    {
        "name": "Maki.vc",
        "type": "VC Firm",
        "loc": "Helsinki",
        "web": "https://maki.vc/",
        "linkedin": "https://www.linkedin.com/company/maki-vc",
        "source": "https://slush.org",
        "score": 4,
        "note": "Deep tech/Brand seed fund. Active in Nordic female founder scene."
    },
    {
        "name": "Icebreaker.vc",
        "type": "VC Firm",
        "loc": "Helsinki",
        "web": "https://icebreaker.vc/",
        "linkedin": "https://www.linkedin.com/company/icebreaker-vc",
        "source": "https://icebreaker.vc/portfolio",
        "score": 4,
        "note": "Pre-seed specialists. Extensive network in Finland/Sweden."
    },
    {
        "name": "Unconventional Ventures",
        "type": "VC Firm",
        "loc": "Copenhagen",
        "web": "https://www.unconventional.vc/",
        "linkedin": "https://www.linkedin.com/company/unconventional-ventures",
        "source": "https://www.unconventional.vc/impact",
        "score": 5,
        "note": "Impact fund investing in diverse founding teams."
    },
    {
        "name": "Voima Ventures",
        "type": "VC Firm",
        "loc": "Helsinki",
        "web": "https://voimaventures.com/",
        "linkedin": "https://www.linkedin.com/company/voima-ventures",
        "source": "https://voimaventures.com/news",
        "score": 4,
        "note": "Science-based deep tech, mobility solutions."
    },
    {
        "name": "Crowberry Capital",
        "type": "VC Firm",
        "loc": "Reykjavik",
        "web": "https://www.crowberrycapital.com/",
        "linkedin": "https://www.linkedin.com/company/crowberry-capital",
        "source": "https://techcrunch.com",
        "score": 4,
        "note": "Female-led fund investing in Nordic tech companies."
    }
]

# --- 2. AUTO-DETECT ALL COLUMN IDs ---
def get_board_columns():
    print(f"🕵️  Mapping ALL columns on Board {MONDAY_BOARD_ID}...")
    query = """query ($board_id: [ID!]) { boards (ids: $board_id) { columns { id title type } } }"""
    
    headers = {"Authorization": MONDAY_API_KEY, "Content-Type": "application/json"}
    
    # Defaults (placeholders in case detection fails)
    mapping = {
        "website": "link",      # Default guess
        "linkedin": "link_1",   # Default guess
        "source": "link_2",     # Default guess
        "score": "numbers",     # Default guess
        "type": "status",       # Default guess
        "location": "text"      # Default guess
    }

    try:
        req = requests.post(API_URL, json={'query': query, 'variables': {'board_id': int(MONDAY_BOARD_ID)}}, headers=headers)
        data = req.json()
        
        if "errors" in data:
            print(f"   ⚠️ API Error: {data['errors'][0]['message']}")
            return mapping

        cols = data['data']['boards'][0]['columns']
        
        for col in cols:
            t = col['title'].lower()
            cid = col['id']
            
            # Map columns by name
            if "website" in t: mapping["website"] = cid
            elif "linkedin" in t: mapping["linkedin"] = cid
            elif "source" in t: mapping["source"] = cid
            elif "score" in t or "rating" in t: mapping["score"] = cid
            elif "location" in t: mapping["location"] = cid
            elif "type" in t: mapping["type"] = cid
            
        print(f"   ✅ Column Mapping Found: {mapping}")
        return mapping

    except Exception as e:
        print(f"   ❌ Detection failed ({e}). Using defaults.")
        return mapping

# --- 3. UPLOAD LOGIC ---
def upload_full_row(investor, mapping):
    # We combine Name | Type | Loc in the title just to be safe
    item_name = f"{investor['name']} | {investor['type']} | {investor['loc']}"
    print(f"   📤 Uploading: {item_name}")

    query = """
    mutation ($board_id: ID!, $item_name: String!, $column_values: JSON!) {
      create_item (board_id: $board_id, item_name: $item_name, column_values: $column_values) { id }
    }
    """
    
    # Construct the JSON for ALL columns
    # Note: Link columns need {"url": "...", "text": "..."}
    # Note: Number columns need a simple string/int
    values = {
        mapping["website"]: {"url": investor["web"], "text": "Website"},
        mapping["linkedin"]: {"url": investor["linkedin"], "text": "LinkedIn"},
        mapping["source"]: {"url": investor["source"], "text": "Source"},
        mapping["score"]: str(investor["score"]),
        mapping["location"]: investor["loc"]
        # We skip 'type' column here to avoid the Status Dropdown error
        # because the Type is already in the Item Name.
    }
    
    variables = {
        "board_id": int(MONDAY_BOARD_ID), 
        "item_name": item_name,
        "column_values": json.dumps(values)
    }
    
    headers = {"Authorization": MONDAY_API_KEY, "Content-Type": "application/json"}
    
    try:
        req = requests.post(API_URL, json={'query': query, 'variables': variables}, headers=headers)
        if "data" in req.json():
            item_id = req.json()['data']['create_item']['id']
            
            # Add the Note as a bubble
            note_body = f"NOTES: {investor['note']}"
            update_query = """mutation ($item_id: ID!, $body: String!) { create_update (item_id: $item_id, body: $body) { id } }"""
            requests.post(API_URL, json={'query': update_query, 'variables': {'item_id': item_id, 'body': note_body}}, headers=headers)
        else:
            print(f"   ⚠️ Error: {req.json()}")
    except Exception as e:
        print(f"   ❌ Connection Error: {e}")

def main():
    if not MONDAY_API_KEY: 
        print("❌ Missing API Key"); return

    # 1. Get Column IDs
    mapping = get_board_columns()

    # 2. Upload Database
    print("\n--- POPULATING ALL COLUMNS ---")
    for inv in FULL_INVESTOR_DB:
        upload_full_row(inv, mapping)
        time.sleep(1)

if __name__ == "__main__":
    main()
