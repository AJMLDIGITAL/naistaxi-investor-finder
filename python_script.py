import os
import requests
import json

# Load secrets
API_KEY = os.environ.get("MONDAY_API_KEY")
BOARD_ID = os.environ.get("MONDAY_BOARD_ID")
API_URL = "https://api.monday.com/v2"

headers = {"Authorization": API_KEY, "Content-Type": "application/json"}

def run_debug():
    print(f"🕵️ DIAGNOSING CONNECTION TO BOARD ID: {BOARD_ID}...\n")

    # 1. GET BOARD NAME (Checks if ID is correct)
    query_board = """
    query {
      boards (ids: %s) {
        name
        groups {
          id
          title
        }
      }
    }
    """ % BOARD_ID

    try:
        r = requests.post(API_URL, json={'query': query_board}, headers=headers)
        data = r.json()
        
        if "errors" in data:
            print("❌ CRITICAL ERROR: API Key or Board ID is WRONG.")
            print(f"Error Details: {data['errors'][0]['message']}")
            return

        boards = data['data']['boards']
        if not boards:
            print(f"❌ ERROR: Board {BOARD_ID} not found. Are you sure this number is correct?")
            return

        board_name = boards[0]['name']
        print(f"✅ CONNECTED TO BOARD: '{board_name}'")
        
        groups = boards[0]['groups']
        first_group = groups[0]
        print(f"   Targeting Group: '{first_group['title']}' (ID: {first_group['id']})")

        # 2. CREATE A TEST ITEM
        print("\n📝 Attempting to create a TEST ITEM...")
        mutation = """
        mutation {
          create_item (
            board_id: %s, 
            group_id: "%s",
            item_name: "🟥 TEST ROW - IF YOU SEE THIS, IT WORKS"
          ) {
            id
          }
        }
        """ % (BOARD_ID, first_group['id'])

        r2 = requests.post(API_URL, json={'query': mutation}, headers=headers)
        item_data = r2.json()

        if "data" in item_data:
            item_id = item_data['data']['create_item']['id']
            print(f"\n🎉 SUCCESS! Item created.")
            print(f"🆔 New Item ID: {item_id}")
            print(f"🔗 CLICK HERE TO FIND IT: https://monday.com/boards/{BOARD_ID}/pulses/{item_id}")
        else:
            print("❌ Failed to create item.")
            print(item_data)

    except Exception as e:
        print(f"❌ Python Error: {e}")

if __name__ == "__main__":
    run_debug()
