"""Check whether Google Ads itself records any view-through conversions
for the belgium_new_creative_dg campaign around 2026-05-26, which would
support the other AI's claim that hiamusic was a view-through buyer."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env.local")

from api._lib.google_ads_client import get_client, customer_id

client = get_client()
svc = client.get_service("GoogleAdsService")
cid = customer_id()

# 1. Resolve "belgium_new_creative_dg" -> Google Ads campaign id by name match
print("=== Campaigns matching 'new creative' (looking for the DG variant) ===\n")
q = """
SELECT campaign.id, campaign.name, campaign.status,
       campaign.advertising_channel_type, campaign.advertising_channel_sub_type
FROM campaign
WHERE campaign.status != 'REMOVED'
"""
candidate_ids = []
for r in svc.search(customer_id=cid, query=q):
    print(f"  [{r.campaign.id}] {r.campaign.name}")
    print(f"      channel={r.campaign.advertising_channel_type.name}  sub={r.campaign.advertising_channel_sub_type.name}  status={r.campaign.status.name}")
    candidate_ids.append((r.campaign.id, r.campaign.name))

# 2. For each candidate, pull conv breakdown on 2026-05-26 segmented by conversion action.
#    Includes BOTH click-through (metrics.conversions) AND view-through (metrics.view_through_conversions).
print("\n=== Conversions on 2026-05-26 by campaign + action (incl. view-through) ===\n")
print(f"{'CAMPAIGN':<48} {'ACTION':<35} {'CLICK_CONV':>11} {'VIEW_THRU':>10} {'ALL_CONV':>9} {'ALL_VAL':>10}")
print("-" * 130)
for cmp_id, cmp_name in candidate_ids:
    q2 = f"""
    SELECT
        campaign.name,
        segments.conversion_action_name,
        metrics.conversions,
        metrics.view_through_conversions,
        metrics.all_conversions,
        metrics.all_conversions_value
    FROM campaign
    WHERE campaign.id = {cmp_id}
      AND segments.date = '2026-05-26'
    """
    any_row = False
    for r in svc.search(customer_id=cid, query=q2):
        any_row = True
        n = (r.campaign.name or "")[:46]
        a = (r.segments.conversion_action_name or "?")[:33]
        print(f"  {n:<48} {a:<35} {r.metrics.conversions:>11.2f} {r.metrics.view_through_conversions:>10} {r.metrics.all_conversions:>9.2f} EUR{r.metrics.all_conversions_value:>6.2f}")
    if not any_row:
        print(f"  {cmp_name[:46]:<48} (no conversions on 2026-05-26)")

# 3. Same query for 2026-05-25 + 2026-05-26 (catches view-through with a 24-48h
#    impression-to-conversion window).
print("\n=== Same, but 2026-05-24..27 (in case impression preceded purchase by hours/days) ===\n")
for cmp_id, cmp_name in candidate_ids:
    q3 = f"""
    SELECT
        segments.date,
        segments.conversion_action_name,
        metrics.view_through_conversions,
        metrics.all_conversions,
        metrics.all_conversions_value
    FROM campaign
    WHERE campaign.id = {cmp_id}
      AND segments.date >= '2026-05-24'
      AND segments.date <= '2026-05-27'
      AND metrics.all_conversions > 0
    ORDER BY segments.date
    """
    for r in svc.search(customer_id=cid, query=q3):
        print(f"  [{cmp_id}] {cmp_name[:35]:<35} {r.segments.date} {r.segments.conversion_action_name[:30]:<30} vt={r.metrics.view_through_conversions} all={r.metrics.all_conversions:.2f} val=EUR{r.metrics.all_conversions_value:.2f}")
