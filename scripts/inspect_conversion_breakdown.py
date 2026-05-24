"""
Break down campaign conversions by conversion action.
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
    print(f"Conversion Breakdown for Customer ID: {customer_id}")
    print("=" * 80)
    
    query = """
        SELECT
            campaign.id,
            campaign.name,
            segments.conversion_action,
            segments.conversion_action_category,
            segments.conversion_action_name,
            metrics.conversions,
            metrics.all_conversions
        FROM campaign
        WHERE campaign.status = 'ENABLED'
          AND metrics.all_conversions > 0
    """
    
    try:
        response = ga_service.search(customer_id=customer_id, query=query)
        for r in response:
            c = r.campaign
            seg = r.segments
            m = r.metrics
            print(f"Campaign: {c.name} (ID: {c.id})")
            print(f"  Conversion Action: {seg.conversion_action_name}")
            print(f"  Category: {seg.conversion_action_category.name}")
            print(f"  Conversions (Primary): {m.conversions:.2f}")
            print(f"  All Conversions (Incl. Secondary): {m.all_conversions:.2f}")
            print("-" * 80)
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
