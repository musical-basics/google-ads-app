"""
POST /api/sync/conversions
Body: { hours: int (optional, default 48), dry_run: bool (optional, default false) }

GET /api/sync/conversions
Called automatically by Vercel Cron every 2 hours.
Authenticated via Authorization: Bearer <CRON_SECRET> header.

Pulls recent conversion logs from Supabase (CTA clicks, waitlist signups) and
Shopify (purchase orders) and uploads them to Google Ads.
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

    # 1. Resolve/create all three conversion actions in Google Ads
    action_map = {}
    for key, action_name in conversions.CONVERSION_ACTIONS.items():
        action_map[action_name] = conversions.get_or_create_conversion_action(
            client, customer_id, action_name
        )

    # 2a. Fetch CTA clicks + waitlist signups from Supabase
    supabase_logs = conversions.fetch_supabase_logs(hours=hours)

    # 2b. Fetch purchase conversions from Shopify orders
    shopify_purchases = conversions.fetch_shopify_purchases(hours=hours)

    all_logs = supabase_logs + shopify_purchases

    # 3. Upload everything to Google Ads
    res = conversions.upload_conversions(client, customer_id, all_logs, action_map, dry_run=dry_run)

    log_action("sync_conversions", {
        "hours": hours,
        "dry_run": dry_run,
        "supabase_logs_found": len(supabase_logs),
        "shopify_purchases_found": len(shopify_purchases),
        "total_found": len(all_logs),
        "uploaded": res.get("uploaded", 0),
        "success_count": res.get("success_count", 0),
        "fail_count": res.get("fail_count", 0),
    }, success=True)

    breakdown = {"supabase": len(supabase_logs), "shopify": len(shopify_purchases)}
    return res, all_logs, breakdown


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
            res, logs, breakdown = _run_sync(hours=3, dry_run=False)
            return respond(self, 200, {
                "success": True,
                "source": "cron",
                "logs_found": len(logs),
                "breakdown": breakdown,
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

            res, logs, breakdown = _run_sync(hours=hours, dry_run=dry_run)

            return respond(self, 200, {
                "success": True,
                "hours": hours,
                "dry_run": dry_run,
                "logs_found": len(logs),
                "breakdown": breakdown,
                "google_ads_results": res,
            })
        except Exception as e:
            log_exception("sync_conversions", e)
            return respond(self, 500, {"error": str(e), "trace": traceback.format_exc()})
