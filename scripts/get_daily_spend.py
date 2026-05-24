"""
Pull daily spend and performance for all campaigns over the last 14 days.
"""
import os
import sys
from datetime import datetime, date as date_cls, timedelta

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
    
    end_date = date_cls.today()
    start_date = end_date - timedelta(days=14)
    
    print("=" * 80)
    print(f"Daily Spend Report ({start_date} to {end_date})")
    print("=" * 80)
    
    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            segments.date,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions
        FROM campaign
        WHERE campaign.status = 'ENABLED'
            AND segments.date >= '{start_date.isoformat()}'
            AND segments.date <= '{end_date.isoformat()}'
        ORDER BY segments.date DESC, campaign.name ASC
    """
    
    try:
        response = ga_service.search(customer_id=customer_id, query=query)
        rows = list(response)
        
        if not rows:
            print("No performance data found for the last 14 days.")
            return
            
        print(f"{'Date':12} | {'Campaign Name':40} | {'Imps':6} | {'Clicks':6} | {'Cost':8} | {'Convs':5}")
        print("-" * 88)
        
        for r in rows:
            cost = r.metrics.cost_micros / 1_000_000
            print(f"{r.segments.date:12} | {r.campaign.name[:40]:40} | {r.metrics.impressions:6} | {r.metrics.clicks:6} | ${cost:7.2f} | {r.metrics.conversions:5.1f}")
            
    except Exception as e:
        print(f"Error querying Google Ads API: {e}")

if __name__ == "__main__":
    main()
