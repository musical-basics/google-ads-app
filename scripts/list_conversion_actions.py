"""List all conversion actions on the account, plus which one fired today
and the per-action value attached to today's conversions."""
import sys
from pathlib import Path
from datetime import date
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env.local")

from api._lib.google_ads_client import get_client, customer_id

client = get_client()
svc = client.get_service("GoogleAdsService")
cid = customer_id()

print("=== All conversion actions configured on this account ===\n")
q = """
SELECT
    conversion_action.id,
    conversion_action.name,
    conversion_action.status,
    conversion_action.type,
    conversion_action.category,
    conversion_action.primary_for_goal,
    conversion_action.counting_type,
    conversion_action.include_in_conversions_metric,
    conversion_action.value_settings.default_value,
    conversion_action.value_settings.default_currency_code,
    conversion_action.value_settings.always_use_default_value
FROM conversion_action
WHERE conversion_action.status != 'REMOVED'
ORDER BY conversion_action.name
"""
for r in svc.search(customer_id=cid, query=q):
    ca = r.conversion_action
    vs = ca.value_settings
    primary = "PRIMARY" if ca.primary_for_goal else "secondary"
    print(f"  [{ca.id}] {ca.name}")
    print(f"      status={ca.status.name}  type={ca.type.name}  category={ca.category.name}")
    print(f"      counting={ca.counting_type.name}  include_in_conv_metric={ca.include_in_conversions_metric}  {primary}")
    print(f"      default_value={vs.default_value} {vs.default_currency_code}  always_use_default={vs.always_use_default_value}")
    print()

print("\n=== Today's conversions, broken out by action ===\n")
today = date.today().isoformat()
q2 = f"""
SELECT
    campaign.name,
    segments.conversion_action_name,
    metrics.all_conversions,
    metrics.all_conversions_value,
    metrics.conversions,
    metrics.conversions_value
FROM campaign
WHERE segments.date = '{today}'
  AND metrics.all_conversions > 0
"""
any_rows = False
for r in svc.search(customer_id=cid, query=q2):
    any_rows = True
    print(f"  {r.campaign.name[:40]:<40}  action={r.segments.conversion_action_name}")
    print(f"      all_conv={r.metrics.all_conversions}  all_value={r.metrics.all_conversions_value}")
    print(f"      conv={r.metrics.conversions}  value={r.metrics.conversions_value}")
if not any_rows:
    print("  (no rows)")
