import os
import requests
import json
import time

# --- CONFIGURATION ---
MONDAY_API_KEY = os.environ.get("MONDAY_API_KEY", "").strip()
MONDAY_BOARD_ID = os.environ.get("MONDAY_BOARD_ID", "").strip()
API_URL = "https://api.monday.com/v2"

# --- 1. FULL DATA ---
FULL_INVESTOR_DB = [
    {
        "name": "Rosberg Ventures", "type": "VC Firm", "loc": "Monaco",
        "web": "https://rosberg.ventures/", "linkedin": "https://www.linkedin.com/company/rosberg-ventures",
        "source": "https://slush.org", "score": 5,
        "note": "Founded by Nico Rosberg. Heavy focus on Mobility/Sustainability."
    },
    {
        "name": "BackingMinds", "type": "VC Firm", "loc": "Stockholm",
        "web": "https://www.backingminds.com/", "linkedin": "https://www.linkedin.com/company/backingminds",
        "source": "https://tech.eu", "score": 5,
        "note": "Founded by women, invests in 'blind spots'."
    },
    {
        "name": "Auxxo Female Catalyst", "type": "VC Firm", "loc": "Berlin",
        "web": "https://auxxo.de/", "linkedin": "https://www.linkedin.com/company/auxxo-female-catalyst-fund",
        "source": "https://sifted.eu", "score": 5,
        "note": "Co-invests specifically in female founders."
    },
    {
        "name": "EIT Urban Mobility", "type": "Grant/VC", "loc": "Barcelona",
        "web": "https://www.eiturbanmobility.eu/", "linkedin": "https://www.linkedin.com/company/eit-urban-mobility",
        "source": "https://eit.europa.eu", "score": 5,
        "note": "Major EU funding for mobility startups."
    },
    {
        "name": "Maki.vc", "type": "VC Firm", "loc": "Helsinki",
        "web": "https://maki.vc/", "linkedin": "https://www.linkedin.com/company/maki-vc",
        "source": "https://slush.org", "score": 4,
        "note": "Deep tech/Brand seed fund. Active in Nordic female founder scene."
    },
    {
        "name": "Icebreaker.vc", "type": "VC Firm", "loc": "Helsinki",
        "web": "https://icebreaker.vc/", "linkedin": "https://www.linkedin.com/company/icebreaker-vc",
        "source": "https://icebreaker.vc/portfolio", "score": 4,
        "note": "Pre-seed specialists. Extensive network in Finland/Sweden."
    },
    {
        "name": "Unconventional Ventures", "type": "VC Firm", "loc": "Copenhagen",
        "web": "https://www.unconventional.vc/", "linkedin": "https://www.linkedin.com/company/unconventional-ventures",
        "source": "https://www.unconventional.vc/impact", "score": 5,
        "note": "Impact fund investing in diverse founding teams."
    },
    {
        "name": "Voima Ventures", "type": "VC Firm", "loc": "Helsinki",
        "web": "https://voimaventures.com/", "linkedin": "https://www.linkedin.com/company/voima-ventures",
        "source": "https://voimaventures.com/news", "score": 4,
        "note": "Science-based deep tech, mobility solutions."
    },
    {
        "name": "Crowberry Capital", "type": "VC Firm", "loc": "Reykjavik",
        "web": "https://www.crowberrycapital.com/", "linkedin": "https://www.linkedin.com/company/crowberry-capital",
        "source": "https://techcrunch.com", "score": 4,
        "note": "Female-led fund investing in Nordic tech companies."
    }
]

# --- 2. SMART COLUMN MAPPING ---
def get_column_details():
    print(f"🕵️  Mapping columns & TYPES on Board {MONDAY_BOARD_ID}...")
    query = """query ($board_id: [ID!]) { boards (ids: $board_id) { columns { id title type } } }"""
    headers = {"Authorization": MONDAY_API_KEY, "Content-Type": "application/json"}
    
    mapping = {}

    try:
        req = requests.post(API_URL, json={'query': query, 'variables': {'board_id': int(MONDAY_BOARD_ID)}}, headers=headers)
        data = req.json()
        
        if "errors" in data:
            print(f"   ⚠️ API Error: {data['errors'][0]['message']}")
            return {}

        cols = data['data']['boards'][0]['columns']
        
        for col in cols:
            t = col['title'].lower()
            c_id = col['id']
            c_type = col['type'] # Crucial! We capture the type now.
            
            key = None
            if "website" in t: key = "website"
            elif "linkedin" in t: key = "linkedin"
            elif "source" in t: key = "source"
            elif "score" in t or "rating" in t: key = "score"
            elif "location" in t: key = "location"
            
            if key:
                mapping[key] = {"id": c_id, "type": c_type}
                print(f"   ✅ Mapped '{key}' -> ID: {c_id} | Type: {c_type}")

        return mapping

    except Exception as e:
        print(f"   ❌ Detection failed: {e}")
        return {}

# --- 3. SMART FORMATTER (The Fix) ---
def format_value_for_monday(value, col_type):
    """Formats data correctly based on what Monday expects for that column type"""
    if not value: return None
    
    # 1. LINK COLUMNS
    if col_type == "link":
        return {"url": value, "text": "Link"}
    
    # 2. TEXT COLUMNS (Sometimes users make 'Website' a text column)
    elif col_type == "text":
        return str(value)
        
    # 3. NUMBER COLUMNS
    elif col_type == "numeric":
        return str(value) # Numbers must be strings in JSON
        
    # 4. RATING COLUMNS (Stars)
    elif col_type == "rating":
        return {"rating": int(value)}
        
    # 5. DROPDOWN/STATUS
    elif col_type == "color" or col_type == "status":
        return {"label": str(value)}
        
    # Default fallback
    return str(value)

# --- 4. UPLOAD LOGIC ---
def upload_row(inv, mapping):
    item_name = f"{inv['name']} | {inv['type']} | {inv['loc']}"
    print(f"   📤 Uploading: {item_name}")

    # Build Column Values
    col_values = {}
    
    # Helper to add data if the column exists
    def add_val(key, data_val):
        if key in mapping:
            col_id = mapping[key]["id"]
            col_type = mapping[key]["type"]
            # Auto-format the data so Monday accepts it!
            col_values[col_id] = format_value_for_monday(data_val, col_type)

    add_val("website", inv["web"])
    add_val("linkedin", inv["linkedin"])
    add_val("source", inv["source"])
    add_val("score", inv["score"])
    add_val("location", inv["loc"])

    query = """
    mutation ($board_id: ID!, $item_name: String!, $column_values: JSON!) {
      create_item (board_id: $board_id, item_name: $item_name, column_values: $column_values) { id }
    }
    """
    
    variables = {
        "board_id": int(MONDAY_BOARD_ID), 
        "item_name": item_name,
        "column_values": json.dumps(col_values)
    }
    
    headers = {"Authorization": MONDAY_API_KEY, "Content-Type": "application/json"}
    
    try:
        req = requests.post(API_URL, json={'query': query, 'variables': variables}, headers=headers)
        response = req.json()
        
        if response.get("data") and response['data'].get('create_item'):
            item_id = response['data']['create_item']['id']
            # Add Note
            note = f"NOTE: {inv['note']}"
            q2 = """mutation ($item_id: ID!, $body: String!) { create_update (item_id: $item_id, body: $body) { id } }"""
            requests.post(API_URL, json={'query': q2, 'variables': {'item_id': item_id, 'body': note}}, headers=headers)
            print("      ✅ Success")
        else:
            err = response.get('errors', [{'message': 'Unknown'}])[0]['message']
            print(f"      ❌ Failed: {err}")
    except Exception as e:
        print(f"      ❌ Error: {e}")

def main():
    if not MONDAY_API_KEY: print("❌ Missing Key"); return

    # 1. Get Map
    mapping = get_column_details()
    
    # 2. Upload
    print("\n--- STARTING UPLOAD ---")
    for inv in FULL_INVESTOR_DB:
        upload_row(inv, mapping)
        time.sleep(1)

if __name__ == "__main__":
    main()
