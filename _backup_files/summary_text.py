"""
Plain-text daily summary renderer. Shared by the GET endpoint and the email sender.
"""
from datetime import datetime, date as date_cls
from zoneinfo import ZoneInfo

from .supabase_client import (
    get_all_campaign_states,
    get_daily_performance,
    count_total_sales,
    get_sales_range,
)
from . import guardrails, config


def _ag_metrics(rows: list[dict], ag_id: str) -> dict:
    ag_rows = [r for r in rows if str(r.get("ad_group_id", "")) == ag_id]
    spend       = sum(r.get("cost_cents") or 0 for r in ag_rows)
    impressions = sum(r.get("impressions") or 0 for r in ag_rows)
    views       = sum(r.get("views") or 0 for r in ag_rows)
    clicks      = sum(r.get("clicks") or 0 for r in ag_rows)
    conversions = sum(float(r.get("conversions") or 0) for r in ag_rows)
    revenue     = sum(r.get("conversion_value_cents") or 0 for r in ag_rows)
    ctr = f"{clicks/impressions*100:.2f}%" if impressions else "n/a"
    vcr = f"{views/impressions*100:.1f}%"  if impressions else "n/a"
    cpa = f"${spend/conversions/100:.2f}"  if conversions else "n/a"
    return dict(
        spend=spend, impressions=impressions, views=views, clicks=clicks,
        conversions=conversions, revenue=revenue, ctr=ctr, vcr=vcr, cpa=cpa,
    )


def _fmt_ag(label: str, m: dict, ticket_count: int) -> str:
    return (
        f"  [{label}]\n"
        f"    Spend: ${m['spend']/100:.2f}  |  Impressions: {m['impressions']}  |  Views: {m['views']} ({m['vcr']})\n"
        f"    Clicks: {m['clicks']} ({m['ctr']})  |  Conversions: {m['conversions']:.1f}  |  CPA: {m['cpa']}\n"
        f"    Tickets (Shopify-attributed): {ticket_count}"
    )


def render_daily_summary(date_str: str) -> str:
    tz = ZoneInfo(config.TIMEZONE)
    today  = datetime.now(tz).date()
    concert = date_cls.fromisoformat(config.CONCERT_DATE)
    days_until = (concert - today).days

    states = get_all_campaign_states()
    active_states = [s for s in states if str(s.get("campaign_id")) in config.ACTIVE_CAMPAIGNS]
    rows  = get_daily_performance(date_str)

    # ── Shopify ticket sales ──────────────────────────────────────
    seats_sold      = count_total_sales()
    seats_remaining = max(0, 100 - seats_sold)

    day_start  = f"{date_str}T00:00:00+00:00"
    day_end    = f"{date_str}T23:59:59+00:00"
    day_sales  = get_sales_range(day_start, day_end)

    standard_count = sum(1 for s in day_sales if s.get("ticket_tier") == "standard")
    vip_count      = sum(1 for s in day_sales if s.get("ticket_tier") == "vip")
    tier_str = f"{standard_count} standard, {vip_count} VIP" if (standard_count or vip_count) else "n/a"

    # Map campaign ID to its ad groups and details
    CAMPAIGN_AD_GROUPS = {
        config.CAMPAIGN_2_ID: (config.AG2_SUBSCRIBERS, config.AG2_VIEWERS, "Campaign 2 (New Creative)", config.UTM_CAMPAIGN_2),
        config.CAMPAIGN_3_ID: (config.AG3_SUBSCRIBERS, config.AG3_VIEWERS, "Campaign 3 (Original Creative)", config.UTM_CAMPAIGN_3),
    }

    ab_breakdown_sections = []
    for state in active_states:
        camp_id = state["campaign_id"]
        if camp_id not in CAMPAIGN_AD_GROUPS:
            continue
        sub_id, view_id, camp_label, utm_camp = CAMPAIGN_AD_GROUPS[camp_id]
        
        camp_rows = [r for r in rows if str(r.get("campaign_id", "")) == str(camp_id)]
        sub_metrics = _ag_metrics(camp_rows, sub_id)
        view_metrics = _ag_metrics(camp_rows, view_id)
        
        sub_sales = [s for s in day_sales if s.get("utm_content") == config.UTM_CONTENT_SUBSCRIBERS and s.get("utm_campaign") == utm_camp]
        view_sales = [s for s in day_sales if s.get("utm_content") == config.UTM_CONTENT_VIEWERS and s.get("utm_campaign") == utm_camp]
        
        section = (
            f"=== {camp_label} (ID: {camp_id}) ===\n"
            f"{_fmt_ag('subscribers_and_viewers', sub_metrics, len(sub_sales))}\n"
            f"{_fmt_ag('video_viewers_only     ', view_metrics, len(view_sales))}"
        )
        ab_breakdown_sections.append(section)

    ab_breakdown_str = "\n\n".join(ab_breakdown_sections)

    # ── Active campaigns totals ────────────────────────────────────
    active_camp_ids = set(config.ACTIVE_CAMPAIGNS)
    active_rows = [r for r in rows if str(r.get("campaign_id")) in active_camp_ids]
    
    spend       = sum(r.get("cost_cents") or 0 for r in active_rows)
    impressions = sum(r.get("impressions") or 0 for r in active_rows)
    views       = sum(r.get("views") or 0 for r in active_rows)
    clicks      = sum(r.get("clicks") or 0 for r in active_rows)
    conversions = sum(float(r.get("conversions") or 0) for r in active_rows)
    revenue     = sum(r.get("conversion_value_cents") or 0 for r in active_rows)

    daily_budget = sum(s.get("daily_budget_cents") or 0 for s in active_states)
    pct_of_daily = (spend / daily_budget * 100) if daily_budget else 0

    total_spend  = sum(s.get("spend_to_date_cents") or 0 for s in active_states)
    total_budget = sum(s.get("total_budget_cents") or 0 for s in active_states)
    total_conv   = sum(float(s.get("conversions_to_date") or 0) for s in active_states)
    total_rev    = sum(s.get("revenue_to_date_cents") or 0 for s in active_states)
    
    pct_total    = (total_spend / total_budget * 100) if total_budget else 0
    roas         = (total_rev / total_spend) if total_spend else 0
    cpa          = (total_spend / total_conv) if total_conv else 0

    # ── Guardrail alerts ──────────────────────────────────────────
    g = guardrails.evaluate()
    alerts     = [s["message"] for s in g["soft"]] + [h["message"] for h in g["hard"]]
    alerts_str = "\n".join(f"  - {a}" for a in alerts) if alerts else "  none"

    status_str = ", ".join(f"{s.get('campaign_name') or s['campaign_id']}: {s.get('status')}" for s in active_states)

    return f"""BELGIUM CONCERT ADS: {date_str}
Days until concert: {days_until}
Seats remaining (Shopify): {seats_remaining} of 100  ({seats_sold} sold)

YESTERDAY — A/B BREAKDOWN:
{ab_breakdown_str}

YESTERDAY — TOTAL (ACTIVE):
  Spend: {spend / 100:.2f} EUR ({pct_of_daily:.0f}% of ${daily_budget/100:.2f} daily budget)
  Impressions: {impressions}  |  Views: {views}  |  Clicks: {clicks}
  Conversions: {conversions:.1f}  |  Tickets sold: {tier_str}
  Revenue: {revenue / 100:.2f} EUR

TO DATE (ACTIVE):
  Total spend: {total_spend / 100:.2f} of {total_budget / 100:.2f} EUR ({pct_total:.0f}%)
  Total conversions: {total_conv:.1f}
  Total ad-attributed revenue: {total_rev / 100:.2f} EUR
  ROAS: {roas:.2f}x
  CPA: {cpa / 100:.2f} EUR

STATUS: {status_str}

ALERTS:
{alerts_str}
"""
