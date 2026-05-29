"""One-shot ad changes requested 2026-05-29:
  1. Pause campaign 'belgium_new_creative_yt with cold audience'
  2. Pause campaign 'belgium_new_creative_yt diaspora_fans'
  3. Double the daily budget of the two Demand Gen campaigns:
       - Belgium Concert - New Creative (May 2026)
       - Belgium Concert - Original Creative (May 2026)

Dry-run by default. Pass --apply to actually write.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env.local")

from google.protobuf import field_mask_pb2
from api._lib.google_ads_client import get_client, customer_id

apply = "--apply" in sys.argv

PAUSE_IDS = {
    23875386621: "belgium_new_creative_yt with cold audience",
    23884972699: "belgium_new_creative_yt diaspora_fans",
}
DOUBLE_BUDGET_IDS = {
    23871037379: "Belgium Concert - New Creative (May 2026)",
    23875661669: "Belgium Concert - Original Creative (May 2026)",
}

client = get_client()
svc = client.get_service("GoogleAdsService")
camp_svc = client.get_service("CampaignService")
budget_svc = client.get_service("CampaignBudgetService")
cid = customer_id()

# 1. Read current state for everything we're going to touch.
all_ids = list(PAUSE_IDS.keys()) + list(DOUBLE_BUDGET_IDS.keys())
ids_csv = ",".join(str(i) for i in all_ids)
q = f"""
SELECT campaign.id, campaign.name, campaign.status,
       campaign.resource_name, campaign_budget.resource_name,
       campaign_budget.amount_micros, campaign_budget.name
FROM campaign
WHERE campaign.id IN ({ids_csv})
"""
state = {}
for r in svc.search(customer_id=cid, query=q):
    state[r.campaign.id] = {
        "name": r.campaign.name,
        "status": r.campaign.status.name,
        "campaign_resource": r.campaign.resource_name,
        "budget_resource": r.campaign_budget.resource_name,
        "budget_micros": r.campaign_budget.amount_micros,
        "budget_name": r.campaign_budget.name,
    }

print(f"=== Plan {'(APPLY)' if apply else '(DRY RUN)'} ===\n")
print("Pauses:")
for cid_, label in PAUSE_IDS.items():
    s = state.get(cid_)
    if not s:
        print(f"  [{cid_}] {label} — NOT FOUND")
        continue
    print(f"  [{cid_}] {s['name']}: {s['status']} -> PAUSED")
print("\nBudget doubles:")
for cid_, label in DOUBLE_BUDGET_IDS.items():
    s = state.get(cid_)
    if not s:
        print(f"  [{cid_}] {label} — NOT FOUND")
        continue
    cur_eur = s["budget_micros"] / 1_000_000
    new_eur = cur_eur * 2
    print(f"  [{cid_}] {s['name']}: EUR{cur_eur:.2f}/day -> EUR{new_eur:.2f}/day  (budget='{s['budget_name']}')")

if not apply:
    print("\nDRY RUN. Re-run with --apply to write.")
    sys.exit(0)

# 2. Apply pauses
pause_ops = []
for cid_ in PAUSE_IDS:
    if cid_ not in state:
        continue
    op = client.get_type("CampaignOperation")
    op.update.resource_name = state[cid_]["campaign_resource"]
    op.update.status = client.enums.CampaignStatusEnum.PAUSED
    op.update_mask.CopyFrom(field_mask_pb2.FieldMask(paths=["status"]))
    pause_ops.append(op)

if pause_ops:
    try:
        res = camp_svc.mutate_campaigns(customer_id=cid, operations=pause_ops)
        print(f"\nPaused {len(res.results)} campaigns:")
        for r in res.results:
            print(f"  {r.resource_name}")
    except Exception as e:
        # Google retired API mutation for legacy VIDEO campaigns; fall through
        # to budget changes anyway and tell the user to pause in the UI.
        msg = str(e)
        if "MUTATE_NOT_ALLOWED" in msg and "VIDEO" in msg:
            print("\nPAUSE FAILED: Google Ads no longer allows API mutations on")
            print("legacy VIDEO campaign type. Pause these two in the UI manually:")
            for cid_, label in PAUSE_IDS.items():
                print(f"  - [{cid_}] {label}")
        else:
            raise

# 3. Apply budget doubles. Budgets are separate resources; one budget per campaign here.
budget_ops = []
for cid_ in DOUBLE_BUDGET_IDS:
    if cid_ not in state:
        continue
    op = client.get_type("CampaignBudgetOperation")
    op.update.resource_name = state[cid_]["budget_resource"]
    op.update.amount_micros = state[cid_]["budget_micros"] * 2
    op.update_mask.CopyFrom(field_mask_pb2.FieldMask(paths=["amount_micros"]))
    budget_ops.append(op)

if budget_ops:
    res = budget_svc.mutate_campaign_budgets(customer_id=cid, operations=budget_ops)
    print(f"\nDoubled {len(res.results)} budgets:")
    for r in res.results:
        print(f"  {r.resource_name}")

# 4. Verify
print("\n=== Post-change state ===")
for r in svc.search(customer_id=cid, query=q):
    eur = r.campaign_budget.amount_micros / 1_000_000
    print(f"  [{r.campaign.id}] {r.campaign.name}")
    print(f"      status={r.campaign.status.name}  budget=EUR{eur:.2f}/day")
