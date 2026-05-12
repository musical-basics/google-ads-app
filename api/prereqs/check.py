"""
GET /api/prereqs/check

Verify all 5 prerequisites before any campaign action. Returns 200 with
{ ok: bool, blockers: [{key, message}], info: {...} }.

This endpoint never modifies state. The agent calls it before every action.
"""
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from _lib.http_helpers import require_api_key, respond
from _lib.log import log_exception


def _check_developer_token() -> tuple[bool, str]:
    val = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", "")
    if not val:
        return False, "GOOGLE_ADS_DEVELOPER_TOKEN is empty"
    if val.startswith("PENDING_APPROVAL"):
        return False, f"developer token is still a placeholder ({val}) - approval not yet landed"
    return True, "developer token present"


def _check_google_ads_oauth() -> tuple[bool, str]:
    for k in ("GOOGLE_ADS_CLIENT_ID", "GOOGLE_ADS_CLIENT_SECRET", "GOOGLE_ADS_REFRESH_TOKEN", "GOOGLE_ADS_CUSTOMER_ID"):
        if not os.environ.get(k):
            return False, f"{k} is missing"
    return True, "google ads oauth env complete"


def _check_video_assets() -> tuple[bool, str]:
    landscape = os.environ.get("VIDEO_ID_LANDSCAPE", "")
    portrait = os.environ.get("VIDEO_ID_PORTRAIT", "")
    if not landscape:
        return False, "VIDEO_ID_LANDSCAPE is empty - no YouTube video to attach to the ad"
    msg = f"landscape={landscape}"
    if portrait:
        msg += f", portrait={portrait}"
    return True, msg


def _check_audiences() -> tuple[bool, str]:
    subs = os.environ.get("AUDIENCE_SUBSCRIBERS_ID", "")
    look = os.environ.get("AUDIENCE_LOOKALIKE_ID", "")
    intent = os.environ.get("AUDIENCE_CUSTOM_INTENT_ID", "")
    if not subs and not look and not intent:
        return False, "no audience IDs configured - campaign would target nobody. Set at least AUDIENCE_SUBSCRIBERS_ID or AUDIENCE_CUSTOM_INTENT_ID"
    parts = []
    if subs:
        parts.append(f"subscribers={subs}")
    if look:
        parts.append(f"lookalike={look}")
    if intent:
        parts.append(f"custom_intent={intent}")
    return True, ", ".join(parts)


def _check_shopify_creds() -> tuple[bool, str]:
    for k in ("SHOPIFY_STORE_DOMAIN", "SHOPIFY_CLIENT_ID", "SHOPIFY_CLIENT_SECRET"):
        if not os.environ.get(k):
            return False, f"{k} is missing"
    return True, "shopify client_credentials env complete"


def _check_supabase() -> tuple[bool, str]:
    if not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        return False, "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing"
    return True, "supabase env complete"


def _check_resend() -> tuple[bool, str]:
    if not os.environ.get("RESEND_API_KEY"):
        return False, "RESEND_API_KEY missing - daily summary cannot send"
    if not os.environ.get("NOTIFY_EMAIL_TO"):
        return False, "NOTIFY_EMAIL_TO missing"
    return True, "resend env complete"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not require_api_key(self):
            return respond(self, 401, {"error": "unauthorized"})
        try:
            checks = [
                ("developer_token", _check_developer_token()),
                ("google_ads_oauth", _check_google_ads_oauth()),
                ("video_assets", _check_video_assets()),
                ("audiences", _check_audiences()),
                ("shopify_creds", _check_shopify_creds()),
                ("supabase", _check_supabase()),
                ("resend", _check_resend()),
            ]
            blockers = [{"key": k, "message": msg} for k, (ok, msg) in checks if not ok]
            info = {k: msg for k, (ok, msg) in checks if ok}
            return respond(self, 200, {
                "ok": len(blockers) == 0,
                "blockers": blockers,
                "info": info,
            })
        except Exception as e:
            log_exception("prereqs_check", e)
            return respond(self, 500, {"error": str(e), "trace": traceback.format_exc()})
