"""
Plain-text daily summary renderer. Shared by the GET endpoint and the email sender.
"""
from datetime import datetime, date as date_cls
from zoneinfo import ZoneInfo

from .supabase_client import (
    get_campaign_state,
    get_daily_performance,
    count_total_sales,
    get_sales_range,
)
from . import guardrails, config


def render_daily_summary(date_str: str) -> str:
    tz = ZoneInfo(config.TIMEZONE)
    today = datetime.now(tz).date()
    concert = date_cls.fromisoformat(config.CONCERT_DATE)
    days_until = (concert - today).days

    state = get_campaign_state() or {}
    rows = get_daily_performance(date_str)
    spend = sum(r.get("cost_cents") or 0 for r in rows)
    impressions = sum(r.get("impressions") or 0 for r in rows)
    views = sum(r.get("views") or 0 for r in rows)
    clicks = sum(r.get("clicks") or 0 for r in rows)
    conversions = sum(float(r.get("conversions") or 0) for r in rows)
    revenue = sum(r.get("conversion_value_cents") or 0 for r in rows)

    daily_budget = state.get("daily_budget_cents") or 0
    pct_of_daily = (spend / daily_budget * 100) if daily_budget else 0

    total_spend = state.get("spend_to_date_cents") or 0
    total_budget = state.get("total_budget_cents") or 0
    total_conv = float(state.get("conversions_to_date") or 0)
    total_rev = state.get("revenue_to_date_cents") or 0
    pct_total = (total_spend / total_budget * 100) if total_budget else 0
    roas = (total_rev / total_spend) if total_spend else 0
    cpa = (total_spend / total_conv) if total_conv else 0

    seats_sold = count_total_sales()
    seats_remaining = max(0, 100 - seats_sold)

    day_start = f"{date_str}T00:00:00+00:00"
    day_end = f"{date_str}T23:59:59+00:00"
    day_sales = get_sales_range(day_start, day_end)
    standard_count = sum(1 for s in day_sales if s.get("ticket_tier") == "standard")
    vip_count = sum(1 for s in day_sales if s.get("ticket_tier") == "vip")
    tier_str = f"{standard_count} standard, {vip_count} VIP" if (standard_count or vip_count) else "n/a"

    g = guardrails.evaluate()
    alerts = [s["message"] for s in g["soft"]] + [h["message"] for h in g["hard"]]
    alerts_str = "\n".join(f"  - {a}" for a in alerts) if alerts else "  none"

    status = state.get("status") or "not_created"

    return f"""BELGIUM CONCERT ADS: {date_str}
Days until concert: {days_until}
Seats remaining (Shopify): {seats_remaining} of 100

YESTERDAY:
  Spend: {spend / 100:.2f} EUR ({pct_of_daily:.0f}% of daily budget)
  Impressions: {impressions}
  Views: {views}
  Clicks: {clicks}
  Conversions: {conversions:.1f} ({tier_str})
  Revenue: {revenue / 100:.2f} EUR

TO DATE:
  Total spend: {total_spend / 100:.2f} of {total_budget / 100:.2f} EUR ({pct_total:.0f}%)
  Total conversions: {total_conv:.1f}
  Total ad-attributed revenue: {total_rev / 100:.2f} EUR
  ROAS: {roas:.2f}x
  CPA: {cpa / 100:.2f} EUR

STATUS: {status}

ALERTS:
{alerts_str}
"""
