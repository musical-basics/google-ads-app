"""
Inspect the size and status of user lists (audiences) targeted in the campaigns.
"""
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "api"))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(HERE, "..", ".env.local"))
except ImportError:
    pass

from api._lib import google_ads_client

def main():
    client = google_ads_client.get_client()
    customer_id = google_ads_client.customer_id()
    
    print("=" * 80)
    print(f"Inspecting User Lists for Customer ID: {customer_id}")
    print("=" * 80)
    
    ga_service = client.get_service("GoogleAdsService")
    
    query = """
        SELECT
            user_list.id,
            user_list.name,
            user_list.membership_status,
            user_list.size_for_search,
            user_list.size_range_for_search,
            user_list.size_for_display,
            user_list.size_range_for_display
        FROM user_list
    """
    
    try:
        response = ga_service.search(customer_id=customer_id, query=query)
        rows = list(response)
        
        print(f"Found {len(rows)} User Lists:")
        print("-" * 80)
        
        for r in rows:
            print(f"Name: {r.user_list.name}")
            print(f"  ID: {r.user_list.id}")
            print(f"  Membership Status: {r.user_list.membership_status.name}")
            print(f"  Size for Search:  {r.user_list.size_for_search} (Range: {r.user_list.size_range_for_search.name})")
            print(f"  Size for Display: {r.user_list.size_for_display} (Range: {r.user_list.size_range_for_display.name})")
            print("-" * 80)
            
    except Exception as e:
        print(f"Error querying Google Ads API: {e}")

if __name__ == "__main__":
    main()
