"""
Seed Supabase with Campaign 2 and Campaign 3.
This script:
  1. Fetches each campaign's current state from the Google Ads API
  2. Upserts it into belgium_campaign_state in Supabase
  3. Pulls all performance data since campaign start and upserts into
     belgium_daily_performance
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "api"))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(HERE, "..", ".env.local"))
    print("✓ Loaded .env.local")
except ImportError:
    pass

from api._lib import google_ads_client, config
from api._lib.supabase_client import upsert_campaign_state, upsert_daily_performance

CAMPAIGNS = {
    "23871037379": "2026-05-20", # Campaign 2 (New Creative Trimmed)
    "23875661669": "2026-05-20"  # Campaign 3 (Original Creative New Targeting)
}

def seed_campaign(client, cid, campaign_id, start_date):
    print(f"\n── Seeding campaign {campaign_id} ───────────────────")
    campaign_resource = f"customers/{cid}/campaigns/{campaign_id}"
    
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
        WHERE campaign.id = {campaign_id}
    """
    rows = list(ga_service.search(customer_id=cid, query=query))
    if not rows:
        print(f"✗ Campaign {campaign_id} not found in account {cid}")
        return

    row = rows[0]
    daily_budget_cents = row.campaign_budget.amount_micros // 10_000
    print(f"  ✓ Found: [{row.campaign.status.name}] {row.campaign.name}")
    print(f"    Budget: ${daily_budget_cents/100:.2f}/day")
    print(f"    Dates:  {row.campaign.start_date_time} → {row.campaign.end_date_time}")

    # Map ad groups based on campaign_id
    if str(campaign_id) == config.CAMPAIGN_2_ID:
        ag_sub = config.AG2_SUBSCRIBERS
        ag_view = config.AG2_VIEWERS
    elif str(campaign_id) == config.CAMPAIGN_3_ID:
        ag_sub = config.AG3_SUBSCRIBERS
        ag_view = config.AG3_VIEWERS
    else:
        ag_sub = None
        ag_view = None

    state_row = {
        "campaign_id": str(campaign_id),
        "resource_name": campaign_resource,
        "status": row.campaign.status.name,
        "daily_budget_cents": daily_budget_cents,
        "total_budget_cents": 200000, # $2000.00
        "ad_group_subscribers_id": ag_sub,
        "ad_group_lookalike_id": ag_view,
        "spend_to_date_cents": 0,
        "conversions_to_date": 0,
        "revenue_to_date_cents": 0,
        "last_synced_at": datetime.now(ZoneInfo(config.TIMEZONE)).isoformat(),
    }
    
    # We can fetch existing state first to make sure we preserve custom fields like total_budget_cents if set
    try:
        from api._lib.supabase_client import supabase
        existing = supabase().table("belgium_campaign_state").select("*").eq("campaign_id", str(campaign_id)).execute()
        if existing.data:
            state_row["total_budget_cents"] = existing.data[0].get("total_budget_cents") or 200000
    except Exception as ex:
        print(f"  Error reading existing campaign state: {ex}")

    upsert_campaign_state(state_row)
    print(f"  ✓ campaign_id={campaign_id} upserted into belgium_campaign_state")

    # Pull all performance since campaign start
    print(f"  Pulling performance since {start_date}...")
    perf_rows = google_ads_client.pull_performance(client, campaign_id, start_date)
    print(f"  Fetched {len(perf_rows)} performance row(s) from Google Ads")

    if perf_rows:
        written = upsert_daily_performance(perf_rows)
        print(f"  ✓ {written} row(s) upserted into belgium_daily_performance")

        total_spend = sum(r.get("cost_cents", 0) for r in perf_rows)
        total_conv = sum(float(r.get("conversions", 0)) for r in perf_rows)
        total_rev = sum(r.get("conversion_value_cents", 0) for r in perf_rows)

        # Update rollup totals
        upsert_campaign_state({
            "campaign_id": campaign_id,
            "spend_to_date_cents": total_spend,
            "conversions_to_date": total_conv,
            "revenue_to_date_cents": total_rev,
            "last_synced_at": datetime.utcnow().isoformat(),
        })

        print(f"  Rollup: spend=${total_spend/100:.2f} conv={total_conv:.1f} revenue=${total_rev/100:.2f}")
    else:
        print("  (no performance data yet)")

def main():
    client = google_ads_client.get_client()
    cid = google_ads_client.customer_id()
    for campaign_id, start_date in CAMPAIGNS.items():
        seed_campaign(client, cid, campaign_id, start_date)
    print("\n✅ Seed complete for Campaigns 2 & 3!\n")

if __name__ == "__main__":
    main()
