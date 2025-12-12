"""
Naistaixi Investor Finder - DEBUG MODE
This script prints the RAW response from Monday.com to find the hidden error.
"""

import requests
import json
import os
import csv
from datetime import datetime

# --- CONFIGURATION ---
# These must match your board exactly!
MONDAY_COLUMN_IDS = {
    "status_id": "color_mkyj5j54",    # Status Column
    "type_id": "color_mkyjzz25",      # Type Column 
    "website_id": "link_mkyj3m1e",    # Website
    "linkedin_id": "link_mkyjpc2z",   # LinkedIn
    "score_id": "numeric_mkyjx5h6",   # Score
    "location_id": "text_mkyjfhyc",   # Location
    "notes_id": "long_text_mkyjra9c", # Notes
    "source_id": "text_mkyjcxqn",     # Source
    "email_id": "email_mkyjbej4"      # Email
}

MONDAY_API_KEY = os.environ.get('MONDAY_API_KEY')
MONDAY_BOARD_ID = os.environ.get('MONDAY_BOARD_ID')

def push_debug_item():
    url = "https://api.monday.com/v2"
    headers = {"Authorization": MONDAY_API_KEY, "Content-Type": "application/json"}
    
    # We will try to add JUST ONE dummy item to test the connection
    item_name = "TEST CONNECTION ITEM"
    
    # We send simplified data to see where it breaks
    column_values = {
        MONDAY_COLUMN_IDS["status_id"]: {"label": "New Lead"}, 
        MONDAY_COLUMN_IDS["type_id"]: {"label": "VC"},
        MONDAY_COLUMN_IDS["email_id"]: {"text": "test@test.com", "email": "test@test.com"}
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
        "itemName": item_name,
        "columnValues": json.dumps(column_values)
    }
    
    print(f"🚀 Sending Test Item to Board ID: {MONDAY_BOARD_ID}")
    
    try:
        response = requests.post(url, headers=headers, json={"query": query, "variables": variables})
        
        # PRINT THE RAW TRUTH
        print(f"\n🔍 HTTP Status Code: {response.status_code}")
        print(f"📄 Full Response from Monday:\n{response.text}\n")
        
        response_json = response.json()
        if "errors" in response_json:
            print("❌ ERROR FOUND! Monday.com rejected the data.")
            print("Reason: " + response_json["errors"][0]["message"])
        elif "data" in response_json and response_json["data"]["create_item"] is not None:
            print("✅ SUCCESS! Item created. ID: " + response_json["data"]["create_item"]["id"])
        else:
            print("⚠️ Unknown response format.")
            
    except Exception as e:
        print(f"❌ Network Error: {str(e)}")

if __name__ == "__main__":
    push_debug_item()
