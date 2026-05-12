"""
GET /api/campaign/status

Returns the current Supabase-tracked state plus live status from Google Ads
(if the campaign exists and credentials are configured).
"""
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from _lib.http_helpers import require_api_key, respond
from _lib.log import log_exception
from _lib.supabase_client import get_campaign_state
from _lib import google_ads_client


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not require_api_key(self):
            return respond(self, 401, {"error": "unauthorized"})
        try:
            state = get_campaign_state()
            if not state or not state.get("resource_name"):
                return respond(self, 200, {"exists": False, "state": None, "live": None})

            live = None
            live_error = None
            try:
                client = google_ads_client.get_client()
                live = google_ads_client.get_campaign_status(client, state["resource_name"])
            except Exception as e:
                live_error = str(e)
            return respond(self, 200, {
                "exists": True,
                "state": state,
                "live": live,
                "live_error": live_error,
            })
        except Exception as e:
            log_exception("campaign_status", e)
            return respond(self, 500, {"error": str(e), "trace": traceback.format_exc()})
