import os
import sys
from dotenv import load_dotenv
from google.ads.googleads.client import GoogleAdsClient
from google.api_core import protobuf_helpers

load_dotenv(".env.local")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "api"))

from _lib import google_ads_client
client = google_ads_client.get_client()
cid = google_ads_client.customer_id()
ga_service = client.get_service("GoogleAdsService")
ad_group_service = client.get_service("AdGroupService")

query = """
    SELECT
        ad_group.id,
        ad_group.name,
        ad_group.cpv_bid_micros
    FROM ad_group
    WHERE campaign.name IN ('belgium_new_creative_yt', 'belgium_original_yt')
"""
try:
    rows = ga_service.search(customer_id=cid, query=query)
    operations = []
    
    for r in rows:
        ag_id = r.ad_group.id
        # Double the bid, or set to $0.20 (200000 micros)
        # We will just set it to 200000 explicitly which is $0.20
        new_cpv = 200000
        
        op = client.get_type("AdGroupOperation")
        ag = op.update
        ag.resource_name = ad_group_service.ad_group_path(cid, ag_id)
        ag.cpv_bid_micros = new_cpv
        
        client.copy_from(op.update_mask, protobuf_helpers.field_mask(None, ag._pb))
        operations.append(op)
        
    print(f"Updating {len(operations)} ad groups to $0.20 Target CPV...")
    if operations:
        response = ad_group_service.mutate_ad_groups(customer_id=cid, operations=operations)
        for result in response.results:
            print(f"✅ Updated ad group: {result.resource_name}")
except Exception as e:
    print(f"Error: {e}")
