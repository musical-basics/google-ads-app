"""
Inspect the exact configuration of targeted Audience resources.
"""
import os
import sys

# Add standard library paths
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
    print(f"Inspecting Audience Definitions for Customer ID: {customer_id}")
    print("=" * 80)
    
    query = """
        SELECT
            audience.id,
            audience.name,
            audience.status,
            audience.description,
            audience.dimensions
        FROM audience
    """
    
    try:
        response = ga_service.search(customer_id=customer_id, query=query)
        for r in response:
            aud = r.audience
            print(f"Audience Name: {aud.name}")
            print(f"  ID: {aud.id}")
            print(f"  Status: {aud.status.name}")
            print(f"  Description: {aud.description}")
            print("  Definition Protobuf:")
            # Use string representation of the protobuf object
            print(aud)
            print("=" * 80)
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
