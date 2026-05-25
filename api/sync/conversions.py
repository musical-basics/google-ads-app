"""
POST /api/sync/conversions
Body: { hours: int (optional, default 48), dry_run: bool (optional, default false) }

GET /api/sync/conversions
Called automatically by Vercel Cron every 2 hours.
Authenticated via Authorization: Bearer <CRON_SECRET> header.

Pulls recent conversion logs from Supabase and uploads click conversions to Google Ads.
"""
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from _lib.http_helpers import require_api_key, respond, read_json_body
from _lib.log import log_action, log_exception
from _lib import google_ads_client, conversions


def _run_sync(hours: int, dry_run: bool):
    """Shared sync logic used by both GET (cron) and POST (manual)."""
    client = google_ads_client.get_client()
    customer_id = google_ads_client.customer_id()

    # 1. Resolve/create conversion actions in Google Ads
    action_map = {}
    for key, action_name in conversions.CONVERSION_ACTIONS.items():
        action_map[action_name] = conversions.get_or_create_conversion_action(
            client, customer_id, action_name
        )

    # 2. Fetch logs from Supabase
    logs = conversions.fetch_supabase_logs(hours=hours)

    # 3. Upload to Google Ads
    res = conversions.upload_conversions(client, customer_id, logs, action_map, dry_run=dry_run)

    log_action("sync_conversions", {
        "hours": hours,
        "dry_run": dry_run,
        "logs_found": len(logs),
        "uploaded": res.get("uploaded", 0),
        "success_count": res.get("success_count", 0),
        "fail_count": res.get("fail_count", 0),
    }, success=True)

    return res, logs


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Called by Vercel Cron every 2 hours. Authenticated via CRON_SECRET."""
        cron_secret = os.environ.get("CRON_SECRET", "")
        auth_header = self.headers.get("Authorization", "")
        expected = f"Bearer {cron_secret}"

        if not cron_secret or auth_header != expected:
            return respond(self, 401, {"error": "unauthorized"})

        try:
            # Use a 3-hour window to safely overlap with the 2-hour cron cadence
            res, logs = _run_sync(hours=3, dry_run=False)
            return respond(self, 200, {
                "success": True,
                "source": "cron",
                "logs_found": len(logs),
                "google_ads_results": res,
            })
        except Exception as e:
            log_exception("sync_conversions_cron", e)
            return respond(self, 500, {"error": str(e), "trace": traceback.format_exc()})

    def do_POST(self):
        """Manual trigger with API key auth."""
        if not require_api_key(self):
            return respond(self, 401, {"error": "unauthorized"})
        try:
            body = read_json_body(self)
            hours = int(body.get("hours") or 48)
            dry_run = bool(body.get("dry_run"))

            res, logs = _run_sync(hours=hours, dry_run=dry_run)

            return respond(self, 200, {
                "success": True,
                "hours": hours,
                "dry_run": dry_run,
                "logs_found": len(logs),
                "google_ads_results": res
            })
        except Exception as e:
            log_exception("sync_conversions", e)
            return respond(self, 500, {"error": str(e), "trace": traceback.format_exc()})
