"""
Detailed audit of all campaigns, ad groups, criteria, bid strategies, and performance metrics.
"""
import os
import sys
from datetime import datetime, timedelta

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
    
    print("=" * 100)
    print(f"GOOGLE ADS COMPREHENSIVE AUDIT FOR CUSTOMER ID: {customer_id}")
    print("=" * 100)
    
    # 1. Query Campaign Details & Metrics (Last 14 days)
    # We query campaign_criterion and ad_group separately to avoid Cartesian product size limits if needed.
    campaign_query = """
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.primary_status,
            campaign.advertising_channel_type,
            campaign.bidding_strategy_type,
            campaign_budget.amount_micros,
            campaign.network_settings.target_google_search,
            campaign.network_settings.target_search_network,
            campaign.network_settings.target_content_network,
            campaign.network_settings.target_partner_search_network,
            campaign.network_settings.target_youtube,
            metrics.impressions,
            metrics.clicks,
            metrics.interactions,
            metrics.cost_micros,
            metrics.conversions
        FROM campaign
        WHERE campaign.status = 'ENABLED'
    """
    
    try:
        response = ga_service.search(customer_id=customer_id, query=campaign_query)
        campaigns = list(response)
        
        print(f"\nFound {len(campaigns)} ENABLED Campaigns:")
        print("-" * 100)
        
        for row in campaigns:
            c = row.campaign
            b = row.campaign_budget
            m = row.metrics
            
            print(f"Campaign: {c.name} (ID: {c.id})")
            print(f"  Status: {c.status.name}")
            print(f"  Primary Status: {c.primary_status.name}")
            print(f"  Channel Type: {c.advertising_channel_type.name}")
            print(f"  Bidding Strategy Type: {c.bidding_strategy_type.name}")
            print(f"  Daily Budget: ${b.amount_micros / 1_000_000:.2f}")
            print(f"  Networks:")
            print(f"    - Target Google Search: {c.network_settings.target_google_search}")
            print(f"    - Target Search Network: {c.network_settings.target_search_network}")
            print(f"    - Target Content Network (Display): {c.network_settings.target_content_network}")
            print(f"    - Target Partner Search Network: {c.network_settings.target_partner_search_network}")
            print(f"    - Target YouTube: {c.network_settings.target_youtube}")
            
            # Metrics (all time or since creation)
            print(f"  Lifetime Metrics:")
            print(f"    - Impressions: {m.impressions}")
            print(f"    - Clicks: {m.clicks}")
            print(f"    - Interactions/Views: {m.interactions}")
            print(f"    - Cost: ${m.cost_micros / 1_000_000:.2f}")
            print(f"    - Conversions: {m.conversions:.2f}")
            if m.clicks > 0:
                print(f"    - Avg CPC: ${m.cost_micros / m.clicks / 1_000_000:.2f}")
            if m.interactions > 0:
                print(f"    - Avg CPV/Engagement: ${m.cost_micros / m.interactions / 1_000_000:.2f}")
            
            # Query Geo and Language criteria for this campaign
            crit_query = f"""
                SELECT
                    campaign_criterion.criterion_id,
                    campaign_criterion.type,
                    campaign_criterion.status,
                    campaign_criterion.location.geo_target_constant,
                    campaign_criterion.language.language_constant
                FROM campaign_criterion
                WHERE campaign.id = {c.id}
            """
            crit_resp = ga_service.search(customer_id=customer_id, query=crit_query)
            locations = []
            languages = []
            for cr in crit_resp:
                cc = cr.campaign_criterion
                if cc.type.name == "LOCATION":
                    locations.append(cc.location.geo_target_constant.split("/")[-1])
                elif cc.type.name == "LANGUAGE":
                    languages.append(cc.language.language_constant.split("/")[-1])
            
            print(f"  Targeted Location IDs: {locations}")
            print(f"  Targeted Language IDs: {languages}")
            
            # Query Ad Groups in this campaign
            ag_query = f"""
                SELECT
                    ad_group.id,
                    ad_group.name,
                    ad_group.status,
                    ad_group.type,
                    ad_group.target_cpv_micros,
                    ad_group.cpc_bid_micros,
                    ad_group.target_cpm_micros,
                    ad_group.target_cpa_micros
                FROM ad_group
                WHERE campaign.id = {c.id}
            """
            ag_resp = ga_service.search(customer_id=customer_id, query=ag_query)
            print("  Ad Groups:")
            for agr in ag_resp:
                ag = agr.ad_group
                print(f"    - Ad Group: {ag.name} (ID: {ag.id}) [Status: {ag.status.name}]")
                print(f"      Type: {ag.type_.name}")
                if ag.target_cpv_micros:
                    print(f"      Target CPV: ${ag.target_cpv_micros / 1_000_000:.4f}")
                if ag.cpc_bid_micros:
                    print(f"      CPC Bid: ${ag.cpc_bid_micros / 1_000_000:.2f}")
                if ag.target_cpa_micros:
                    print(f"      Target CPA: ${ag.target_cpa_micros / 1_000_000:.2f}")
                if ag.target_cpm_micros:
                    print(f"      Target CPM: ${ag.target_cpm_micros / 1_000_000:.2f}")
                
                # Check Ad Group Criteria (Targeted Audiences / Lists)
                agc_query = f"""
                    SELECT
                        ad_group_criterion.criterion_id,
                        ad_group_criterion.type,
                        ad_group_criterion.status,
                        ad_group_criterion.audience.audience,
                        ad_group_criterion.user_list.user_list,
                        ad_group_criterion.custom_audience.custom_audience
                    FROM ad_group_criterion
                    WHERE ad_group.id = {ag.id}
                """
                agc_resp = ga_service.search(customer_id=customer_id, query=agc_query)
                has_criteria = False
                for agcr in agc_resp:
                    has_criteria = True
                    agc = agcr.ad_group_criterion
                    print(f"      Criterion ID: {agc.criterion_id} [Status: {agc.status.name}, Type: {agc.type_.name}]")
                    if agc.audience.audience:
                        print(f"        Audience Resource: {agc.audience.audience}")
                    if agc.user_list.user_list:
                        print(f"        UserList Resource: {agc.user_list.user_list}")
                    if agc.custom_audience.custom_audience:
                        print(f"        CustomAudience Resource: {agc.custom_audience.custom_audience}")
                if not has_criteria:
                    print("      Criterion: NONE (Broad targeting or demographic only)")
                    
            print("-" * 100)
            
    except Exception as e:
        print(f"Error querying Google Ads: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
