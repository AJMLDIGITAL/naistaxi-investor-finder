import os
import requests
import json
import time

# --- CONFIGURATION ---
MONDAY_API_KEY = os.environ.get("MONDAY_API_KEY", "").strip()
MONDAY_BOARD_ID = os.environ.get("MONDAY_BOARD_ID", "").strip()
API_URL = "https://api.monday.com/v2"

# --- 1. THE DATABASE (Full Data) ---
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

# --- 2. ROBUST COLUMN DETECTION ---
def get_board_columns():
    print(f"🕵️  Mapping columns on Board {MONDAY_BOARD_ID}...")
    query = """query ($board_id: [ID!]) { boards (ids: $board_id) { columns { id title type } } }"""
    
    headers = {"Authorization": MONDAY_API_KEY, "Content-Type": "application/json"}
    
    # Defaults: Start with None so we don't force bad data
    mapping = {
        "website": None,
        "linkedin": None,
        "source": None,
        "score": None,
        "location": None
    }

    try:
        req = requests.post(API_URL, json={'query': query, 'variables': {'board_id': int(MONDAY_BOARD_ID)}}, headers=headers)
        data = req.json()
        
        if "errors" in data:
            print(f"   ⚠️ API Error reading columns: {data['errors'][0]['message']}")
            return mapping

        cols = data['data']['boards'][0]['columns']
        
        print("   --- Found Columns on Board ---")
        for col in cols:
            t = col['title'].lower()
            cid = col['id']
            ctype = col['type']
            print(f"   found: '{col['title']}' ({ctype}) -> ID: {cid}")
            
            # Map columns by fuzzy name matching
            if "website" in t: mapping["website"] = cid
            elif "linkedin" in t: mapping["linkedin"] = cid
            elif "source" in t: mapping["source"] = cid
            elif "score" in t or "rating" in t: mapping["score"] = cid
            elif "location" in t: mapping["location"] = cid
            
        print(f"   ------------------------------")
        return mapping

    except Exception as e:
        print(f"   ❌ Detection failed: {e}")
        return mapping

# --- 3. UPLOAD LOGIC ---
def upload_full_row(investor, mapping):
    # Combine key info into Name to ensure visibility no matter what
    item_name = f"{investor['name']} | {investor['type']} | {investor['loc']}"
    print(f"   📤 Uploading: {item_name}")

    # Build the column values dictionary dynamically
    # We only add columns that we actually found IDs for.
    values = {}
    
    if mapping["website"]:
        values[mapping["website"]] = {"url": investor["web"], "text": "Website"}
        
    if mapping["linkedin"]:
        values[mapping["linkedin"]] = {"url": investor["linkedin"], "text": "LinkedIn"}
        
    if mapping["source"]:
        values[mapping["source"]] = {"url": investor["source"], "text": "Source"}
        
    if mapping["score"]:
        values[mapping["score"]] = str(investor["score"])
        
    if mapping["location"]:
        values[mapping["location"]] = investor["loc"]

    # Construct Query
    query = """
    mutation ($board_id: ID!, $item_name: String!, $column_values: JSON!) {
      create_item (board_id: $board_id, item_name: $item_name, column_values: $column_values) { 
        id 
      }
    }
    """
    
    variables = {
        "board_id": int(MONDAY_BOARD_ID), 
        "item_name": item_name,
        "column_values": json.dumps(values)
    }
    
    headers = {"Authorization": MONDAY_API_KEY, "Content-Type": "application/json"}
    
    try:
        req = requests.post(API_URL, json={'query': query, 'variables': variables}, headers=headers)
        response = req.json()
        
        # Check if 'data' is present
        if response.get("data") and response['data'].get('create_item'):
            item_id = response['data']['create_item']['id']
            
            # Add the Note as a bubble
            note_body = f"NOTES: {investor['note']}"
            update_query = """mutation ($item_id: ID!, $body: String!) { create_update (item_id: $item_id, body: $body) { id } }"""
            requests.post(API_URL, json={'query': update_query, 'variables': {'item_id': item_id, 'body': note_body}}, headers=headers)
            print("      ✅ Success")
        else:
            # If Monday rejected it, print the exact error message
            error_msg = response.get('errors', [{'message': 'Unknown Error'}])[0]['message']
            print(f"      ❌ Monday Rejected Upload: {error_msg}")
            
    except Exception as e:
        print(f"      ❌ Python Error: {e}")

def main():
    if not MONDAY_API_KEY: 
        print("❌ Missing API Key"); return

    # 1. Get Column IDs
    mapping = get_board_columns()
    
    # Check if we are missing critical columns
    missing = [k for k, v in mapping.items() if v is None]
    if missing:
        print(f"   ⚠️ WARNING: Could not find columns for: {missing}")
        print("      (Data for these columns will be skipped to prevent crashing)")

    # 2. Upload Database
    print("\n--- POPULATING DATABASE ---")
    for inv in FULL_INVESTOR_DB:
        upload_full_row(inv, mapping)
        time.sleep(1)

if __name__ == "__main__":
    main()
