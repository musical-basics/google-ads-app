"""Demote 'CTA Click' from a primary conversion action to a secondary one
so bidding (maximize_conversions) stops optimizing for landing-page CTA
clicks and only counts real purchases / waitlist signups.

Sets:
  primary_for_goal: True  -> False

Leaves include_in_conversions_metric=True for now so historical reports
still show CTA clicks; we can flip that too if needed.

Run with --apply to write. Without --apply, prints the planned change only.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env.local")

from google.protobuf import field_mask_pb2

from api._lib.google_ads_client import get_client, customer_id

CONV_ACTION_ID = "7621781246"  # CTA Click

apply = "--apply" in sys.argv

client = get_client()
svc = client.get_service("GoogleAdsService")
cid = customer_id()

# Read current state
q = f"""
SELECT
    conversion_action.id,
    conversion_action.name,
    conversion_action.resource_name,
    conversion_action.primary_for_goal,
    conversion_action.include_in_conversions_metric,
    conversion_action.status,
    conversion_action.category
FROM conversion_action
WHERE conversion_action.id = {CONV_ACTION_ID}
"""
row = None
for r in svc.search(customer_id=cid, query=q):
    row = r
if row is None:
    print(f"conversion action {CONV_ACTION_ID} not found")
    sys.exit(1)

ca = row.conversion_action
print(f"Current state of [{ca.id}] {ca.name}:")
print(f"  primary_for_goal              = {ca.primary_for_goal}")
print(f"  include_in_conversions_metric = {ca.include_in_conversions_metric}")
print(f"  category                      = {ca.category.name}")
print(f"  status                        = {ca.status.name}")
print(f"  resource_name                 = {ca.resource_name}")
print()

if ca.primary_for_goal is False:
    print("Already secondary - nothing to do.")
    sys.exit(0)

if not apply:
    print("DRY RUN. Would set primary_for_goal=False. Re-run with --apply to write.")
    sys.exit(0)

ca_service = client.get_service("ConversionActionService")
op = client.get_type("ConversionActionOperation")
upd = op.update
upd.resource_name = ca.resource_name
upd.primary_for_goal = False
op.update_mask.CopyFrom(field_mask_pb2.FieldMask(paths=["primary_for_goal"]))

resp = ca_service.mutate_conversion_actions(customer_id=cid, operations=[op])
print(f"Updated: {resp.results[0].resource_name}")

# Verify
for r in svc.search(customer_id=cid, query=q):
    print(f"\nNew primary_for_goal = {r.conversion_action.primary_for_goal}")
