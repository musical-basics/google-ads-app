"""
POST /api/guardrails/check
Body: { enforce: bool (optional, default false) }

Evaluates hard + soft rules. If enforce=true and a hard rule fires, pauses the
campaign and records the action. Returns the triggered rules either way.
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
from _lib import guardrails, google_ads_client


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if not require_api_key(self):
            return respond(self, 401, {"error": "unauthorized"})
        try:
            body = read_json_body(self)
            enforce = bool(body.get("enforce"))

            result = guardrails.evaluate()
            actions: list[dict] = []

            if enforce and result["hard"]:
                state = get_campaign_state()
                if state and state.get("resource_name") and state.get("status") != "PAUSED":
                    try:
                        client = google_ads_client.get_client()
                        google_ads_client.pause_campaign(client, state["resource_name"])
                        upsert_campaign_state({"campaign_id": state["campaign_id"], "status": "PAUSED"})
                        actions.append({
                            "action": "paused",
                            "triggered_by": [r["rule"] for r in result["hard"]],
                        })
                        log_action("guardrail_auto_pause", {
                            "rules": result["hard"],
                            "snapshot": result["snapshot"],
                        }, success=True)
                    except Exception as e:
                        log_exception("guardrail_pause_failed", e)
                        actions.append({"action": "pause_failed", "error": str(e)})

            return respond(self, 200, {
                "enforce": enforce,
                "hard": result["hard"],
                "soft": result["soft"],
                "snapshot": result["snapshot"],
                "actions": actions,
            })
        except Exception as e:
            log_exception("guardrails_check", e)
            return respond(self, 500, {"error": str(e), "trace": traceback.format_exc()})
