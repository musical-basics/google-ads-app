"""
POST /api/sync/conversions
Body: { hours: int (optional, default 48), dry_run: bool (optional, default false) }

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


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if not require_api_key(self):
            return respond(self, 401, {"error": "unauthorized"})
        try:
            body = read_json_body(self)
            hours = int(body.get("hours") or 48)
            dry_run = bool(body.get("dry_run"))

            client = google_ads_client.get_client()
            customer_id = google_ads_client.customer_id()

            # 1. Resolve/create conversion actions in Google Ads
            action_map = {}
            for key, action_name in conversions.CONVERSION_ACTIONS.items():
                action_map[action_name] = conversions.get_or_create_conversion_action(client, customer_id, action_name)

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
