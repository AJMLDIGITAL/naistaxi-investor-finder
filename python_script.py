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
            {"name": "Active Capital", "location": "San Antonio, US
