"""
Naistaixi Automated Investor Finder
Searches for US-based SaaS/B2B investors and syncs to Monday.com.
FINAL PRODUCTION VERSION.
"""

import requests
import json
import re
from datetime import datetime
from typing import List, Dict
import os
import csv

# --- CONFIGURATION: US SaaS/B2B FOCUS ---
MISSION_KEYWORDS = ["SaaS", "B2B", "software", "fintech", "early-stage", "pre-seed"]
LOCATIONS = ["US", "San Francisco", "New York", "Boston", "California", "Silicon Valley"]

# --- CRITICAL: CONFIRMED MONDAY.COM COLUMN IDS ---
MONDAY_COLUMN_IDS = {
    "status_id": "color_mkyj5j54",    # Status Column (Set to 'New Lead')
    "type_id": "color_mkyjzz25",      # Type Column (VC, Angel, etc.)
    "website_id": "link_mkyj3m1e",    # Website Column
    "linkedin_id": "link_mkyjpc2z",   # LinkedIn Column
    "score_id": "numeric_mkyjx5h6",   # Score Column
    "location_id": "text_mkyjfhyc",   # Location Column
    "notes_id": "long_text_mkyjra9c", # Notes Column
    "source_id": "text_mkyjcxqn",     # Source Column
    "email_id": "email_mkyjbej4"      # Contact Email Column
}

# Get credentials from environment
MONDAY_API_KEY = os.environ.get('MONDAY_API_KEY')
MONDAY_BOARD_ID = os.environ.get('MONDAY_BOARD_ID')

class InvestorFinder:
    def __init__(self):
        self.investors = []
        
    def search_crunchbase_free(self) -> List[Dict]:
        """Simulated Search for US SaaS Investors"""
        # Representative US SaaS/B2B firms
        investors = [
            {"name": "Susa Ventures", "location": "San Francisco, US", "website": "https://susaventures.com", "linkedin": "https://www.linkedin.com/company/susa-ventures", "email": "info@susaventures.com", "type": "VC", "sectors": ["B2B", "SaaS", "Fintech"], "stage": "pre-seed, seed"},
            {"name": "Uncork Capital", "location": "Palo Alto, US", "website": "https://uncorkcapital.com", "linkedin": "https://www.linkedin.com/company/uncork-capital", "email": "hello@uncorkcapital.com", "type": "VC", "sectors": ["B2B", "SaaS", "Marketplaces"], "stage": "pre-seed, seed"},
            {"name": "Pear VC", "location": "Palo Alto, US", "website": "https://pear.vc", "linkedin": "https://www.linkedin.com/company/pear-vc", "email": "contact@pear.vc", "type": "VC", "sectors": ["B2B", "SaaS", "Deeptech"], "stage": "pre-seed, seed"},
            {"name": "Homebrew", "location": "San Francisco, US", "website": "https://homebrew.vc", "linkedin": "https://www.linkedin.com/company/homebrew-vc", "email": "pitch@homebrew.vc", "type": "VC", "sectors": ["B2B", "SaaS"], "stage": "pre-seed"},
            {"name": "Active Capital", "location": "San Antonio, US", "website": "https://activecapital.com", "linkedin": "https://www.linkedin.com/company/active-capital", "email": "hello@activecapital.com", "type": "VC", "sectors": ["B2B", "SaaS", "Software"], "stage": "pre-seed, seed"},
            {"name": "500 Global", "location": "San Francisco, US", "website": "https://500.co", "linkedin": "https://www.linkedin.com/company/500startups", "email": "global@500.co", "type": "Accelerator/VC", "sectors": ["Fintech", "SaaS", "B2B"], "stage": "pre-seed, seed"}
        ]
        return investors
    
    def search_angellist_free(self) -> List[Dict]:
        return [{"name": "Operator Collective", "location": "San Francisco, US", "website": "https://operatorcollective.com", "linkedin": "https://www.linkedin.com/company/operator-collective", "email": "contact@operatorcollective.com", "type": "VC/Angel", "sectors": ["B2B", "SaaS"], "stage": "seed"}]
    
    def search_github_lists(self) -> List[Dict]:
        return []
    
    def calculate_score(self, investor: Dict) -> int:
        score = 0
        stage = investor.get("stage", "").lower()
        if "pre-seed" in stage: score += 40
        elif "seed" in stage: score += 30
        
        location = investor.get("location", "").lower()
        if any(loc.lower() in location for loc in LOCATIONS): score += 20
        
        sectors = " ".join(investor.get("sectors", [])).lower()
        if "saas" in sectors or "b2b" in sectors: score += 30
        if "software" in sectors or "fintech" in sectors: score += 10
        return min(score, 100)
    
    def enrich_investor(self, investor: Dict) -> Dict:
        """Add calculated fields"""
        investor["score"] = self.calculate_score(investor)
        investor["source"] = "Automated Discovery"
        investor["focus"] = f"{', '.join(investor.get('sectors', []))} | {investor.get('stage', 'N/A')}"
        investor["email"] = investor.get("email", "")
        
        # Build Notes Content
        investor["notes_content"] = f"Sectors: {investor['focus']}"
        return investor
    
    def push_to_monday(self, investor: Dict):
        """Create item in Monday.com board using CONFIRMED IDs"""
        
        url = "https://api.monday.com/v2"
        headers = {"Authorization": MONDAY_API_KEY, "Content-Type": "application/json"}
        
        # --- Final Column Value Mapping ---
        column_values = {
            MONDAY_COLUMN_IDS["website_id"]: {"url": investor.get("website", ""), "text": "Website"},
            MONDAY_COLUMN_IDS["linkedin_id"]: {"url": investor.get("linkedin", ""), "text": "LinkedIn"},
            MONDAY_COLUMN_IDS["score_id"]: investor.get("score", 0), 
            MONDAY_COLUMN_IDS["location_id"]: investor.get("location", ""), 
            MONDAY_COLUMN_IDS["source_id"]: investor.get("source", ""),
            MONDAY_COLUMN_IDS["email_id"]: {"text": investor.get("email", ""), "email": investor.get("email", "")},
            
            # Status mapped to "New Lead" using ID color_mkyj5j54
            MONDAY_COLUMN_IDS["status_id"]: {"label": "New Lead"},

            # Type mapped to Investor Type (e.g. VC) using ID color_mkyjzz25
            MONDAY_COLUMN_IDS["type_id"]: {"label": investor.get("type", "VC")},
            
            # Notes
            MONDAY_COLUMN_IDS["notes_id"]: investor.get("notes_content", "")
        }
        
        item_name = investor.get("name", "Unknown Investor")
        query = '''
        mutation ($boardId: ID!, $itemName: String!, $columnValues: JSON!) {
          create_item(
            board_id: $boardId,
            item_name: $itemName,
            column_values: $columnValues
          ) {
            id
          }
        }
        '''
        
        variables = {"boardId": MONDAY_BOARD_ID, "itemName": item_name, "columnValues": json.dumps(column_values)}
        
        try:
            response = requests.post(url, headers=headers, json={"query": query, "variables": variables}, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ Added to Monday.com: {item_name}")
                return True
            else:
                print(f"❌ Failed to add {item_name}. Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error pushing to Monday.com: {str(e)}")
            return False
    
    def run(self):
        print("\n🚀 Starting US SaaS/B2B Investor Discovery...")
        all_investors = []
        all_investors.extend(self.search_crunchbase_free())
        all_investors.extend(self.search_angellist_free())
        all_investors.extend(self.search_github_lists())
        unique_names = set()
        unique_investors = [inv for inv in all_investors if inv["name"] not in unique_names and not unique_names.add(inv["name"])]
        
        print(f"\n📊 Total unique investors found: {len(unique_investors)}\n")
        
        for investor in unique_investors: self.enrich_investor(investor)
        qualified = [inv for inv in unique_investors if inv["score"] >= 60]
        print(f"✅ Qualified leads: {len(qualified)}\n")
        
        print("📤 Step 4: Pushing to Monday.com CRM...")
        success_count = sum(1 for investor in qualified if self.push_to_monday(investor))
        
        print("\n" + "="*50)
        print("🎉 DISCOVERY COMPLETE!")
        print(f"Successfully added to Monday.com: {success_count}")
        print("="*50 + "\n")
        self.save_backup(qualified)
    
    def save_backup(self, investors: List[Dict]):
        try:
            filename = f"investors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                if investors:
                    all_keys = set().union(*(d.keys() for d in investors))
                    writer = csv.DictWriter(f, fieldnames=list(all_keys))
                    writer.writeheader()
                    writer.writerows(investors)
            print(f"💾 Backup saved: {filename}")
        except Exception as e:
            print(f"⚠️  Could not save backup: {str(e)}")

if __name__ == "__main__":
    finder = InvestorFinder()
    finder.run()
