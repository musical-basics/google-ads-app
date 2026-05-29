"""Print campaign + ad group status given a gad_adgroupid (or all groups in
a campaign if --campaign is passed)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env.local")

from api._lib.google_ads_client import get_client, customer_id

client = get_client()
svc = client.get_service("GoogleAdsService")
cid = customer_id()

ad_group_id = sys.argv[1] if len(sys.argv) > 1 else "195520511703"

q = f"""
SELECT
    campaign.id, campaign.name, campaign.status,
    ad_group.id, ad_group.name, ad_group.status
FROM ad_group
WHERE ad_group.id = {ad_group_id}
"""
for r in svc.search(customer_id=cid, query=q):
    print(f"Campaign: [{r.campaign.id}] {r.campaign.name}  status={r.campaign.status.name}")
    print(f"Ad group: [{r.ad_group.id}] {r.ad_group.name}    status={r.ad_group.status.name}")

# Also show all ad groups under the same campaign for context
camp_id = 23875661669
print(f"\nAll ad groups under campaign {camp_id}:")
q2 = f"""
SELECT ad_group.id, ad_group.name, ad_group.status
FROM ad_group
WHERE campaign.id = {camp_id}
ORDER BY ad_group.id
"""
for r in svc.search(customer_id=cid, query=q2):
    print(f"  [{r.ad_group.id}] {r.ad_group.name}    status={r.ad_group.status.name}")
