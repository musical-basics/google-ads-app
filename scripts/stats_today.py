"""Pull today's per-campaign + per-ad-group stats across all enabled campaigns."""
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
today = date.today().isoformat()

# Per-campaign totals today
camp_q = f"""
SELECT
    campaign.id, campaign.name, campaign.status,
    metrics.impressions, metrics.clicks, metrics.interactions,
    metrics.cost_micros, metrics.conversions, metrics.conversions_value
FROM campaign
WHERE segments.date = '{today}'
  AND campaign.status != 'REMOVED'
ORDER BY metrics.cost_micros DESC
"""
print(f"=== Campaign totals for {today} ===\n")
print(f"{'CAMPAIGN':<45} {'STATUS':<8} {'IMPR':>8} {'CLK':>5} {'ENG':>5} {'COST':>9} {'CONV':>5} {'REV':>8}")
print("-" * 100)
campaign_rows = []
for r in svc.search(customer_id=cid, query=camp_q):
    campaign_rows.append(r)
    name = r.campaign.name[:43]
    cost_eur = r.metrics.cost_micros / 1_000_000
    rev_eur = r.metrics.conversions_value
    print(f"{name:<45} {r.campaign.status.name:<8} {r.metrics.impressions:>8} {r.metrics.clicks:>5} {r.metrics.interactions:>5} EUR{cost_eur:>6.2f} {r.metrics.conversions:>5.1f} EUR{rev_eur:>5.2f}")

if not campaign_rows:
    print("(no activity yet today)")
    sys.exit(0)

# Per-ad-group breakdown for any campaign with activity
print(f"\n=== Ad group breakdown ({today}) ===\n")
print(f"{'CAMPAIGN':<35} {'AD GROUP':<40} {'IMPR':>8} {'CLK':>5} {'COST':>9} {'CONV':>5}")
print("-" * 110)
ag_q = f"""
SELECT
    campaign.name, ad_group.id, ad_group.name, ad_group.status,
    metrics.impressions, metrics.clicks, metrics.cost_micros, metrics.conversions
FROM ad_group
WHERE segments.date = '{today}'
  AND campaign.status != 'REMOVED'
ORDER BY campaign.name, metrics.cost_micros DESC
"""
for r in svc.search(customer_id=cid, query=ag_q):
    if r.metrics.impressions == 0 and r.metrics.clicks == 0:
        continue
    cn = r.campaign.name[:33]
    an = r.ad_group.name[:38]
    cost_eur = r.metrics.cost_micros / 1_000_000
    print(f"{cn:<35} {an:<40} {r.metrics.impressions:>8} {r.metrics.clicks:>5} EUR{cost_eur:>6.2f} {r.metrics.conversions:>5.1f}")
