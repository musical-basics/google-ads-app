"""For every paid Belgium-concert order, report which A/B variant the
buyer actually saw at landing time.

Two data sources:
1. concert_tickets.ticket_orders.attribution_detail.ab_variant (set by the
   Shopify webhook deployed 2026-06-10 02:58 CEST). Reliable for orders
   AFTER that timestamp.
2. For older orders or when attribution_detail.ab_variant is null, fall
   back to scanning analytics_logs by IP / gclid for the first pageview
   in the order's lookback window.

Also flags orders where the buyer landed AFTER the variant-T force
(2026-06-10 21:38 CEST = 19:38 UTC), since those are not real A/B signal."""
import os, json, urllib.parse, urllib.request, re
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env.local")
load_dotenv(ROOT.parent / "belgium-concert-landing-page" / ".env.local")

TICKETS_URL = os.environ["TICKETS_SUPABASE_URL"]
TICKETS_KEY = os.environ["TICKETS_SUPABASE_SERVICE_ROLE_KEY"]
ANALYTICS_URL = os.environ["ANALYTICS_SUPABASE_URL"]
ANALYTICS_KEY = os.environ["ANALYTICS_SUPABASE_SERVICE_ROLE_KEY"]

FORCE_T_AT = datetime.fromisoformat("2026-06-10T19:38:00+00:00")  # 21:38 CEST


def fetch(url, key, path, schema):
    req = urllib.request.Request(
        f"{url}/rest/v1/{path}",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept-Profile": schema},
    )
    return json.loads(urllib.request.urlopen(req).read())


def variant_from_analytics(browser_ip, gclid, purchase_iso):
    """Scan analytics_logs near purchase time for matching pageview, return ab_variant."""
    purchase_dt = datetime.fromisoformat(purchase_iso.replace("+00:00", "Z").replace("Z", "+00:00"))
    start = (purchase_dt - timedelta(hours=48)).isoformat().replace("+00:00", "Z")
    end = (purchase_dt + timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    # Try by IP first
    if browser_ip:
        qs = urllib.parse.urlencode({
            "select": "created_at,metadata",
            "ip_address": f"eq.{browser_ip}",
            "event_name": "eq.pageview",
            "created_at": f"gte.{start}",
            "order": "created_at.asc",
        })
        try:
            rows = fetch(ANALYTICS_URL, ANALYTICS_KEY, f"analytics_logs?{qs}&created_at=lte.{end}", "concert_analytics")
            for r in rows:
                m = r.get("metadata") or {}
                if m.get("ab_variant"):
                    return (m["ab_variant"], "by_ip", r["created_at"])
        except Exception:
            pass
    # Fall back to gclid
    if gclid:
        qs = urllib.parse.urlencode({
            "select": "created_at,metadata",
            "metadata->>gclid": f"eq.{gclid}",
            "event_name": "eq.pageview",
            "order": "created_at.asc",
        })
        try:
            rows = fetch(ANALYTICS_URL, ANALYTICS_KEY, f"analytics_logs?{qs}", "concert_analytics")
            for r in rows:
                m = r.get("metadata") or {}
                if m.get("ab_variant"):
                    return (m["ab_variant"], "by_gclid", r["created_at"])
        except Exception:
            pass
    return (None, None, None)


def parse_gclid_from_payload(payload):
    landing = (payload or {}).get("landing_site", "")
    m = re.search(r"gclid=([A-Za-z0-9_\-]+)", landing)
    if m: return m.group(1)
    m = re.search(r"attributes\[gclid\]=([A-Za-z0-9_\-]+)", landing)
    if m: return m.group(1)
    return None


# Pull all paid orders. Note: the 004 attribution migration was committed
# to the LP repo but never applied to the live DB, so we attribute purely
# by analytics_logs lookup here.
qs = urllib.parse.urlencode({
    "select": "shopify_order_name,customer_email,customer_first_name,customer_last_name,ticket_type,ticket_quantity,created_at,shopify_payload",
    "order_status": "eq.paid",
    "order": "created_at.asc",
})
orders = fetch(TICKETS_URL, TICKETS_KEY, f"ticket_orders?{qs}", "concert_tickets")

print(f"=== Variant attribution for {len(orders)} paid orders ===\n")
print(f"{'ORDER':<7} {'TIME (UTC)':<17} {'BUYER':<22} {'TIER':<10} {'SRC':<13} {'VARIANT':<8} {'BASIS':<14} POST-FORCE-T?")
print("-" * 115)

variant_counts = {}
src_counts = {}
ad_attributed = []

for o in orders:
    name = (f"{o.get('customer_first_name') or ''} {o.get('customer_last_name') or ''}").strip() or o["customer_email"]
    purchase_dt = datetime.fromisoformat(o["created_at"].replace("+00:00", "Z").replace("Z", "+00:00"))
    post_t = "yes (forced T)" if purchase_dt >= FORCE_T_AT else ""

    # Source: parse landing_site for ad attribution
    payload = o.get("shopify_payload") or {}
    landing = payload.get("landing_site", "")
    if "utm_source=google" in landing or "gclid" in landing or "gbraid" in landing:
        src = "google_ads"
    elif "utm_source=musicalbasics" in landing or "utm_medium=email" in landing or re.search(r"[?&](sid|cid)=", landing):
        src = "email"
    elif "youtube.com" in (payload.get("referring_site") or "") or "youtu.be" in (payload.get("referring_site") or ""):
        src = "youtube_organic"
    else:
        src = "direct_unknown"
    src_counts[src] = src_counts.get(src, 0) + 1

    # Variant: scan analytics_logs by IP/gclid for first pageview's ab_variant
    browser_ip = payload.get("browser_ip")
    gclid = parse_gclid_from_payload(payload)
    variant, method, when = variant_from_analytics(browser_ip, gclid, o["created_at"])
    basis = method or ""

    variant_label = variant or "(unknown)"
    variant_counts[variant_label] = variant_counts.get(variant_label, 0) + 1

    print(f"{o['shopify_order_name']:<7} {o['created_at'][:16]:<17} {name[:20]:<22} {(o.get('ticket_type') or '?')[:8]:<10} {src[:11]:<13} {variant_label:<8} {basis:<14} {post_t}")

    if src == "google_ads":
        ad_attributed.append((o["shopify_order_name"], name, variant_label, src))

print("\n=== Distribution ===\n")
print("By variant:")
for v, n in sorted(variant_counts.items(), key=lambda x: -x[1]):
    print(f"  {v:<10}  {n} order(s)")

print("\nBy attribution source:")
for s, n in sorted(src_counts.items(), key=lambda x: -x[1]):
    print(f"  {s:<20}  {n} order(s)")

print("\n=== Ad-attributed buyers and their variants ===")
for order, name, v, src in ad_attributed:
    print(f"  {order:<7} {name[:25]:<27} variant={v}")
