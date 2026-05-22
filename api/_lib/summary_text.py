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

    state = get_campaign_state() or {}
    rows  = get_daily_performance(date_str)

    # ── Per-ad-group metrics ──────────────────────────────────────
    sub  = _ag_metrics(rows, config.AD_GROUP_SUBSCRIBERS)
    view = _ag_metrics(rows, config.AD_GROUP_VIEWERS)

    # ── Campaign totals ───────────────────────────────────────────
    spend       = sum(r.get("cost_cents") or 0 for r in rows)
    impressions = sum(r.get("impressions") or 0 for r in rows)
    views       = sum(r.get("views") or 0 for r in rows)
    clicks      = sum(r.get("clicks") or 0 for r in rows)
    conversions = sum(float(r.get("conversions") or 0) for r in rows)
    revenue     = sum(r.get("conversion_value_cents") or 0 for r in rows)

    daily_budget = state.get("daily_budget_cents") or 0
    pct_of_daily = (spend / daily_budget * 100) if daily_budget else 0

    total_spend  = state.get("spend_to_date_cents") or 0
    total_budget = state.get("total_budget_cents") or 0
    total_conv   = float(state.get("conversions_to_date") or 0)
    total_rev    = state.get("revenue_to_date_cents") or 0
    pct_total    = (total_spend / total_budget * 100) if total_budget else 0
    roas         = (total_rev / total_spend) if total_spend else 0
    cpa          = (total_spend / total_conv) if total_conv else 0

    # ── Shopify ticket sales ──────────────────────────────────────
    seats_sold      = count_total_sales()
    seats_remaining = max(0, 100 - seats_sold)

    day_start  = f"{date_str}T00:00:00+00:00"
    day_end    = f"{date_str}T23:59:59+00:00"
    day_sales  = get_sales_range(day_start, day_end)

    standard_count = sum(1 for s in day_sales if s.get("ticket_tier") == "standard")
    vip_count      = sum(1 for s in day_sales if s.get("ticket_tier") == "vip")
    tier_str = f"{standard_count} standard, {vip_count} VIP" if (standard_count or vip_count) else "n/a"

    # Attribution per ad group via utm_content (set as final_url_suffix per ad group)
    sub_sales  = [s for s in day_sales if s.get("utm_content") == config.UTM_CONTENT_SUBSCRIBERS]
    view_sales = [s for s in day_sales if s.get("utm_content") == config.UTM_CONTENT_VIEWERS]

    # ── Guardrail alerts ──────────────────────────────────────────
    g = guardrails.evaluate()
    alerts     = [s["message"] for s in g["soft"]] + [h["message"] for h in g["hard"]]
    alerts_str = "\n".join(f"  - {a}" for a in alerts) if alerts else "  none"

    status = state.get("status") or "not_created"

    return f"""BELGIUM CONCERT ADS: {date_str}
Days until concert: {days_until}
Seats remaining (Shopify): {seats_remaining} of 100  ({seats_sold} sold)

YESTERDAY — A/B BREAKDOWN:
{_fmt_ag("subscribers_and_viewers", sub, len(sub_sales))}

{_fmt_ag("video_viewers_only     ", view, len(view_sales))}

YESTERDAY — TOTAL:
  Spend: {spend / 100:.2f} EUR ({pct_of_daily:.0f}% of ${daily_budget/100:.2f} daily budget)
  Impressions: {impressions}  |  Views: {views}  |  Clicks: {clicks}
  Conversions: {conversions:.1f}  |  Tickets sold: {tier_str}
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
