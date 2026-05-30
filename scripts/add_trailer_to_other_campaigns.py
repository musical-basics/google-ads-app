"""Add the new trailer video (N75lvM0-hn8 = asset 367428577991) as an
ADDITIONAL ad in every ad group of the 3 other active campaigns:

  - Belgium Concert - New Creative (May 2026)       DG  id=23871037379
  - Belgium Concert - Original Creative (May 2026)  DG  id=23875661669
  - belgium_new_creative_yt                         VIDEO id=23873822810

Strategy: Google Ads ad creatives are immutable post-creation, so 'adding
a video to an existing ad' isn't possible. Instead we create a NEW ad in
each ad group with the trailer as its video. The existing ads stay live;
both ads compete for impressions and Google's optimizer picks winners.

For the VIDEO (YouTube channel-type) campaign we attempt creation -- if
the API rejects it the way it rejected campaign status changes, we fall
back to telling Lionel to create those ads in the UI.

Run with --apply to write. Dry-run by default.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env.local")

from api._lib.google_ads_client import get_client, customer_id

CID = "3152829803"
NEW_VIDEO_ASSET = f"customers/{CID}/assets/367428577991"  # Belgium Trailer
LOGO_ASSET      = f"customers/{CID}/assets/360332176594"
CTA_ASSET       = f"customers/{CID}/assets/360340411444"
LANDING_URL     = "https://belgium.musicalbasics.com"

# Map of (campaign_id, channel_type, [(ad_group_name, ad_group_id), ...])
# The 4 DG ads were already created in the first run -- only re-enable
# them in TARGETS if you've manually removed them first.
TARGETS_DG_DONE = [
    (23871037379, "DEMAND_GEN", [
        ("video_viewers_only",      195468560286),
        ("subscribers_and_viewers", 195468564846),
    ]),
    (23875661669, "DEMAND_GEN", [
        ("subscribers_and_viewers", 195520511703),
        ("video_viewers_only",      197105972095),
    ]),
]
TARGETS = [
    (23873822810, "VIDEO", [
        ("subscribers_and_viewers", 196446326843),
        ("video_viewers_only",      197364971032),
    ]),
]

HEADLINES = [
    "Belgium Piano Concert",
    "Live in Zaventem June 11",
    "MusicalBasics Live",
    "Solo Piano, June 11 2026",
    "Reserve Your Seat Today",
]
LONG_HEADLINE = "Lionel Yu performs his viral piano performance live in Zaventem, Belgium. June 11, 2026."
DESCRIPTION   = "Reserve your seat for a piano concert near Brussels with Lionel Yu (MusicalBasics)"

apply = "--apply" in sys.argv

client = get_client()
cid = customer_id()
ad_svc = client.get_service("AdGroupAdService")


def build_dg_ad(ag_resource: str, ad_name: str):
    op = client.get_type("AdGroupAdOperation")
    aga = op.create
    aga.ad_group = ag_resource
    aga.status = client.enums.AdGroupAdStatusEnum.ENABLED
    ad = aga.ad
    ad.name = ad_name
    ad.final_urls.append(LANDING_URL)
    vra = ad.demand_gen_video_responsive_ad
    vra.business_name.text = "MusicalBasics"
    for text in HEADLINES:
        h = client.get_type("AdTextAsset"); h.text = text
        vra.headlines.append(h)
    lh = client.get_type("AdTextAsset"); lh.text = LONG_HEADLINE
    vra.long_headlines.append(lh)
    d = client.get_type("AdTextAsset"); d.text = DESCRIPTION
    vra.descriptions.append(d)
    v = client.get_type("AdVideoAsset"); v.asset = NEW_VIDEO_ASSET
    vra.videos.append(v)
    logo = client.get_type("AdImageAsset"); logo.asset = LOGO_ASSET
    vra.logo_images.append(logo)
    cta = client.get_type("AdCallToActionAsset"); cta.asset = CTA_ASSET
    vra.call_to_actions.append(cta)
    return op


def build_video_ad(ag_resource: str, ad_name: str):
    """Build a VIDEO_RESPONSIVE_AD for a legacy VIDEO-type campaign.
    Confirmed not working in v24: API rejects new ads on VIDEO campaigns
    with a misleading 'REQUIRED at video_responsive_ad' error regardless
    of which fields are populated. Same pattern as the campaign-level
    MUTATE_NOT_ALLOWED rejection. Kept here for reference."""
    op = client.get_type("AdGroupAdOperation")
    aga = op.create
    aga.ad_group = ag_resource
    aga.status = client.enums.AdGroupAdStatusEnum.ENABLED
    ad = aga.ad
    ad.name = ad_name
    ad.final_urls.append(LANDING_URL)
    vra = ad.video_responsive_ad
    v = client.get_type("AdVideoAsset"); v.asset = NEW_VIDEO_ASSET
    vra.videos.append(v)
    for text in HEADLINES:
        ha = client.get_type("AdTextAsset"); ha.text = text
        vra.headlines.append(ha)
    lh = client.get_type("AdTextAsset"); lh.text = LONG_HEADLINE
    vra.long_headlines.append(lh)
    da = client.get_type("AdTextAsset"); da.text = DESCRIPTION
    vra.descriptions.append(da)
    ca = client.get_type("AdTextAsset"); ca.text = "Book now"
    vra.call_to_actions.append(ca)
    logo = client.get_type("AdImageAsset"); logo.asset = LOGO_ASSET
    vra.logo_images.append(logo)
    return op


print(f"Plan ({'APPLY' if apply else 'DRY RUN'}): create 1 trailer ad in each of 6 ad groups\n")
for camp_id, channel, ad_groups in TARGETS:
    print(f"  campaign [{camp_id}] ({channel}):")
    for name, ag_id in ad_groups:
        print(f"    + ad in ad_group '{name}' ({ag_id})")

if not apply:
    print("\nDry run. Re-run with --apply to write.")
    sys.exit(0)

results = []
for camp_id, channel, ad_groups in TARGETS:
    for ag_name, ag_id in ad_groups:
        ag_resource = f"customers/{cid}/adGroups/{ag_id}"
        ad_name = f"Trailer ad - {ag_name} - camp{camp_id}"
        if channel == "DEMAND_GEN":
            op = build_dg_ad(ag_resource, ad_name)
        else:
            op = build_video_ad(ag_resource, ad_name)
        try:
            resp = ad_svc.mutate_ad_group_ads(customer_id=cid, operations=[op])
            ad_resource = resp.results[0].resource_name
            ad_id = ad_resource.split("~")[-1]
            results.append((camp_id, ag_name, ag_id, ad_id, "ok"))
            print(f"\nOK  [{camp_id}] {ag_name}: created ad {ad_id}")
        except Exception as e:
            msg = str(e)
            short = msg[msg.find("errors"):msg.find("errors")+3000] if "errors" in msg else msg[:2000]
            results.append((camp_id, ag_name, ag_id, "-", "fail"))
            print(f"\nFAIL [{camp_id}] {ag_name}: {short}")

print("\n=== Summary ===")
for camp_id, ag, ag_id, ad_id, status in results:
    print(f"  [{camp_id}] {ag:<28} ad_group={ag_id}  ad={ad_id:>15}  {status}")
