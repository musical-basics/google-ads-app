"""
Update existing ad groups with ValueTrack suffixes.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "api"))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(HERE, "..", ".env.local"))
    print("✓ Loaded .env.local")
except ImportError:
    pass

from google.protobuf import field_mask_pb2
from api._lib import google_ads_client, config

def main():
    client = google_ads_client.get_client()
    cid = google_ads_client.customer_id()
    ag_service = client.get_service("AdGroupService")

    ad_group_suffixes = {
        config.AG2_SUBSCRIBERS: config.FINAL_URL_SUFFIX[config.AG2_SUBSCRIBERS],
        config.AG2_VIEWERS:     config.FINAL_URL_SUFFIX[config.AG2_VIEWERS],
        config.AG3_SUBSCRIBERS: config.FINAL_URL_SUFFIX[config.AG3_SUBSCRIBERS],
        config.AG3_VIEWERS:     config.FINAL_URL_SUFFIX[config.AG3_VIEWERS],
    }

    print("\n── Updating final_url_suffix on active ad groups ──")
    for ag_id, suffix in ad_group_suffixes.items():
        resource_name = f"customers/{cid}/adGroups/{ag_id}"
        print(f"Updating {resource_name}...")
        print(f"  New Suffix: {suffix}")
        
        op = client.get_type("AdGroupOperation")
        ag = op.update
        ag.resource_name = resource_name
        ag.final_url_suffix = suffix
        
        fm = field_mask_pb2.FieldMask(paths=["final_url_suffix"])
        op.update_mask.CopyFrom(fm)
        
        try:
            resp = ag_service.mutate_ad_groups(customer_id=cid, operations=[op])
            print(f"  ✓ Success: {resp.results[0].resource_name}")
        except Exception as e:
            print(f"  ✗ Failed to update ad group {ag_id}: {e}")
            
    print("\n✅ ValueTrack suffix updates complete!\n")

if __name__ == "__main__":
    main()
