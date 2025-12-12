"""
Naistaixi Smart Investor Hunter
Searches broadly, SCORES the results, pushes QUALIFIED leads (>60), AND saves a CSV backup.
"""

import requests
import json
import os
import time
import csv
from datetime import datetime
from duckduckgo_search import DDGS

# --- CONFIGURATION ---
TARGET_SOURCES = [
    {"name": "Crunchbase List", "query": "top 20 SaaS pre-seed VC investors US Crunchbase"},
    {"name": "AngelList",       "query": "active SaaS VCs AngelList Wellfound US"},
    {"name": "General Search",  "query": "best B2B SaaS pre-seed investors United States contact"},
    {"name": "OpenVC",          "query": "OpenVC list SaaS investors US"}
]

MAX_RESULTS_PER_SOURCE = 10 
MIN_SCORE_TO_KEEP = 60 

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
    
    # Negative Keywords
    if "private equity" in text: score -= 20
    if "real estate" in text: score -= 30
    if "crypto" in text: score -= 10
    
    return min(score, 100)

def get_real_investors():
    all_results = []
    print("🚀 Starting Smart Search...")
    
    with DDGS() as ddgs:
        for source in TARGET_SOURCES:
            print(f"🔎 Searching: {source['query']}...")
            try:
                search_results = list(ddgs.text(source['query'], max_results=MAX
