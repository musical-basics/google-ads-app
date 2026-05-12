"""
Hard + soft guardrail evaluation. Pure-ish: takes state, returns triggered rules.
Enforcement (pausing) is the caller's job.
"""
from datetime import datetime, date as date_cls
from zoneinfo import ZoneInfo

from . import config
from .supabase_client import get_campaign_state, get_performance_range


def _today_in_tz() -> date_cls:
    return datetime.now(ZoneInfo(config.TIMEZONE)).date()


def evaluate() -> dict:
    """
    Returns {
        hard: [ {rule, message, action: "pause"} ],
        soft: [ {rule, message} ],
        snapshot: { ... current state ... }
    }
    """
    state = get_campaign_state() or {}
    hard: list[dict] = []
    soft: list[dict] = []

    spend = state.get("spend_to_date_cents") or 0
    total_budget = state.get("total_budget_cents") or 0
    daily_budget = state.get("daily_budget_cents") or 0
    conversions = float(state.get("conversions_to_date") or 0)

    today = _today_in_tz()
    end_date = date_cls.fromisoformat(config.CAMPAIGN_END_DATE)
    concert_date = date_cls.fromisoformat(config.CONCERT_DATE)

    # Hard 1: budget cap
    if total_budget and spend >= int(total_budget * config.HARD_SPEND_CAP_PCT):
        hard.append({
            "rule": "hard_budget_cap_95pct",
            "message": f"spend {spend / 100:.2f} EUR is at or above 95% of total budget {total_budget / 100:.2f}",
            "action": "pause",
        })

    # Hard 2: runaway day. Look at today's row.
    today_iso = today.isoformat()
    today_perf = [r for r in get_performance_range(today_iso, today_iso)]
    today_spend = sum(r.get("cost_cents") or 0 for r in today_perf)
    if daily_budget and today_spend >= int(daily_budget * config.HARD_DAILY_OVERSPEND_PCT):
        hard.append({
            "rule": "hard_daily_overspend_130pct",
            "message": f"today's spend {today_spend / 100:.2f} EUR is at or above 130% of daily budget {daily_budget / 100:.2f}",
            "action": "pause",
        })

    # Hard 3: campaign end reached
    if today > end_date:
        hard.append({
            "rule": "hard_campaign_end_reached",
            "message": f"today ({today_iso}) is past CAMPAIGN_END_DATE ({config.CAMPAIGN_END_DATE})",
            "action": "pause",
        })

    # Soft 1: daily overspend > 110%
    if daily_budget and today_spend > int(daily_budget * config.SOFT_DAILY_OVERSPEND_PCT) and today_spend < int(daily_budget * config.HARD_DAILY_OVERSPEND_PCT):
        soft.append({
            "rule": "soft_daily_overspend_110pct",
            "message": f"today's spend {today_spend / 100:.2f} EUR exceeds 110% of daily budget",
        })

    # Soft 2: 48h zero conversions with >50 EUR spend
    last_48h_perf = _last_n_days_perf(2)
    recent_spend = sum(r.get("cost_cents") or 0 for r in last_48h_perf)
    recent_convs = sum(float(r.get("conversions") or 0) for r in last_48h_perf)
    if recent_spend > config.SOFT_NO_CONVERSION_MIN_SPEND_CENTS and recent_convs == 0:
        soft.append({
            "rule": "soft_no_conversions_48h",
            "message": f"zero conversions in last 48h with {recent_spend / 100:.2f} EUR spent",
        })

    # Soft 3: 7d CPA above ticket price
    last_7d_perf = _last_n_days_perf(7)
    week_spend = sum(r.get("cost_cents") or 0 for r in last_7d_perf)
    week_convs = sum(float(r.get("conversions") or 0) for r in last_7d_perf)
    if week_convs > 0:
        cpa = week_spend / week_convs
        if cpa > config.SOFT_CPA_ALERT_CENTS:
            soft.append({
                "rule": "soft_cpa_above_ticket_price",
                "message": f"7-day CPA {cpa / 100:.2f} EUR exceeds soft threshold {config.SOFT_CPA_ALERT_CENTS / 100:.2f}",
            })

    # Soft 4: pacing to fewer than target by concert date
    days_elapsed = max(1, (today - (end_date - _campaign_length())).days + 1)
    days_to_concert = max(1, (concert_date - today).days)
    projected = conversions + (conversions / days_elapsed) * days_to_concert if days_elapsed else conversions
    if projected < config.SOFT_PACING_MIN_CONVERSIONS_BY_CONCERT and conversions > 0:
        soft.append({
            "rule": "soft_pacing_below_target",
            "message": f"projecting ~{projected:.0f} conversions by concert vs target {config.SOFT_PACING_MIN_CONVERSIONS_BY_CONCERT}",
        })

    return {
        "hard": hard,
        "soft": soft,
        "snapshot": {
            "today": today_iso,
            "today_spend_cents": today_spend,
            "spend_to_date_cents": spend,
            "total_budget_cents": total_budget,
            "daily_budget_cents": daily_budget,
            "conversions_to_date": conversions,
        },
    }


def _campaign_length():
    from datetime import timedelta
    # Assume the campaign started on the row's created_at date.
    state = get_campaign_state() or {}
    created = state.get("created_at")
    if not created:
        return timedelta(days=1)
    if isinstance(created, str):
        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
    else:
        created_dt = created
    today = _today_in_tz()
    return today - created_dt.date()


def _last_n_days_perf(n: int) -> list[dict]:
    from datetime import timedelta
    today = _today_in_tz()
    start = (today - timedelta(days=n - 1)).isoformat()
    end = today.isoformat()
    return get_performance_range(start, end)
