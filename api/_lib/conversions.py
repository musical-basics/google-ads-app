"""
Conversion upload logic for Google Ads.
Fetches logs from Supabase and uploads click conversions to Google Ads.
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from dateutil.parser import parse

from . import google_ads_client

CONVERSION_ACTIONS = {
    "cta_click": "CTA Click",
    "generate_lead": "Waitlist Signup"
}

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

    # Not found, create it
    ca_service = client.get_service("ConversionActionService")
    op = client.get_type("ConversionActionOperation")
    ca = op.create
    ca.name = name
    ca.type_ = client.enums.ConversionActionTypeEnum.UPLOAD_CLICKS
    
    if name == "Waitlist Signup":
        ca.category = client.enums.ConversionActionCategoryEnum.SUBMIT_LEAD_FORM
    else:
        ca.category = client.enums.ConversionActionCategoryEnum.OUTBOUND_CLICK
        
    ca.status = client.enums.ConversionActionStatusEnum.ENABLED
    ca.value_settings.default_value = 1.0
    ca.value_settings.default_currency_code = "EUR"
    
    resp = ca_service.mutate_conversion_actions(customer_id=customer_id, operations=[op])
    resource_name = resp.results[0].resource_name
    return resource_name


def fetch_supabase_logs(hours=48):
    """Fetch recent cta_click and generate_lead logs from concert_analytics.analytics_logs."""
    from supabase import create_client, ClientOptions
    url = os.environ.get("ANALYTICS_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = os.environ.get("ANALYTICS_SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("Supabase credentials missing (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY)")

    # Use concert_analytics schema
    supabase_client = create_client(url, key, options=ClientOptions(schema="concert_analytics"))
    
    since_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    
    res = supabase_client.table("analytics_logs").select("*").gte("created_at", since_time).execute()
    rows = res.data or []
    
    conversions = []
    for r in rows:
        event_name = r.get("event_name")
        if event_name not in ("cta_click", "generate_lead"):
            continue
        
        metadata = r.get("metadata") or {}
        gclid = metadata.get("gclid")
        if not gclid:
            continue
            
        conversions.append({
            "gclid": gclid,
            "created_at": r.get("created_at"),
            "event_name": event_name,
            "metadata": metadata
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
        gclid = conv["gclid"]
        action_name = CONVERSION_ACTIONS.get(event_name)
        action_resource = action_map.get(action_name)
        
        if not action_resource:
            continue
            
        # Parse and re-format date for Google Ads (yyyy-mm-dd HH:mm:ss+|-HH:mm)
        dt = parse(conv["created_at"])
        formatted_date = dt.strftime("%Y-%m-%d %H:%M:%S%z")
        if formatted_date[-5] in ("+", "-") and formatted_date[-2] != ":":
            formatted_date = formatted_date[:-2] + ":" + formatted_date[-2:]
            
        click_conv = client.get_type("ClickConversion")
        click_conv.conversion_action = action_resource
        click_conv.gclid = gclid
        click_conv.conversion_date_time = formatted_date
        click_conv.conversion_value = 1.0
        click_conv.currency_code = "EUR"
        
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
        if result.gclid:
            success_count += 1
        else:
            fail_count += 1
            
    return {
        "success_count": success_count,
        "fail_count": fail_count,
        "uploaded": len(ops),
        "partial_failure_msg": partial_failure_msg
    }
