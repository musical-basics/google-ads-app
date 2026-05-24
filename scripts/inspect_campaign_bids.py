"""
Inspect bidding strategy details for campaigns.
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
    
    query = """
        SELECT
            campaign.id,
            campaign.name,
            campaign.bidding_strategy_type,
            campaign.maximize_conversions.target_cpa_micros
        FROM campaign
        WHERE campaign.status = 'ENABLED'
    """
    
    try:
        response = ga_service.search(customer_id=customer_id, query=query)
        for r in response:
            c = r.campaign
            print(f"Campaign: {c.name} (ID: {c.id})")
            print(f"  Bidding Strategy Type: {c.bidding_strategy_type.name}")
            if c.maximize_conversions:
                print(f"  Maximize Conversions Target CPA (micros): {c.maximize_conversions.target_cpa_micros}")
                if c.maximize_conversions.target_cpa_micros > 0:
                    print(f"    -> Target CPA: ${c.maximize_conversions.target_cpa_micros / 1_000_000:.2f}")
                else:
                    print("    -> No Target CPA set (or set to 0)")
            print("-" * 80)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
