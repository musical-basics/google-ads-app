"""
POST /api/sync/shopify
Body: { since: "YYYY-MM-DD" (optional, defaults to 7 days ago) }

Pulls orders from Shopify, parses UTM attribution, upserts into belgium_ticket_sales.
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
from _lib.supabase_client import upsert_ticket_sales
from _lib import shopify_client, config


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if not require_api_key(self):
            return respond(self, 401, {"error": "unauthorized"})
        try:
            body = read_json_body(self)
            tz = ZoneInfo(config.TIMEZONE)
            if body.get("since"):
                since_iso = body["since"] + "T00:00:00+00:00"
            else:
                since_iso = (datetime.now(tz) - timedelta(days=7)).isoformat()

            nodes = shopify_client.get_orders_since(since_iso)
            rows = []
            skipped = 0
            for n in nodes:
                row = shopify_client.parse_order_to_row(n)
                if row is None:
                    skipped += 1
                    continue
                rows.append(row)
            written = upsert_ticket_sales(rows)
            ad_attributed = sum(1 for r in rows if r.get("ad_attributed"))

            log_action("sync_shopify", {
                "since": since_iso,
                "orders_pulled": len(nodes),
                "tickets_matched": len(rows),
                "ad_attributed": ad_attributed,
                "skipped_non_ticket": skipped,
            }, success=True)
            return respond(self, 200, {
                "since": since_iso,
                "orders_pulled": len(nodes),
                "tickets_matched": len(rows),
                "ad_attributed": ad_attributed,
                "rows_written": written,
            })
        except Exception as e:
            log_exception("sync_shopify", e)
            return respond(self, 500, {"error": str(e), "trace": traceback.format_exc()})
