"""
Conversion upload logic for Google Ads.
Fetches logs from Supabase (CTA clicks, waitlist signups) and Shopify (purchases)
and uploads click conversions to Google Ads.

Rules enforced here:
  - 89-day window: Google Ads rejects conversions older than the click's conversion
    window (max 90 days). We cap at 89 to be safe.
  - Deduplication: each (gclid, event_name) pair is only uploaded once per run,
    and we use gclid+order_id as the order_id field for Shopify purchases.
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from dateutil.parser import parse

from . import google_ads_client

# Map event names → Google Ads conversion action names.
# NOTE: "Shopify Purchase" intentionally differs from the existing WEBPAGE_CODELESS
# "Purchase" action so the upload pipeline creates its own UPLOAD_CLICKS action.
# Click conversions cannot be uploaded to WEBPAGE_CODELESS actions.
CONVERSION_ACTIONS = {
    "cta_click":     "CTA Click",
    "generate_lead": "Waitlist Signup",
    "purchase":      "Shopify Purchase",
}

# Google Ads max conversion window is 90 days; use 89 to be safe.
MAX_CONVERSION_WINDOW_DAYS = 89


def get_or_create_conversion_action(client, customer_id, name):
    """Retrieve the resource name of a conversion action by name, or create it if not found."""
    ga_service = client.get_service("GoogleAdsService")
    query = f"""
        SELECT
            conversion_action.resource_name,
            conversion_action.name,
            conversion_action.status
        FROM conversion_action
        WHERE conversion_action.name = '{name}'
    """
    try:
        rows = list(ga_service.search(customer_id=customer_id, query=query))
        if rows:
            resource_name = rows[0].conversion_action.resource_name
            return resource_name
    except Exception as e:
        print(f"Warning querying conversion action: {e}", file=sys.stderr)

    # Not found — create it
    ca_service = client.get_service("ConversionActionService")
    op = client.get_type("ConversionActionOperation")
    ca = op.create
    ca.name = name
    ca.type_ = client.enums.ConversionActionTypeEnum.UPLOAD_CLICKS

    if name == "Waitlist Signup":
        ca.category = client.enums.ConversionActionCategoryEnum.SUBMIT_LEAD_FORM
    elif name == "Shopify Purchase":
        ca.category = client.enums.ConversionActionCategoryEnum.PURCHASE
    else:
        ca.category = client.enums.ConversionActionCategoryEnum.OUTBOUND_CLICK

    ca.status = client.enums.ConversionActionStatusEnum.ENABLED
    ca.value_settings.default_value = 1.0
    ca.value_settings.default_currency_code = "EUR"

    resp = ca_service.mutate_conversion_actions(customer_id=customer_id, operations=[op])
    resource_name = resp.results[0].resource_name
    return resource_name


def _is_within_window(created_at_str: str) -> bool:
    """Return True if the event is within the 89-day Google Ads conversion window."""
    try:
        dt = parse(created_at_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - dt
        return age.days <= MAX_CONVERSION_WINDOW_DAYS
    except Exception:
        return False


def _click_id_from(source: dict) -> tuple[str | None, str | None, str | None]:
    """Return (gclid, wbraid, gbraid) from a dict (analytics metadata or parsed UTMs).
    Only one will be present per click — gclid for standard web, wbraid/gbraid for
    privacy-restricted (iOS Safari, some Android) flows."""
    return source.get("gclid"), source.get("wbraid"), source.get("gbraid")


def fetch_supabase_logs(hours=48):
    """
    Fetch recent cta_click and generate_lead logs from Supabase analytics_logs.
    Only returns events with a click id (gclid OR wbraid OR gbraid) and within the
    89-day window. Deduplicates by (click_id, event_name).
    """
    from supabase import create_client, ClientOptions
    url = os.environ.get("ANALYTICS_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = os.environ.get("ANALYTICS_SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("Supabase credentials missing (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY)")

    supabase_client = create_client(url, key, options=ClientOptions(schema="concert_analytics"))

    since_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    res = supabase_client.table("analytics_logs").select("*").gte("created_at", since_time).execute()
    rows = res.data or []

    conversions = []
    seen = set()  # dedup by (click_id, event_name)

    for r in rows:
        event_name = r.get("event_name")
        if event_name not in ("cta_click", "generate_lead"):
            continue

        metadata = r.get("metadata") or {}
        gclid, wbraid, gbraid = _click_id_from(metadata)
        click_id = gclid or wbraid or gbraid
        if not click_id:
            continue

        created_at = r.get("created_at", "")
        if not _is_within_window(created_at):
            continue

        dedup_key = (click_id, event_name)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        conversions.append({
            "gclid": gclid,
            "wbraid": wbraid,
            "gbraid": gbraid,
            "created_at": created_at,
            "event_name": event_name,
            "metadata": metadata,
            "conversion_value": 1.0,
            "currency": "EUR",
        })

    return conversions


def fetch_shopify_purchases(hours=48):
    """
    Fetch recent Shopify ticket orders that have a gclid in their landingPageUrl.
    Returns them as conversion dicts compatible with upload_conversions().
    Only returns orders within the 89-day window.
    Deduplicates by (gclid, shopify_order_id).
    """
    from . import shopify_client
    from . import config

    since_iso = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    orders = shopify_client.get_orders_since(since_iso)

    conversions = []
    seen = set()

    for node in orders:
        row = shopify_client.parse_order_to_row(node)
        if not row:
            continue

        gclid, wbraid, gbraid = _click_id_from(row)
        click_id = gclid or wbraid or gbraid
        if not click_id:
            continue

        ordered_at = row.get("ordered_at", "")
        if not _is_within_window(ordered_at):
            continue

        order_id = row["shopify_order_id"]
        dedup_key = (click_id, order_id)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        # Use actual ticket amount as the conversion value
        amount_eur = row.get("amount_cents", 0) / 100.0

        conversions.append({
            "gclid": gclid,
            "wbraid": wbraid,
            "gbraid": gbraid,
            "created_at": ordered_at,
            "event_name": "purchase",
            "metadata": {"shopify_order_id": order_id, "tier": row.get("ticket_tier")},
            "conversion_value": amount_eur if amount_eur > 0 else config.TIER_PRICE_CENTS.get(row.get("ticket_tier", ""), 2900) / 100.0,
            "currency": row.get("currency") or "EUR",
            "order_id": order_id,   # used as external attribution ID
        })

    return conversions


def upload_conversions(client, customer_id, conversions, action_map, dry_run=False):
    """Upload list of conversion dictionaries to Google Ads."""
    if not conversions:
        return {"success_count": 0, "fail_count": 0, "uploaded": 0}

    upload_service = client.get_service("ConversionUploadService")
    ops = []

    for conv in conversions:
        event_name = conv["event_name"]
        action_name = CONVERSION_ACTIONS.get(event_name)
        action_resource = action_map.get(action_name)

        if not action_resource:
            continue

        # Exactly one of gclid / wbraid / gbraid must be set per click conversion.
        gclid = conv.get("gclid")
        wbraid = conv.get("wbraid")
        gbraid = conv.get("gbraid")
        if not (gclid or wbraid or gbraid):
            continue

        # Parse and re-format date for Google Ads (yyyy-mm-dd HH:mm:ss+|-HH:mm)
        dt = parse(conv["created_at"])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S%z")
        # Ensure colon in offset (e.g. +0000 → +00:00)
        if len(formatted_date) > 5 and formatted_date[-5] in ("+", "-") and formatted_date[-3] != ":":
            formatted_date = formatted_date[:-2] + ":" + formatted_date[-2:]

        click_conv = client.get_type("ClickConversion")
        click_conv.conversion_action = action_resource
        if gclid:
            click_conv.gclid = gclid
        elif wbraid:
            click_conv.wbraid = wbraid
        elif gbraid:
            click_conv.gbraid = gbraid
        click_conv.conversion_date_time = formatted_date
        click_conv.conversion_value = float(conv.get("conversion_value", 1.0))
        click_conv.currency_code = conv.get("currency", "EUR")

        # For purchases, set order_id to prevent Google Ads deduplication
        if conv.get("order_id"):
            click_conv.order_id = str(conv["order_id"])

        ops.append(click_conv)

    if dry_run:
        return {"success_count": 0, "fail_count": 0, "uploaded": len(ops), "dry_run": True}

    request = client.get_type("UploadClickConversionsRequest")
    request.customer_id = customer_id
    request.conversions.extend(ops)
    request.partial_failure = True

    resp = upload_service.upload_click_conversions(request=request)

    partial_failure_msg = None
    if resp.partial_failure_error.code != 0:
        partial_failure_msg = resp.partial_failure_error.message

    success_count = 0
    fail_count = 0
    for result in resp.results:
        # A successful upload echoes back at least one click identifier.
        if result.gclid or result.wbraid or result.gbraid:
            success_count += 1
        else:
            fail_count += 1

    return {
        "success_count": success_count,
        "fail_count": fail_count,
        "uploaded": len(ops),
        "partial_failure_msg": partial_failure_msg,
    }
