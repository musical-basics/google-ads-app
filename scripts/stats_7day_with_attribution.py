"""7-day campaign + ad group rollup with Google Ads' own click-attributed
Shopify Purchase totals (the source of truth, not Shopify's landing_site UTMs)."""
import sys
from pathlib import Path
from datetime import date, timedelta
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env.local")

from api._lib.google_ads_client import get_client, customer_id

client = get_client()
svc = client.get_service("GoogleAdsService")
cid = customer_id()
today = date.today().isoformat()
since = (date.today() - timedelta(days=6)).isoformat()

# Per-campaign 7-day totals
print(f"=== Per-campaign totals {since} -> {today} (7 days) ===\n")
q = f"""
SELECT
    campaign.name, campaign.status,
    metrics.impressions, metrics.clicks, metrics.cost_micros,
    metrics.conversions, metrics.conversions_value
FROM campaign
WHERE segments.date >= '{since}' AND segments.date <= '{today}'
  AND campaign.status != 'REMOVED'
"""
camps = {}
for r in svc.search(customer_id=cid, query=q):
    n = r.campaign.name
    if n not in camps:
        camps[n] = {"status": r.campaign.status.name, "impr": 0, "clk": 0, "cost": 0, "conv": 0.0, "rev": 0.0}
    camps[n]["impr"] += r.metrics.impressions
    camps[n]["clk"] += r.metrics.clicks
    camps[n]["cost"] += r.metrics.cost_micros
    camps[n]["conv"] += r.metrics.conversions
    camps[n]["rev"] += r.metrics.conversions_value

print(f"{'CAMPAIGN':<48} {'STATUS':<8} {'IMPR':>8} {'CLK':>5} {'COST':>10} {'CONV':>6} {'REV':>9} {'ROAS':>6}")
print("-" * 120)
for n, c in sorted(camps.items(), key=lambda x: -x[1]["cost"]):
    cost_eur = c["cost"] / 1_000_000
    roas = c["rev"] / cost_eur if cost_eur > 0 else 0
    print(f"{n[:46]:<48} {c['status']:<8} {c['impr']:>8} {c['clk']:>5} EUR{cost_eur:>7.2f} {c['conv']:>6.1f} EUR{c['rev']:>6.2f} {roas:>5.2f}x")

# Click-attributed Shopify Purchases (the only conversion action that matters for ROI)
print(f"\n=== Shopify Purchases (click-attributed by Google Ads) {since} -> {today} ===\n")
q2 = f"""
SELECT
    segments.date, campaign.name, ad_group.name,
    segments.conversion_action_name,
    metrics.conversions, metrics.conversions_value, metrics.view_through_conversions
FROM ad_group
WHERE segments.date >= '{since}' AND segments.date <= '{today}'
  AND segments.conversion_action_name = 'Shopify Purchase'
  AND metrics.conversions > 0
ORDER BY segments.date DESC
"""
total_conv = 0.0
total_rev = 0.0
for r in svc.search(customer_id=cid, query=q2):
    print(f"  {r.segments.date}  {r.campaign.name[:42]:<42} {r.ad_group.name[:28]:<28} conv={r.metrics.conversions:.2f} val=EUR{r.metrics.conversions_value:>6.2f} vt={r.metrics.view_through_conversions}")
    total_conv += r.metrics.conversions
    total_rev += r.metrics.conversions_value
print(f"\n  TOTAL: {total_conv:.0f} Shopify Purchases, EUR{total_rev:.2f} revenue (click-attributed)")

# Per-ad-group cost-per-purchase (impressions, clicks, cost vs purchases)
print(f"\n=== Ad group efficiency {since} -> {today} ===\n")
q3 = f"""
SELECT
    campaign.name, ad_group.name, ad_group.status,
    metrics.impressions, metrics.clicks, metrics.cost_micros
FROM ad_group
WHERE segments.date >= '{since}' AND segments.date <= '{today}'
  AND campaign.status != 'REMOVED'
"""
ags = {}
for r in svc.search(customer_id=cid, query=q3):
    key = (r.campaign.name, r.ad_group.name)
    if key not in ags:
        ags[key] = {"status": r.ad_group.status.name, "impr": 0, "clk": 0, "cost": 0, "purch": 0.0, "rev": 0.0}
    ags[key]["impr"] += r.metrics.impressions
    ags[key]["clk"] += r.metrics.clicks
    ags[key]["cost"] += r.metrics.cost_micros

# Merge in purchase numbers from q2
q4 = f"""
SELECT campaign.name, ad_group.name, segments.conversion_action_name,
       metrics.conversions, metrics.conversions_value
FROM ad_group
WHERE segments.date >= '{since}' AND segments.date <= '{today}'
  AND segments.conversion_action_name = 'Shopify Purchase'
"""
for r in svc.search(customer_id=cid, query=q4):
    key = (r.campaign.name, r.ad_group.name)
    if key in ags:
        ags[key]["purch"] += r.metrics.conversions
        ags[key]["rev"] += r.metrics.conversions_value

print(f"{'CAMPAIGN':<35} {'AD GROUP':<30} {'IMPR':>8} {'CLK':>5} {'COST':>9} {'PURCH':>6} {'REV':>9} {'CPP':>9}")
print("-" * 130)
for key, a in sorted(ags.items(), key=lambda x: -x[1]["cost"]):
    if a["impr"] == 0:
        continue
    cost_eur = a["cost"] / 1_000_000
    cpp = cost_eur / a["purch"] if a["purch"] > 0 else float('inf')
    cpp_str = f"EUR{cpp:.2f}" if a["purch"] > 0 else "no sale"
    print(f"{key[0][:33]:<35} {key[1][:28]:<30} {a['impr']:>8} {a['clk']:>5} EUR{cost_eur:>6.2f} {a['purch']:>6.1f} EUR{a['rev']:>6.2f} {cpp_str:>9}")
