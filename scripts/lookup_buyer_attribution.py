"""For a given buyer email, find the order in concert_tickets.ticket_orders
and cross-reference analytics_logs to see what UTM / referrer / IP brought
them to the landing page. Tells us whether they came from Google Ads."""
import os, sys, json, urllib.parse, urllib.request
from pathlib import Path
from dotenv import load_dotenv
from datetime import timedelta, datetime

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env.local")
load_dotenv(ROOT.parent / "belgium-concert-landing-page" / ".env.local")

ANALYTICS_URL = os.environ["ANALYTICS_SUPABASE_URL"]
ANALYTICS_KEY = os.environ["ANALYTICS_SUPABASE_SERVICE_ROLE_KEY"]
TICKETS_URL   = os.environ.get("TICKETS_SUPABASE_URL", ANALYTICS_URL)
TICKETS_KEY   = os.environ.get("TICKETS_SUPABASE_SERVICE_ROLE_KEY", ANALYTICS_KEY)

email = sys.argv[1] if len(sys.argv) > 1 else "jacobsolaf@gmail.com"


def fetch(url, key, path, schema):
    req = urllib.request.Request(
        f"{url}/rest/v1/{path}",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Accept-Profile": schema,
        },
    )
    return json.loads(urllib.request.urlopen(req).read())


def find_order(url, key):
    qs = urllib.parse.urlencode({
        "select": "id,shopify_order_id,shopify_order_name,customer_email,ticket_type,ticket_quantity,order_status,created_at,shopify_payload",
        "customer_email": f"eq.{email}",
    })
    return fetch(url, key, f"ticket_orders?{qs}", "concert_tickets")


print(f"Looking up orders for {email}...\n")
orders = []
for url, key, label in [(ANALYTICS_URL, ANALYTICS_KEY, "analytics project"),
                         (TICKETS_URL, TICKETS_KEY, "tickets project")]:
    try:
        orders = find_order(url, key)
        if orders:
            print(f"Found {len(orders)} order(s) in {label}")
            break
    except Exception as e:
        print(f"({label}: {e})")

if not orders:
    print(f"No order found for {email}")
    sys.exit(0)

for o in orders:
    print(f"\n=== Order {o.get('shopify_order_name') or o.get('shopify_order_id')} ===")
    print(f"  Created: {o['created_at']}")
    print(f"  Status:  {o['order_status']}")
    print(f"  Type:    {o.get('ticket_type')}  qty={o.get('ticket_quantity')}")

    payload = o.get("shopify_payload") or {}
    note_attrs = payload.get("note_attributes") or []
    landing_url = None
    utms = {}
    for attr in note_attrs:
        n = attr.get("name", "")
        v = attr.get("value", "")
        if n in ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "gclid", "landing_url", "referrer"):
            utms[n] = v
            if n == "landing_url":
                landing_url = v

    print(f"\n  Shopify note_attributes (UTM trail):")
    if utms:
        for k, v in utms.items():
            print(f"    {k} = {v}")
    else:
        print(f"    (none — Shopify checkout didn't capture UTMs)")

    # Try to find the IP via customer info in shopify_payload
    customer = payload.get("customer") or {}
    browser_ip = payload.get("browser_ip") or payload.get("client_details", {}).get("browser_ip")
    print(f"\n  Customer:    {customer.get('first_name','?')} {customer.get('last_name','?')}")
    print(f"  Browser IP:  {browser_ip or '(not in payload)'}")
    if customer.get("default_address"):
        addr = customer["default_address"]
        print(f"  Address:     {addr.get('city')}, {addr.get('country')}")

    # Pull analytics_logs by IP if we have one
    if browser_ip:
        print(f"\n  Analytics_logs for IP {browser_ip}:")
        ts = datetime.fromisoformat(o["created_at"].replace("Z","+00:00"))
        start = (ts - timedelta(days=14)).isoformat()
        end   = (ts + timedelta(hours=2)).isoformat()
        qs = urllib.parse.urlencode({
            "select": "created_at,event_name,path,country,metadata",
            "ip_address": f"eq.{browser_ip}",
            "created_at": f"gte.{start}",
            "order": "created_at.asc",
        })
        try:
            rows = fetch(ANALYTICS_URL, ANALYTICS_KEY, f"analytics_logs?{qs}&created_at=lte.{end}", "concert_analytics")
            if not rows:
                print(f"    (no analytics_logs rows for this IP in the 14 days before purchase)")
            for r in rows:
                meta = r.get("metadata") or {}
                attribution = {k: meta[k] for k in ("utm_source","utm_medium","utm_campaign","utm_content","gclid","referrer") if k in meta}
                print(f"    {r['created_at']} {r['event_name']:<10} {r.get('country','')} {json.dumps(attribution) if attribution else ''}")
        except Exception as e:
            print(f"    ERROR querying analytics_logs: {e}")
