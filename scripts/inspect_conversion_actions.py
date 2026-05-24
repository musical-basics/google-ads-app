"""
Query and list conversion actions in the account.
"""
import os
import sys

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
    ga_service = client.get_service("GoogleAdsService")
    
    print("=" * 80)
    print(f"Inspecting Conversion Actions for Customer ID: {customer_id}")
    print("=" * 80)
    
    query = """
        SELECT
            conversion_action.id,
            conversion_action.name,
            conversion_action.type,
            conversion_action.status,
            conversion_action.category
        FROM conversion_action
    """
    
    try:
        response = ga_service.search(customer_id=customer_id, query=query)
        for r in response:
            ca = r.conversion_action
            print(f"Name: {ca.name}")
            print(f"  ID: {ca.id}")
            print(f"  Type: {ca.type_.name}")
            print(f"  Status: {ca.status.name}")
            print(f"  Category: {ca.category.name}")
            print("-" * 80)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
