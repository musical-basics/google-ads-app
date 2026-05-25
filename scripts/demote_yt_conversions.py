"""
Set YouTube auto-created conversion actions (follow-on views, earned actions, etc.)
to SECONDARY so they no longer pollute the "Conversions" column in Google Ads.
They'll still appear in "All Conversions" for reference.

Run once:
  .venv/bin/python scripts/demote_yt_conversions.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "api"))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(HERE, "..", ".env.local"))
    load_dotenv(os.path.join(HERE, "..", ".env"))
except ImportError:
    pass

from _lib import google_ads_client


def main():
    client = google_ads_client.get_client()
    customer_id = google_ads_client.customer_id()
    ga_service = client.get_service("GoogleAdsService")
    ca_service = client.get_service("ConversionActionService")

    query = """
        SELECT
            conversion_action.resource_name,
            conversion_action.name,
            conversion_action.category,
            conversion_action.primary_for_goal,
            conversion_action.status
        FROM conversion_action
        WHERE conversion_action.status != 'REMOVED'
    """

    rows = list(ga_service.search(customer_id=customer_id, query=query))
    demoted = []

    for row in rows:
        ca = row.conversion_action
        category_name = ca.category.name if hasattr(ca.category, "name") else str(ca.category)

        is_youtube = any(kw in category_name.upper() for kw in (
            "YOUTUBE", "FOLLOW_ON", "ENGAGED_VIEW", "EARNED"
        ))

        if not is_youtube:
            continue

        print(f"  Found YouTube action: [{category_name}] {ca.name}  primary={ca.primary_for_goal}")

        if not ca.primary_for_goal:
            print(f"    → Already secondary, skipping.")
            continue

        # Build update operation — only change primary_for_goal
        op = client.get_type("ConversionActionOperation")
        update = op.update
        update.resource_name = ca.resource_name
        update.primary_for_goal = False
        op.update_mask.paths.append("primary_for_goal")

        try:
            ca_service.mutate_conversion_actions(
                customer_id=customer_id,
                operations=[op],
            )
            demoted.append(ca.name)
            print(f"    → DEMOTED to secondary ✓")
        except Exception as e:
            print(f"    → ERROR: {e}")

    print(f"\n=== Done. Demoted {len(demoted)} YouTube conversion action(s) to secondary ===")
    for name in demoted:
        print(f"  - {name}")


if __name__ == "__main__":
    main()
