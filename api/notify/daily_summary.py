"""
POST /api/notify/daily_summary
Body: { date?: "YYYY-MM-DD", to?: "email" }

Renders the daily summary and sends it via Resend.
"""
import os
import sys
import traceback
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from http.server import BaseHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from _lib.http_helpers import require_api_key, respond, read_json_body
from _lib.log import log_action, log_exception
from _lib.summary_text import render_daily_summary
from _lib.email import send_email
from _lib import config


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if not require_api_key(self):
            return respond(self, 401, {"error": "unauthorized"})
        try:
            body = read_json_body(self)
            tz = ZoneInfo(config.TIMEZONE)
            date_str = body.get("date") or (datetime.now(tz).date() - timedelta(days=1)).isoformat()
            text = render_daily_summary(date_str)
            subject = f"Belgium ads daily - {date_str}"
            result = send_email(subject=subject, body=text, to=body.get("to"))
            log_action("notify_daily_summary", {"date": date_str, "resend": result}, success=True)
            return respond(self, 200, {
                "sent": True,
                "date": date_str,
                "resend_id": result.get("id"),
                "preview": text,
            })
        except Exception as e:
            log_exception("notify_daily_summary", e)
            return respond(self, 500, {"error": str(e), "trace": traceback.format_exc()})
