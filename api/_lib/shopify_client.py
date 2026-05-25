"""
Shopify Admin GraphQL client using the new client_credentials flow.
See shopify-eu-pricing.md for context. Tokens are short-lived (~24h) and re-issued
every cold start of this serverless function - acceptable given low call volume.
"""
import os
import requests
from urllib.parse import urlparse, parse_qs

from . import config


_cached_token: str | None = None


def _domain() -> str:
    d = os.environ.get("SHOPIFY_STORE_DOMAIN")
    if not d:
        raise RuntimeError("SHOPIFY_STORE_DOMAIN is missing")
    return d


def _api_version() -> str:
    return os.environ.get("SHOPIFY_API_VERSION", "2025-10")


def refresh_access_token() -> str:
    global _cached_token
    client_id = os.environ.get("SHOPIFY_CLIENT_ID")
    client_secret = os.environ.get("SHOPIFY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("SHOPIFY_CLIENT_ID or SHOPIFY_CLIENT_SECRET missing")
    url = f"https://{_domain()}/admin/oauth/access_token"
    res = requests.post(
        url,
        json={
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        },
        timeout=15,
    )
    res.raise_for_status()
    data = res.json()
    _cached_token = data["access_token"]
    return _cached_token


def _token() -> str:
    if _cached_token:
        return _cached_token
    return refresh_access_token()


def gql(query: str, variables: dict | None = None) -> dict:
    url = f"https://{_domain()}/admin/api/{_api_version()}/graphql.json"
    res = requests.post(
        url,
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": _token(),
        },
        json={"query": query, "variables": variables or {}},
        timeout=30,
    )
    res.raise_for_status()
    body = res.json()
    if "errors" in body and body["errors"]:
        raise RuntimeError(f"Shopify GraphQL errors: {body['errors']}")
    return body["data"]


def get_orders_since(since_iso: str) -> list[dict]:
    """
    Pull orders created since `since_iso` (ISO 8601). Returns raw GraphQL nodes.
    Filters at the API level for tickets only (matching ticket variant IDs).

    Shopify's order search language silently drops orders when the timestamp
    carries a `+HH:MM` offset (it expects Z or no zone). Normalize to Z.
    """
    out: list[dict] = []
    cursor: str | None = None
    normalized = since_iso.replace("+00:00", "Z")
    query_str = f"created_at:>={normalized}"
    q = """
    query($query: String, $first: Int, $after: String) {
      orders(query: $query, first: $first, after: $after, sortKey: CREATED_AT) {
        pageInfo { hasNextPage endCursor }
        nodes {
          id
          name
          createdAt
          email
          totalPriceSet { shopMoney { amount currencyCode } }
          landingPageUrl
          referrerUrl
          customAttributes { key value }
          lineItems(first: 10) {
            nodes { variant { id } quantity }
          }
        }
      }
    }
    """
    while True:
        data = gql(q, {"query": query_str, "first": 250, "after": cursor})
        page = data["orders"]
        out.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    return out


def parse_order_to_row(node: dict) -> dict | None:
    """
    Convert a Shopify GraphQL order node into a belgium_ticket_sales row.
    Returns None if no Belgium ticket variant is in the order.
    """
    variant_ids = []
    for li in node.get("lineItems", {}).get("nodes", []):
        v = (li.get("variant") or {}).get("id") or ""
        if "/" in v:
            variant_ids.append(v.split("/")[-1])
    tier = None
    for vid in variant_ids:
        if vid in config.TICKET_TIERS:
            tier = config.TICKET_TIERS[vid]
            break
    if tier is None:
        return None

    landing = node.get("landingPageUrl") or ""
    utms = _extract_utms(landing, node.get("customAttributes") or [])
    ad_attributed = utms.get("utm_campaign") == config.UTM_CAMPAIGN

    amount = float(((node.get("totalPriceSet") or {}).get("shopMoney") or {}).get("amount") or 0)
    currency = ((node.get("totalPriceSet") or {}).get("shopMoney") or {}).get("currencyCode")

    gid = node["id"]
    order_id = gid.split("/")[-1] if "/" in gid else gid

    return {
        "shopify_order_id": order_id,
        "order_name": node.get("name"),
        "customer_email": node.get("email"),
        "ticket_tier": tier,
        "amount_cents": int(round(amount * 100)),
        "currency": currency,
        "utm_source": utms.get("utm_source"),
        "utm_medium": utms.get("utm_medium"),
        "utm_campaign": utms.get("utm_campaign"),
        "utm_content": utms.get("utm_content"),
        "utm_term": utms.get("utm_term"),
        "gclid": utms.get("gclid"),
        "landing_site": landing,
        "ordered_at": node.get("createdAt"),
        "ad_attributed": ad_attributed,
        "raw": node,
    }


def _extract_utms(landing_url: str, custom_attrs: list[dict]) -> dict:
    """
    Pull UTM params AND gclid from the landing URL query string, falling back
    to order custom attributes (cart attributes preserved through checkout).
    """
    utms: dict[str, str] = {}
    if landing_url:
        qs = parse_qs(urlparse(landing_url).query)
        for k in ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "gclid"):
            if k in qs and qs[k]:
                utms[k] = qs[k][0]
    for attr in custom_attrs or []:
        key = (attr.get("key") or "").lower()
        if key in ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "gclid"):
            utms.setdefault(key, attr.get("value") or "")
    return utms
