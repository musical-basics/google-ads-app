"""Print the raw Shopify landing_site / referring_site for a buyer's order,
and scan analytics_logs in a tight window before the purchase for any
pageviews that geo-match."""
import os, sys, json, urllib.parse, urllib.request
from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta, datetime

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env.local")
load_dotenv(ROOT.parent / "belgium-concert-landing-page" / ".env.local")

ANALYTICS_URL = os.environ["ANALYTICS_SUPABASE_URL"]
ANALYTICS_KEY = os.environ["ANALYTICS_SUPABASE_SERVICE_ROLE_KEY"]
TICKETS_URL   = os.environ["TICKETS_SUPABASE_URL"]
TICKETS_KEY   = os.environ["TICKETS_SUPABASE_SERVICE_ROLE_KEY"]

email = sys.argv[1] if len(sys.argv) > 1 else "jacobsolaf@gmail.com"


def fetch(url, key, path, schema):
    req = urllib.request.Request(
        f"{url}/rest/v1/{path}",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept-Profile": schema},
    )
    return json.loads(urllib.request.urlopen(req).read())


# Get order
qs = urllib.parse.urlencode({
    "select": "shopify_order_name,created_at,shopify_payload",
    "customer_email": f"eq.{email}",
})
orders = fetch(TICKETS_URL, TICKETS_KEY, f"ticket_orders?{qs}", "concert_tickets")
if not orders:
    print(f"no order for {email}")
    sys.exit(0)

o = orders[0]
payload = o["shopify_payload"]
print(f"Order {o['shopify_order_name']} created {o['created_at']}\n")

# Shopify landing_site = the URL the buyer FIRST hit on the store (with UTMs)
# referring_site       = the http referrer when they arrived
for key in ("landing_site", "landing_site_ref", "referring_site", "source_name",
            "source_identifier", "source_url", "browser_ip", "client_details"):
    if key in payload:
        print(f"  {key}: {payload[key]}")

# customer note_attributes (we already saw these were empty for this order)
# Also check customer-level data for default source/utm tags
cust = payload.get("customer", {})
for key in ("note", "tags", "default_address"):
    if cust.get(key):
        print(f"  customer.{key}: {cust[key]}")

# Scan analytics_logs in a 24h window before purchase, from Belgium
ts = datetime.fromisoformat(o["created_at"].replace("+00:00", "Z").replace("Z","+00:00"))
start = (ts - timedelta(hours=24)).isoformat().replace("+00:00", "Z")
end   = (ts + timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
print(f"\nScanning analytics_logs Belgium pageviews from {start} to {end}...\n")
qs = urllib.parse.urlencode({
    "select": "created_at,event_name,ip_address,country,metadata",
    "country": "eq.BE",
    "event_name": "eq.pageview",
    "created_at": f"gte.{start}",
    "order": "created_at.asc",
})
rows = fetch(ANALYTICS_URL, ANALYTICS_KEY, f"analytics_logs?{qs}&created_at=lte.{end}", "concert_analytics")
print(f"{len(rows)} BE pageviews in window. Filtering for likely match:\n")
for r in rows:
    meta = r.get("metadata") or {}
    city = meta.get("city", "")
    landing = meta.get("landing_url", "")
    has_utm = any(k in meta for k in ("utm_source","gclid"))
    marker = "  *** UTM ***" if has_utm else ""
    print(f"  {r['created_at']} {city:<20} {r['ip_address'][:45]:<45}{marker}")
    if has_utm:
        for k in ("utm_source","utm_medium","utm_campaign","utm_content","gclid","landing_url","referrer"):
            if meta.get(k):
                print(f"      {k}: {meta[k]}")
