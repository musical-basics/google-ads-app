"""
GET /api/summary/daily?date=YYYY-MM-DD&format=text|json

Returns the plain-text daily summary block from the spec.
Default date is yesterday in TIMEZONE.
"""
import os
import sys
import traceback
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from http.server import BaseHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from _lib.http_helpers import require_api_key, respond, read_query
from _lib.log import log_exception
from _lib.summary_text import render_daily_summary
from _lib import config


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if not require_api_key(self):
            return respond(self, 401, {"error": "unauthorized"})
        try:
            qs = read_query(self)
            tz = ZoneInfo(config.TIMEZONE)
            date_str = qs.get("date") or (datetime.now(tz).date() - timedelta(days=1)).isoformat()
            text = render_daily_summary(date_str)
            fmt = qs.get("format", "json")
            if fmt == "text":
                return respond(self, 200, text)
            return respond(self, 200, {"date": date_str, "text": text})
        except Exception as e:
            log_exception("summary_daily", e)
            return respond(self, 500, {"error": str(e), "trace": traceback.format_exc()})
