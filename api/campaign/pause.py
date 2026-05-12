"""
POST /api/campaign/pause
Body: { reason: str }
"""
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from _lib.http_helpers import require_api_key, respond, read_json_body
from _lib.log import log_action, log_exception
from _lib.supabase_client import get_campaign_state, upsert_campaign_state
from _lib import google_ads_client


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if not require_api_key(self):
            return respond(self, 401, {"error": "unauthorized"})
        try:
            body = read_json_body(self)
            reason = body.get("reason") or "no reason supplied"
            state = get_campaign_state()
            if not state or not state.get("resource_name"):
                return respond(self, 404, {"error": "no campaign exists"})
            client = google_ads_client.get_client()
            resource = google_ads_client.pause_campaign(client, state["resource_name"])
            updated = upsert_campaign_state({"campaign_id": state["campaign_id"], "status": "PAUSED"})
            log_action("campaign_paused", {"reason": reason, "resource": resource}, success=True)
            return respond(self, 200, {"paused": True, "reason": reason, "state": updated})
        except Exception as e:
            log_exception("campaign_pause", e)
            return respond(self, 500, {"error": str(e), "trace": traceback.format_exc()})
