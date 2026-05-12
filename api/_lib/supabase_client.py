"""
Thin Supabase wrapper. Service-role key only - server-side use.
All tables live in the `ads` schema (set as the default for this client).
"""
import os
from supabase import create_client, Client, ClientOptions


_client: Client | None = None
SCHEMA = "ads"


def supabase() -> Client:
    global _client
    if _client is None:
        url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing")
        _client = create_client(url, key, options=ClientOptions(schema=SCHEMA))
    return _client


def get_campaign_state() -> dict | None:
    res = supabase().table("belgium_campaign_state").select("*").limit(1).execute()
    return res.data[0] if res.data else None


def upsert_campaign_state(row: dict) -> dict:
    res = (
        supabase()
        .table("belgium_campaign_state")
        .upsert(row, on_conflict="campaign_id")
        .execute()
    )
    return res.data[0] if res.data else row


def upsert_daily_performance(rows: list[dict]) -> int:
    if not rows:
        return 0
    res = (
        supabase()
        .table("belgium_daily_performance")
        .upsert(rows, on_conflict="date,campaign_id,ad_group_id")
        .execute()
    )
    return len(res.data or [])


def upsert_ticket_sales(rows: list[dict]) -> int:
    if not rows:
        return 0
    res = (
        supabase()
        .table("belgium_ticket_sales")
        .upsert(rows, on_conflict="shopify_order_id")
        .execute()
    )
    return len(res.data or [])


def get_daily_performance(date: str) -> list[dict]:
    res = (
        supabase()
        .table("belgium_daily_performance")
        .select("*")
        .eq("date", date)
        .execute()
    )
    return res.data or []


def get_performance_range(start_date: str, end_date: str) -> list[dict]:
    res = (
        supabase()
        .table("belgium_daily_performance")
        .select("*")
        .gte("date", start_date)
        .lte("date", end_date)
        .execute()
    )
    return res.data or []


def get_sales_range(start_iso: str, end_iso: str) -> list[dict]:
    res = (
        supabase()
        .table("belgium_ticket_sales")
        .select("*")
        .gte("ordered_at", start_iso)
        .lte("ordered_at", end_iso)
        .execute()
    )
    return res.data or []


def count_ad_attributed_sales() -> int:
    res = (
        supabase()
        .table("belgium_ticket_sales")
        .select("shopify_order_id", count="exact")
        .eq("ad_attributed", True)
        .execute()
    )
    return res.count or 0


def count_total_sales() -> int:
    res = (
        supabase()
        .table("belgium_ticket_sales")
        .select("shopify_order_id", count="exact")
        .execute()
    )
    return res.count or 0
