"""Look up a specific click in concert_analytics.analytics_logs by IP/time.

Reads ANALYTICS_SUPABASE_URL and ANALYTICS_SUPABASE_SERVICE_ROLE_KEY from
env (set them in .env.local on the landing-page repo, or export before running).
"""
import os, sys, json, urllib.parse, urllib.request
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env.local")
load_dotenv(Path(__file__).resolve().parent.parent.parent / "belgium-concert-landing-page" / ".env.local")

URL = os.environ["ANALYTICS_SUPABASE_URL"]
KEY = os.environ["ANALYTICS_SUPABASE_SERVICE_ROLE_KEY"]

ip    = sys.argv[1] if len(sys.argv) > 1 else "81.164.73.194"
start = sys.argv[2] if len(sys.argv) > 2 else "2026-05-23T17:40:00Z"
end   = sys.argv[3] if len(sys.argv) > 3 else "2026-05-23T17:55:00Z"

qs = urllib.parse.urlencode({
    "select": "created_at,event_name,path,ip_address,country,metadata",
    "ip_address": f"eq.{ip}",
    "created_at": f"gte.{start}",
    "order": "created_at.asc",
})
req = urllib.request.Request(
    f"{URL}/rest/v1/analytics_logs?{qs}&created_at=lte.{end}",
    headers={
        "apikey": KEY,
        "Authorization": f"Bearer {KEY}",
        "Accept-Profile": "concert_analytics",
    },
)
with urllib.request.urlopen(req) as r:
    rows = json.loads(r.read())

for row in rows:
    print(json.dumps(row, indent=2))
print(f"\n{len(rows)} rows")
