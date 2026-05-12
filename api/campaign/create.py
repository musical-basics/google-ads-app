"""
POST /api/campaign/create

Body: {
  daily_budget_cents: int (required),
  total_budget_cents: int (required),
  video_id_landscape: str (optional, defaults to VIDEO_ID_LANDSCAPE env),
  video_id_portrait: str (optional),
  audience_subscribers_id: str (optional),
  audience_lookalike_id: str (optional),
  audience_custom_intent_id: str (optional),
  dry_run: bool (optional, default false)
}

Idempotent: if a campaign already exists in Supabase, returns the existing state
instead of creating a duplicate. Campaign is created in PAUSED state - call
/api/campaign/resume to enable.
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
            daily = int(body.get("daily_budget_cents") or 0)
            total = int(body.get("total_budget_cents") or 0)
            if daily <= 0 or total <= 0:
                return respond(self, 400, {"error": "daily_budget_cents and total_budget_cents are required and must be > 0"})

            existing = get_campaign_state()
            if existing and existing.get("campaign_id") and not body.get("force"):
                return respond(self, 200, {
                    "already_exists": True,
                    "state": existing,
                })

            video_landscape = body.get("video_id_landscape") or os.environ.get("VIDEO_ID_LANDSCAPE")
            if not video_landscape:
                return respond(self, 400, {"error": "video_id_landscape missing (body or VIDEO_ID_LANDSCAPE env)"})

            client = google_ads_client.get_client()
            result = google_ads_client.create_campaign(
                client=client,
                daily_budget_cents=daily,
                video_id_landscape=video_landscape,
                video_id_portrait=body.get("video_id_portrait") or os.environ.get("VIDEO_ID_PORTRAIT"),
                audience_subscribers_id=body.get("audience_subscribers_id") or os.environ.get("AUDIENCE_SUBSCRIBERS_ID"),
                audience_lookalike_id=body.get("audience_lookalike_id") or os.environ.get("AUDIENCE_LOOKALIKE_ID"),
                audience_custom_intent_id=body.get("audience_custom_intent_id") or os.environ.get("AUDIENCE_CUSTOM_INTENT_ID"),
                dry_run=bool(body.get("dry_run")),
            )

            if body.get("dry_run"):
                log_action("campaign_create_dry_run", {"plan": result}, success=True)
                return respond(self, 200, {"dry_run": True, "plan": result})

            state_row = {
                "campaign_id": result["campaign_id"],
                "resource_name": result["campaign_resource"],
                "ad_group_subscribers_id": result["ad_group_subscribers"].split("/")[-1],
                "ad_group_lookalike_id": result["ad_group_lookalike"].split("/")[-1],
                "status": "PAUSED",
                "daily_budget_cents": daily,
                "total_budget_cents": total,
                "video_id_landscape": video_landscape,
                "video_id_portrait": body.get("video_id_portrait") or os.environ.get("VIDEO_ID_PORTRAIT"),
            }
            saved = upsert_campaign_state(state_row)
            log_action("campaign_created", {"result": result}, success=True)
            return respond(self, 201, {"created": True, "state": saved, "google_ads": result})
        except Exception as e:
            log_exception("campaign_create", e)
            return respond(self, 500, {"error": str(e), "trace": traceback.format_exc()})
