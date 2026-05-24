"""
Inspect the status and policy details of all ads in enabled campaigns.
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
    print(f"Inspecting Ads for Customer ID: {customer_id}")
    print("=" * 80)
    
    ga_service = client.get_service("GoogleAdsService")
    
    # Query ad group ad status and policy summaries
    query = """
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            ad_group.id,
            ad_group.name,
            ad_group.status,
            ad_group_ad.ad.id,
            ad_group_ad.ad.name,
            ad_group_ad.status,
            ad_group_ad.policy_summary.approval_status,
            ad_group_ad.policy_summary.policy_topic_entries
        FROM ad_group_ad
        WHERE campaign.status = 'ENABLED'
    """
    
    try:
        response = ga_service.search(customer_id=customer_id, query=query)
        rows = list(response)
        
        print(f"Found {len(rows)} ads across enabled campaigns:")
        print("-" * 80)
        
        campaign_summary = {}
        
        for row in rows:
            camp_name = row.campaign.name
            camp_id = row.campaign.id
            ag_name = row.ad_group.name
            ag_status = row.ad_group.status.name
            ad_id = row.ad_group_ad.ad.id
            ad_name = row.ad_group_ad.ad.name
            ad_status = row.ad_group_ad.status.name
            approval_status = row.ad_group_ad.policy_summary.approval_status.name
            
            # Print details
            print(f"Campaign: {camp_name} (ID: {camp_id})")
            print(f"  Ad Group: {ag_name} [Status: {ag_status}]")
            print(f"  Ad: {ad_name} [Status: {ad_status}]")
            print(f"  Approval Status: {approval_status}")
            
            policy_topics = row.ad_group_ad.policy_summary.policy_topic_entries
            if policy_topics:
                print("  Policy Issues:")
                for topic in policy_topics:
                    print(f"    - Topic: {topic.topic} (Type: {topic.type_.name})")
                    for evidence in topic.evidences:
                        print(f"      Evidence: {evidence}")
            print("-" * 80)
            
            # Aggregate status counts
            camp_key = f"{camp_name} ({camp_id})"
            if camp_key not in campaign_summary:
                campaign_summary[camp_key] = {"enabled_ads": 0, "approved_ads": 0, "disapproved_ads": 0, "total_ads": 0}
            
            campaign_summary[camp_key]["total_ads"] += 1
            if ad_status == "ENABLED" and ag_status == "ENABLED":
                campaign_summary[camp_key]["enabled_ads"] += 1
            if approval_status in ("APPROVED", "APPROVED_LIMITED"):
                campaign_summary[camp_key]["approved_ads"] += 1
            elif approval_status == "DISAPPROVED":
                campaign_summary[camp_key]["disapproved_ads"] += 1
                
        print("\nSUMMARY:")
        for camp_key, stats in campaign_summary.items():
            print(f"Campaign {camp_key}:")
            print(f"  Total Ads: {stats['total_ads']}")
            print(f"  Active (Enabled) Ads: {stats['enabled_ads']}")
            print(f"  Approved Ads: {stats['approved_ads']}")
            print(f"  Disapproved Ads: {stats['disapproved_ads']}")
            if stats['enabled_ads'] == 0:
                print("  ⚠️ WARNING: No enabled ads are running in this campaign!")
            if stats['approved_ads'] == 0 and stats['total_ads'] > 0:
                print("  ❌ ERROR: No ads are approved in this campaign!")
                
    except Exception as e:
        print(f"Error querying Google Ads API: {e}")

if __name__ == "__main__":
    main()
