"""Add geo + language targeting to ad groups of a Demand Gen campaign.

Demand Gen campaigns reject location/language criteria at the campaign
level (CampaignCriterionService returns an opaque OWNED_AND_OPERATED
error). The actual mechanism is to attach them at the ad_group_criterion
level on every ad group.

Defaults configure the Official Trailer (May 2026) campaign with BE+NL+LU
and EN/NL/FR. Override constants below for other campaigns.

Run with --apply to write. Dry-run by default.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env.local")

from api._lib.google_ads_client import get_client, customer_id

AD_GROUP_IDS = [
    ("subscribers_and_viewers", 200826153750),
    ("video_viewers_only",      200826154030),
]

GEO_IDS = {
    "Belgium":     2056,
    "Netherlands": 2528,
    "Luxembourg":  2442,
}
LANGUAGE_IDS = {
    "English": 1000,
    "Dutch":   1010,
    "French":  1002,
}

apply = "--apply" in sys.argv

client = get_client()
cid = customer_id()
ag_crit_svc = client.get_service("AdGroupCriterionService")

print(f"Plan ({'APPLY' if apply else 'DRY RUN'}): add targeting to {len(AD_GROUP_IDS)} ad group(s)")
for name, _ in AD_GROUP_IDS:
    print(f"  ad group '{name}':")
    for label, gid in GEO_IDS.items():
        print(f"    + location {label} ({gid})")
    for label, lid in LANGUAGE_IDS.items():
        print(f"    + language {label} ({lid})")

if not apply:
    print("\nDry run. Re-run with --apply to write.")
    sys.exit(0)

ops = []
for name, ag_id in AD_GROUP_IDS:
    ag_resource = f"customers/{cid}/adGroups/{ag_id}"
    for label, gid in GEO_IDS.items():
        op = client.get_type("AdGroupCriterionOperation")
        c = op.create
        c.ad_group = ag_resource
        c.location.geo_target_constant = f"geoTargetConstants/{gid}"
        ops.append(op)
    for label, lid in LANGUAGE_IDS.items():
        op = client.get_type("AdGroupCriterionOperation")
        c = op.create
        c.ad_group = ag_resource
        c.language.language_constant = f"languageConstants/{lid}"
        ops.append(op)

resp = ag_crit_svc.mutate_ad_group_criteria(customer_id=cid, operations=ops)
print(f"\nCreated {len(resp.results)} ad group criteria.")

# Verify
print("\n=== Verify: location + language criteria per ad group ===")
svc = client.get_service("GoogleAdsService")
for name, ag_id in AD_GROUP_IDS:
    q = f"""
    SELECT ad_group_criterion.type, ad_group_criterion.location.geo_target_constant,
           ad_group_criterion.language.language_constant
    FROM ad_group_criterion
    WHERE ad_group.id = {ag_id}
      AND ad_group_criterion.type IN ('LOCATION', 'LANGUAGE')
    """
    print(f"\n  {name} (ad_group {ag_id}):")
    for r in svc.search(customer_id=cid, query=q):
        if r.ad_group_criterion.location.geo_target_constant:
            print(f"    LOCATION  {r.ad_group_criterion.location.geo_target_constant}")
        elif r.ad_group_criterion.language.language_constant:
            print(f"    LANGUAGE  {r.ad_group_criterion.language.language_constant}")
