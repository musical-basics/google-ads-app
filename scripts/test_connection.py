"""
Quick connection test for Google Ads API.
Run after filling in all env vars in .env.local.

Usage:
    source .env.local && python3 scripts/test_connection.py
    # Or with dotenv:
    python3 -c "import dotenv; dotenv.load_dotenv('.env.local')" && python3 scripts/test_connection.py
"""
import os
import sys

# Load .env.local automatically if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv(".env.local")
    print("✓ Loaded .env.local")
except ImportError:
    print("(python-dotenv not installed — reading from environment directly)")

# Check all required vars before attempting connection
REQUIRED = [
    "GOOGLE_ADS_DEVELOPER_TOKEN",
    "GOOGLE_ADS_CLIENT_ID",
    "GOOGLE_ADS_CLIENT_SECRET",
    "GOOGLE_ADS_REFRESH_TOKEN",
    "GOOGLE_ADS_CUSTOMER_ID",
]

print("\n── Checking env vars ──────────────────────────────")
missing = []
for var in REQUIRED:
    val = os.environ.get(var, "")
    if val:
        masked = val[:6] + "..." + val[-4:] if len(val) > 12 else "***"
        print(f"  ✓ {var} = {masked}")
    else:
        print(f"  ✗ {var} = MISSING")
        missing.append(var)

if missing:
    print(f"\n✗ Missing {len(missing)} required variable(s). Fill them in .env.local first.")
    sys.exit(1)

print("\n── Connecting to Google Ads API ───────────────────")
try:
    from google.ads.googleads.client import GoogleAdsClient
    from google.ads.googleads.errors import GoogleAdsException
except ImportError:
    print("✗ google-ads package not installed. Run: pip install google-ads")
    sys.exit(1)

cfg = {
    "developer_token": os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
    "client_id": os.environ["GOOGLE_ADS_CLIENT_ID"],
    "client_secret": os.environ["GOOGLE_ADS_CLIENT_SECRET"],
    "refresh_token": os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
    "use_proto_plus": True,
}
login_cid = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").strip()
if login_cid:
    cfg["login_customer_id"] = login_cid
    print(f"  Using login_customer_id: {login_cid}")

customer_id = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")

try:
    client = GoogleAdsClient.load_from_dict(cfg)
    ga_service = client.get_service("GoogleAdsService")

    # Simple query to verify access — list campaigns (or empty if none yet)
    query = """
        SELECT
            campaign.id,
            campaign.name,
            campaign.status
        FROM campaign
        ORDER BY campaign.id
        LIMIT 10
    """
    response = ga_service.search(customer_id=customer_id, query=query)
    rows = list(response)

    print(f"✓ Connected! Customer ID: {customer_id}")
    print(f"\n── Campaigns found: {len(rows)} ─────────────────────────")
    if rows:
        for row in rows:
            print(f"  [{row.campaign.status.name}] {row.campaign.name} (id={row.campaign.id})")
    else:
        print("  (no campaigns yet — account is clean and ready)")

    print("\n✅ Google Ads API connection is LIVE. Ready to proceed!\n")

except GoogleAdsException as ex:
    print(f"\n✗ Google Ads API error:")
    for error in ex.failure.errors:
        print(f"  {error.error_code}: {error.message}")
    sys.exit(1)
except Exception as ex:
    print(f"\n✗ Unexpected error: {ex}")
    sys.exit(1)
