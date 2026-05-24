"""
Upload offline conversions (CTA clicks and waitlist signups) from Supabase analytics_logs
to Google Ads using the Google Ads API.

Usage:
    python3 scripts/upload_conversions.py [--dry-run]
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "api"))

try:
    from dotenv import load_dotenv
    # Load env from ads app and landing page
    load_dotenv(os.path.join(HERE, "..", ".env.local"))
    load_dotenv(os.path.join(HERE, "..", "..", "belgium-concert-landing-page", ".env.local"))
except ImportError:
    pass

from api._lib import google_ads_client, conversions

def main():
    parser = argparse.ArgumentParser(description="Upload offline conversions to Google Ads")
    parser.add_argument("--dry-run", action="store_true", help="Print operations without executing")
    args = parser.parse_args()

    client = google_ads_client.get_client()
    customer_id = google_ads_client.customer_id()
    
    print("=" * 60)
    print(f"Syncing Conversions for Account {customer_id}")
    print("=" * 60)

    # 1. Resolve/create conversion actions in Google Ads
    print("\n[1/3] Resolving conversion actions...")
    action_map = {}
    for key, action_name in conversions.CONVERSION_ACTIONS.items():
        action_map[action_name] = conversions.get_or_create_conversion_action(client, customer_id, action_name)
        print(f"  ✓ Resolved action '{action_name}': {action_map[action_name]}")

    # 2. Fetch log data from Supabase
    print("\n[2/3] Fetching logs from Supabase...")
    logs = conversions.fetch_supabase_logs()
    print(f"  Fetched {len(logs)} logs with gclid since 48 hours ago")

    # 3. Upload to Google Ads
    print("\n[3/3] Uploading click conversions...")
    res = conversions.upload_conversions(client, customer_id, logs, action_map, dry_run=args.dry_run)
    
    if args.dry_run:
        print(f"  [Dry Run] Would upload {res['uploaded']} conversions")
    else:
        print(f"  Upload Complete: {res['success_count']} succeeded, {res['fail_count']} failed/deduplicated")
        if res.get("partial_failure_msg"):
            print(f"  Partial Failure: {res['partial_failure_msg']}")
            
    print("\n✅ Conversion sync complete!")


if __name__ == "__main__":
    main()
