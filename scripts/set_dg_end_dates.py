"""Set end_date = 2026-06-10 on the 3 Demand Gen campaigns that were
created without one (concert is 2026-06-11). The YT campaigns already
have this set correctly. Without it, the DGs would keep running and
billing after the concert ends.

Dry-run by default. Pass --apply to write.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env.local")

from google.protobuf import field_mask_pb2
from api._lib.google_ads_client import get_client, customer_id

TARGETS = [
    (23871037379, "Belgium Concert - New Creative (May 2026)"),
    (23875661669, "Belgium Concert - Original Creative (May 2026)"),
    (23888155116, "Belgium Concert - Official Trailer (May 2026)"),
]
END_DATE = "2026-06-10 23:59:59"  # v24 uses end_date_time (datetime), not end_date

apply = "--apply" in sys.argv
client = get_client()
cid = customer_id()
svc = client.get_service("GoogleAdsService")
camp_svc = client.get_service("CampaignService")

# Read current state
ids_csv = ",".join(str(t[0]) for t in TARGETS)
q = f"""
SELECT campaign.id, campaign.name, campaign.status, campaign.end_date_time,
       campaign.resource_name
FROM campaign WHERE campaign.id IN ({ids_csv})
"""
state = {}
for r in svc.search(customer_id=cid, query=q):
    state[r.campaign.id] = {
        "name": r.campaign.name,
        "status": r.campaign.status.name,
        "end_date": r.campaign.end_date_time,
        "resource_name": r.campaign.resource_name,
    }

print(f"=== Plan ({'APPLY' if apply else 'DRY RUN'}) ===\n")
print(f"{'CAMPAIGN':<48} {'STATUS':<10} {'CURRENT END':<14} {'NEW END':<12}")
print("-" * 90)
for cid_, name in TARGETS:
    s = state.get(cid_)
    if not s:
        print(f"  [{cid_}] NOT FOUND")
        continue
    cur = s["end_date"] or "(none)"
    print(f"  {s['name'][:46]:<48} {s['status']:<10} {cur:<14} {END_DATE:<12}")

if not apply:
    print("\nDry run. Re-run with --apply to write.")
    sys.exit(0)

ops = []
for cid_, _ in TARGETS:
    if cid_ not in state:
        continue
    op = client.get_type("CampaignOperation")
    op.update.resource_name = state[cid_]["resource_name"]
    op.update.end_date_time = END_DATE
    op.update_mask.CopyFrom(field_mask_pb2.FieldMask(paths=["end_date_time"]))
    ops.append(op)

resp = camp_svc.mutate_campaigns(customer_id=cid, operations=ops)
print(f"\nUpdated {len(resp.results)} campaigns.")

# Verify
print("\n=== Post-change state ===")
for r in svc.search(customer_id=cid, query=q):
    print(f"  [{r.campaign.id}] {r.campaign.name}  status={r.campaign.status.name}  end_date={r.campaign.end_date_time}")
