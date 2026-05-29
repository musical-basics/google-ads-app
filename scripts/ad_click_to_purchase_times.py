"""For every paid order whose Shopify landing_site has utm_source=google,
find the matching ad-attributed pageview in analytics_logs and report the
time from ad click to purchase.

Match heuristic: latest pageview before purchase, same utm_campaign,
same country (utm_content if available). IP match is unreliable because
buyers often switch networks between click and purchase (mobile -> home wifi).
"""
import os, json, urllib.parse, urllib.request
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env.local")
load_dotenv(ROOT.parent / "belgium-concert-landing-page" / ".env.local")

ANALYTICS_URL = os.environ["ANALYTICS_SUPABASE_URL"]
ANALYTICS_KEY = os.environ["ANALYTICS_SUPABASE_SERVICE_ROLE_KEY"]
TICKETS_URL   = os.environ["TICKETS_SUPABASE_URL"]
TICKETS_KEY   = os.environ["TICKETS_SUPABASE_SERVICE_ROLE_KEY"]


def fetch(url, key, path, schema):
    req = urllib.request.Request(
        f"{url}/rest/v1/{path}",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept-Profile": schema},
    )
    return json.loads(urllib.request.urlopen(req).read())


def parse_landing_site_utms(landing_site: str) -> dict:
    """Parse utm_* + gclid out of a Shopify landing_site URL or query string."""
    if not landing_site:
        return {}
    # landing_site can be path?qs or just qs
    qs = landing_site.split("?", 1)[1] if "?" in landing_site else landing_site
    out = {}
    for kv in qs.split("&"):
        if "=" in kv:
            k, v = kv.split("=", 1)
            if k.startswith("utm_") or k == "gclid":
                out[k] = urllib.parse.unquote(v)
    return out


def find_matching_pageview(utm_campaign, country, purchase_iso, lookback_days=14):
    """Find the latest pageview in analytics_logs matching utm_campaign +
    country (heuristic) before purchase_iso."""
    purchase = datetime.fromisoformat(purchase_iso.replace("Z","+00:00"))
    start = (purchase - timedelta(days=lookback_days)).isoformat().replace("+00:00", "Z")
    end   = purchase.isoformat().replace("+00:00", "Z")
    qs = urllib.parse.urlencode({
        "select": "created_at,event_name,country,ip_address,metadata",
        "country": f"eq.{country}",
        "event_name": "eq.pageview",
        "created_at": f"gte.{start}",
        "order": "created_at.desc",
        "limit": "200",
    })
    rows = fetch(ANALYTICS_URL, ANALYTICS_KEY,
                 f"analytics_logs?{qs}&created_at=lte.{end}",
                 "concert_analytics")
    for r in rows:
        meta = r.get("metadata") or {}
        if meta.get("utm_campaign") == utm_campaign:
            return r
    return None


# 1. Pull all paid orders
qs = urllib.parse.urlencode({
    "select": "shopify_order_name,customer_email,customer_first_name,customer_last_name,ticket_type,ticket_quantity,order_status,created_at,shopify_payload",
    "order_status": "eq.paid",
    "order": "created_at.asc",
})
orders = fetch(TICKETS_URL, TICKETS_KEY, f"ticket_orders?{qs}", "concert_tickets")
print(f"Found {len(orders)} paid orders total.\n")

ad_orders = []
for o in orders:
    payload = o.get("shopify_payload") or {}
    utms = parse_landing_site_utms(payload.get("landing_site", ""))
    if utms.get("utm_source") == "google":
        ad_orders.append((o, utms))

print(f"{len(ad_orders)} order(s) attributed to Google Ads (utm_source=google):\n")
print(f"{'Order':<8} {'Buyer':<30} {'Type':<6} {'Campaign':<28} {'Click time (UTC)':<25} {'Purchase (UTC)':<25} {'Delta':>10}")
print("-" * 145)

for o, utms in ad_orders:
    name = f"{o.get('customer_first_name','')} {o.get('customer_last_name','')}".strip() or o["customer_email"]
    payload = o.get("shopify_payload") or {}
    addr = (payload.get("customer") or {}).get("default_address") or {}
    country = addr.get("country_code", "")
    campaign = utms.get("utm_campaign", "?")
    purchase_iso = o["created_at"]

    pageview = find_matching_pageview(campaign, country, purchase_iso) if country else None
    if pageview:
        click_iso = pageview["created_at"]
        click_dt = datetime.fromisoformat(click_iso.replace("+00:00","Z").replace("Z","+00:00"))
        purchase_dt = datetime.fromisoformat(purchase_iso.replace("+00:00","Z").replace("Z","+00:00"))
        delta = purchase_dt - click_dt
        total_min = int(delta.total_seconds() / 60)
        if total_min < 60:
            delta_str = f"{total_min}m"
        elif total_min < 24*60:
            delta_str = f"{total_min//60}h{total_min%60:02d}m"
        else:
            delta_str = f"{delta.days}d{(total_min%(24*60))//60}h"
        click_str = click_dt.strftime("%Y-%m-%d %H:%M")
    else:
        delta_str = "(no match)"
        click_str = "-"

    purchase_dt = datetime.fromisoformat(purchase_iso.replace("+00:00","Z").replace("Z","+00:00"))
    purchase_str = purchase_dt.strftime("%Y-%m-%d %H:%M")

    print(f"{o['shopify_order_name']:<8} {name[:28]:<30} {o.get('ticket_type','?'):<6} {campaign[:26]:<28} {click_str:<25} {purchase_str:<25} {delta_str:>10}")
