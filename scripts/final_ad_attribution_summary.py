"""Final accounting: every paid order, whether it came from Google Ads,
total ad spend, total ad revenue, ROAS. Two attribution sources:
  1. Shopify landing_site has utm_source=google (LP-side attribution)
  2. Google Ads' own Shopify Purchase metrics (gclid-cookie attribution)
Both are reported. Organic orders are listed for context."""
import os, sys, json, urllib.parse, urllib.request, re
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env.local")
load_dotenv(ROOT.parent / "belgium-concert-landing-page" / ".env.local")

sys.path.insert(0, str(ROOT))
from api._lib.google_ads_client import get_client, customer_id

TICKETS_URL = os.environ["TICKETS_SUPABASE_URL"]
TICKETS_KEY = os.environ["TICKETS_SUPABASE_SERVICE_ROLE_KEY"]


def fetch_tickets(path, schema="concert_tickets"):
    req = urllib.request.Request(
        f"{TICKETS_URL}/rest/v1/{path}",
        headers={"apikey": TICKETS_KEY, "Authorization": f"Bearer {TICKETS_KEY}", "Accept-Profile": schema},
    )
    return json.loads(urllib.request.urlopen(req).read())


def parse_utm(landing_site: str) -> dict:
    if not landing_site:
        return {}
    qs = landing_site.split("?", 1)[1] if "?" in landing_site else landing_site
    out = {}
    for kv in qs.split("&"):
        if "=" in kv:
            k, v = kv.split("=", 1)
            if k.startswith("utm_") or k in ("gclid", "gbraid", "wbraid"):
                out[k] = urllib.parse.unquote(v)
            # Shopify cart attributes also use attributes[gclid]
            mch = re.match(r"attributes\[(gclid|gbraid|wbraid)\]", k)
            if mch:
                out[mch.group(1)] = urllib.parse.unquote(v)
    return out


def order_total_eur(o):
    """Extract paid total in EUR from shopify_payload."""
    p = o.get("shopify_payload") or {}
    for k in ("current_total_price", "total_price", "total_price_set"):
        v = p.get(k)
        if isinstance(v, str):
            try: return float(v)
            except: pass
        if isinstance(v, dict):
            sm = (v.get("shop_money") or {}).get("amount")
            if sm:
                try: return float(sm)
                except: pass
    return 0.0


# === Pull all paid orders ===
qs = urllib.parse.urlencode({
    "select": "shopify_order_name,customer_email,customer_first_name,customer_last_name,ticket_type,ticket_quantity,order_status,created_at,shopify_payload",
    "order_status": "eq.paid",
    "order": "created_at.asc",
})
orders = fetch_tickets(f"ticket_orders?{qs}")

# === Build classification ===
ad_orders = []
direct_orders = []
for o in orders:
    payload = o.get("shopify_payload") or {}
    landing = payload.get("landing_site") or ""
    utms = parse_utm(landing)
    is_ad_shopify = utms.get("utm_source") == "google" or "gclid" in utms or "gbraid" in utms or "wbraid" in utms
    o["_utms"] = utms
    o["_total_eur"] = order_total_eur(o)
    if is_ad_shopify:
        ad_orders.append(o)
    else:
        direct_orders.append(o)

# === Pull Google Ads' own click-attributed Shopify Purchase metrics ===
client = get_client()
svc = client.get_service("GoogleAdsService")
cid = customer_id()

gads_purchases = []
gads_spend_total = 0
q_conv = """
SELECT segments.date, campaign.name, ad_group.name,
       segments.conversion_action_name,
       metrics.conversions, metrics.conversions_value,
       metrics.view_through_conversions
FROM ad_group
WHERE segments.date >= '2026-05-13' AND segments.date <= '2026-06-13'
  AND segments.conversion_action_name = 'Shopify Purchase'
  AND metrics.all_conversions > 0
ORDER BY segments.date ASC
"""
for r in svc.search(customer_id=cid, query=q_conv):
    gads_purchases.append({
        "date": r.segments.date,
        "campaign": r.campaign.name,
        "ad_group": r.ad_group.name,
        "conv": r.metrics.conversions,
        "value": r.metrics.conversions_value,
        "vt": r.metrics.view_through_conversions,
    })

# === Pull lifetime ad spend ===
q_spend = """
SELECT segments.date, metrics.cost_micros
FROM campaign
WHERE segments.date >= '2026-05-13' AND segments.date <= '2026-06-13'
"""
for r in svc.search(customer_id=cid, query=q_spend):
    gads_spend_total += r.metrics.cost_micros / 1_000_000

# === Print everything ===
print("=" * 90)
print(f"{'ORDER':<7} {'BUYER':<28} {'TIER':<10} {'QTY':>3} {'TOTAL':>9}   ATTRIBUTION")
print("=" * 90)
print("\n--- Google Ads attributed (via Shopify landing_site UTMs / gclid / gbraid) ---")
ad_rev_shopify = 0
for o in ad_orders:
    name = (f"{o.get('customer_first_name') or ''} {o.get('customer_last_name') or ''}").strip() or o["customer_email"]
    ad_rev_shopify += o["_total_eur"]
    utms = o["_utms"]
    sig = utms.get("utm_campaign") or utms.get("gclid", "(gclid only)")[:30]
    print(f"  {o['shopify_order_name']:<7} {name[:26]:<28} {o.get('ticket_type','?'):<10} {o.get('ticket_quantity',0):>3} EUR{o['_total_eur']:>6.2f}   {sig}")

print(f"\n  Subtotal ad-attributed orders: {len(ad_orders)}  revenue=EUR{ad_rev_shopify:.2f}")

print("\n--- Direct / organic per Shopify landing_site ---")
direct_rev = 0
for o in direct_orders:
    name = (f"{o.get('customer_first_name') or ''} {o.get('customer_last_name') or ''}").strip() or o["customer_email"]
    direct_rev += o["_total_eur"]
    print(f"  {o['shopify_order_name']:<7} {name[:26]:<28} {o.get('ticket_type','?'):<10} {o.get('ticket_quantity',0):>3} EUR{o['_total_eur']:>6.2f}   direct/organic")

print(f"\n  Subtotal direct/organic orders: {len(direct_orders)}  revenue=EUR{direct_rev:.2f}")

print("\n" + "=" * 90)
print("GOOGLE ADS' OWN ATTRIBUTION (gclid cookie tracking, includes return-direct buyers)")
print("=" * 90)
print(f"{'DATE':<12} {'CAMPAIGN':<46} {'AD GROUP':<24} {'CONV':>6} {'VALUE':>9}")
gads_total_conv = 0; gads_total_val = 0
for p in gads_purchases:
    print(f"  {p['date']:<12} {p['campaign'][:44]:<46} {p['ad_group'][:22]:<24} {p['conv']:>6.2f} EUR{p['value']:>6.2f}")
    gads_total_conv += p["conv"]
    gads_total_val += p["value"]
print(f"\nGoogle Ads sees: {gads_total_conv:.1f} conversions, EUR{gads_total_val:.2f} revenue")

print("\n" + "=" * 90)
print("FINAL TALLY")
print("=" * 90)
print(f"  Total paid orders:                    {len(orders)}")
print(f"  Total revenue (all orders):           EUR{ad_rev_shopify + direct_rev:.2f}")
print()
print(f"  Ad-attributed via Shopify landing_site: {len(ad_orders)} orders, EUR{ad_rev_shopify:.2f}")
print(f"  Ad-attributed via Google Ads gclid:     {gads_total_conv:.1f} conv, EUR{gads_total_val:.2f}")
print()
print(f"  Total ad spend (5/13 -> 6/13):        EUR{gads_spend_total:.2f}")
print(f"  ROAS (Shopify view):                  {ad_rev_shopify/gads_spend_total:.2f}x")
print(f"  ROAS (Google Ads view):               {gads_total_val/gads_spend_total:.2f}x")
