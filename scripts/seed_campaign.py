"""
Seed Supabase with the existing manually-created campaign.

The campaign "Belgium Campaign May 13" (id=23837741178) was created via
the Google Ads UI before API access was approved. This script:
  1. Fetches the campaign's current state from the Google Ads API
  2. Upserts it into belgium_campaign_state in Supabase
  3. Pulls all performance data since campaign start and upserts into
     belgium_daily_performance

Run once after credentials are set up:
    python3 scripts/seed_campaign.py
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

try:
    from dotenv import load_dotenv
    load_dotenv(".env.local")
    print("✓ Loaded .env.local")
except ImportError:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "api"))

from api._lib import google_ads_client, config
from api._lib.supabase_client import upsert_campaign_state, upsert_daily_performance, get_campaign_state

# The manually created campaign
CAMPAIGN_ID = "23837741178"
CAMPAIGN_RESOURCE = f"customers/{os.environ.get('GOOGLE_ADS_CUSTOMER_ID', '3152829803')}/campaigns/{CAMPAIGN_ID}"
CAMPAIGN_START = "2026-05-13"  # campaign start date from the UI

print(f"\n── Connecting to Google Ads API ───────────────────")
client = google_ads_client.get_client()
cid = google_ads_client.customer_id()

# 1. Fetch campaign state from API
print(f"  Fetching campaign {CAMPAIGN_ID}...")
ga_service = client.get_service("GoogleAdsService")
query = f"""
    SELECT
        campaign.id,
        campaign.name,
        campaign.status,
        campaign.start_date_time,
        campaign.end_date_time,
        campaign_budget.amount_micros
    FROM campaign
    WHERE campaign.id = {CAMPAIGN_ID}
"""
rows = list(ga_service.search(customer_id=cid, query=query))
if not rows:
    print(f"✗ Campaign {CAMPAIGN_ID} not found in account {cid}")
    sys.exit(1)

row = rows[0]
daily_budget_cents = row.campaign_budget.amount_micros // 10_000
print(f"  ✓ Found: [{row.campaign.status.name}] {row.campaign.name}")
print(f"    Budget: ${daily_budget_cents/100:.2f}/day")
print(f"    Dates:  {row.campaign.start_date_time} → {row.campaign.end_date_time}")

# 2. Upsert into Supabase campaign state
print(f"\n── Seeding belgium_campaign_state ─────────────────")
state_row = {
    "campaign_id": CAMPAIGN_ID,
    "resource_name": CAMPAIGN_RESOURCE,
    "campaign_name": row.campaign.name,
    "status": row.campaign.status.name,
    "daily_budget_cents": daily_budget_cents,
    "start_date": row.campaign.start_date_time,
    "end_date": row.campaign.end_date_time,
    "spend_to_date_cents": 0,
    "conversions_to_date": 0,
    "revenue_to_date_cents": 0,
    "last_synced_at": datetime.utcnow().isoformat(),
}
upsert_campaign_state(state_row)
print(f"  ✓ campaign_id={CAMPAIGN_ID} upserted into belgium_campaign_state")

# 3. Pull all performance since campaign start
print(f"\n── Pulling performance since {CAMPAIGN_START} ──────────────")
perf_rows = google_ads_client.pull_performance(client, CAMPAIGN_ID, CAMPAIGN_START)
print(f"  Fetched {len(perf_rows)} performance row(s) from Google Ads")

if perf_rows:
    written = upsert_daily_performance(perf_rows)
    print(f"  ✓ {written} row(s) upserted into belgium_daily_performance")

    total_spend = sum(r.get("cost_cents", 0) for r in perf_rows)
    total_conv = sum(float(r.get("conversions", 0)) for r in perf_rows)
    total_rev = sum(r.get("conversion_value_cents", 0) for r in perf_rows)

    # Update rollup totals
    upsert_campaign_state({
        "campaign_id": CAMPAIGN_ID,
        "spend_to_date_cents": total_spend,
        "conversions_to_date": total_conv,
        "revenue_to_date_cents": total_rev,
        "last_synced_at": datetime.utcnow().isoformat(),
    })

    tz = ZoneInfo(config.TIMEZONE)
    print(f"\n── Rollup summary ──────────────────────────────────")
    print(f"  Total spend:       ${total_spend/100:.2f}")
    print(f"  Total conversions: {total_conv:.1f}")
    print(f"  Total revenue:     ${total_rev/100:.2f}")
    for r in sorted(perf_rows, key=lambda x: x["date"]):
        print(f"  {r['date']}  spend=${r['cost_cents']/100:.2f}  clicks={r.get('clicks',0)}  conv={r.get('conversions',0)}")
else:
    print("  (no performance data yet — campaign may not have served yet)")

print(f"\n✅ Seed complete! Campaign is now tracked in Supabase.\n")
