"""
POST /api/sync/google_ads
Body: { since: "YYYY-MM-DD" (optional, defaults to today in TIMEZONE) }

Pulls per-ad-group performance from Google Ads into belgium_daily_performance,
then rolls up totals into belgium_campaign_state.
"""
import os
import sys
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo
from http.server import BaseHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from _lib.http_helpers import require_api_key, respond, read_json_body
from _lib.log import log_action, log_exception
from _lib.supabase_client import (
    get_campaign_state,
    get_all_campaign_states,
    upsert_campaign_state,
    upsert_daily_performance,
    get_performance_range,
)
from _lib import google_ads_client, config


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if not require_api_key(self):
            return respond(self, 401, {"error": "unauthorized"})
        try:
            body = read_json_body(self)
            tz = ZoneInfo(config.TIMEZONE)
            since = body.get("since") or datetime.now(tz).date().isoformat()

            states = get_all_campaign_states()
            if not states:
                return respond(self, 404, {"error": "no campaigns exist yet"})

            client = google_ads_client.get_client()
            total_written = 0

            for state in states:
                campaign_id = state["campaign_id"]
                rows = google_ads_client.pull_performance(client, campaign_id, since)
                if rows:
                    total_written += upsert_daily_performance(rows)

            # Roll up totals (since campaign start)
            all_perf = get_performance_range("2026-05-01", datetime.now(tz).date().isoformat())
            
            rollup_results = {}
            for state in states:
                campaign_id = state["campaign_id"]
                camp_perf = [r for r in all_perf if str(r.get("campaign_id", "")) == str(campaign_id)]
                
                total_spend = sum(r.get("cost_cents") or 0 for r in camp_perf)
                total_conv = sum(float(r.get("conversions") or 0) for r in camp_perf)
                total_rev = sum(r.get("conversion_value_cents") or 0 for r in camp_perf)
                
                upsert_campaign_state({
                    "campaign_id": campaign_id,
                    "spend_to_date_cents": total_spend,
                    "conversions_to_date": total_conv,
                    "revenue_to_date_cents": total_rev,
                    "last_synced_at": datetime.utcnow().isoformat(),
                })
                
                rollup_results[campaign_id] = {
                    "spend_to_date_cents": total_spend,
                    "conversions_to_date": total_conv,
                    "revenue_to_date_cents": total_rev,
                }

            log_action("sync_google_ads", {"since": since, "rows_written": total_written}, success=True)
            return respond(self, 200, {
                "since": since,
                "rows_written": total_written,
                "rollups": rollup_results,
            })
        except Exception as e:
            log_exception("sync_google_ads", e)
            return respond(self, 500, {"error": str(e), "trace": traceback.format_exc()})
