"""EMERGENCY: pause all 3 DG campaigns immediately. They've been running
post-concert (June 11) because no end date was set on creation. Also set
end_date_time to today end-of-day so they can't accidentally re-enable."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path('/Users/lionelyu/Documents/New Version/google-ads-app')))
from dotenv import load_dotenv
load_dotenv('/Users/lionelyu/Documents/New Version/google-ads-app/.env.local')

from google.protobuf import field_mask_pb2
from api._lib.google_ads_client import get_client, customer_id

client = get_client()
cid = customer_id()
camp_svc = client.get_service('CampaignService')
svc = client.get_service('GoogleAdsService')

TARGETS = [
    (23871037379, "Belgium Concert - New Creative (May 2026)"),
    (23875661669, "Belgium Concert - Original Creative (May 2026)"),
    (23888155116, "Belgium Concert - Official Trailer (May 2026)"),
]

# Step 1: pause them all
ops = []
for cid_, _ in TARGETS:
    op = client.get_type("CampaignOperation")
    op.update.resource_name = f"customers/{cid}/campaigns/{cid_}"
    op.update.status = client.enums.CampaignStatusEnum.PAUSED
    op.update_mask.CopyFrom(field_mask_pb2.FieldMask(paths=["status"]))
    ops.append(op)

try:
    resp = camp_svc.mutate_campaigns(customer_id=cid, operations=ops)
    print(f"Paused {len(resp.results)} campaigns:")
    for r in resp.results:
        print(f"  {r.resource_name}")
except Exception as e:
    print(f"PAUSE FAILED: {str(e).splitlines()[-1][:300]}")

# Step 2: also set end_date_time to today 23:59:59 so they can't run again
ops2 = []
for cid_, _ in TARGETS:
    op = client.get_type("CampaignOperation")
    op.update.resource_name = f"customers/{cid}/campaigns/{cid_}"
    op.update.end_date_time = "2026-06-13 23:59:59"
    op.update_mask.CopyFrom(field_mask_pb2.FieldMask(paths=["end_date_time"]))
    ops2.append(op)

try:
    resp = camp_svc.mutate_campaigns(customer_id=cid, operations=ops2)
    print(f"\nSet end_date_time on {len(resp.results)} campaigns to 2026-06-13 23:59:59")
except Exception as e:
    print(f"\nEND DATE FAILED: {str(e).splitlines()[-1][:300]}")

# Step 3: verify
print("\n=== Post-change state ===")
ids_csv = ",".join(str(t[0]) for t in TARGETS)
for r in svc.search(customer_id=cid, query=f"""
SELECT campaign.id, campaign.name, campaign.status, campaign.end_date_time
FROM campaign WHERE campaign.id IN ({ids_csv})
"""):
    print(f"  [{r.campaign.id}] {r.campaign.name[:46]:<48} status={r.campaign.status.name:<8} end_date={r.campaign.end_date_time}")
