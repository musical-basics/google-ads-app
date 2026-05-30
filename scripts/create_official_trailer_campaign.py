"""Create the third Belgium Demand Gen campaign using the official trailer video.

Same structure as create_new_creative_campaign.py:
- DG channel, maximize_conversions bidding
- BE+NL+LU geo, EN/NL/FR languages
- Two ad groups: subscribers_and_viewers + video_viewers_only with the
  same audience attachments as the other two DGs
- EUR 20/day budget
- utm_campaign=belgium_official_trailer_dg so attribution is distinct

Differences:
- Starts PAUSED (Lionel reviews in UI before enabling)
- Single video asset (the trailer), not three aspect-ratio variants

Run with --apply to actually create. Dry-run without it.
"""
import argparse
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "api"))

from dotenv import load_dotenv
load_dotenv(os.path.join(HERE, "..", ".env.local"))

from api._lib import google_ads_client
from google.protobuf import field_mask_pb2

CID = "3152829803"

AUDIENCE_SUBSCRIBERS_ID = "347448305"
AUDIENCE_VIEWERS_ID     = "347677581"

LOGO_ASSET = "customers/3152829803/assets/360332176594"
CTA_ASSET  = "customers/3152829803/assets/360340411444"

GEO_TARGETS  = ["2056", "2528", "2442"]   # BE, NL, LU
LANGUAGE_IDS = ["1000", "1010", "1002"]   # EN, NL, FR

DAILY_BUDGET_MICROS = 20_000_000  # EUR 20/day

VIDEO_ID = "N75lvM0-hn8"  # Belgium Concert Trailer (unlisted)

# Reuse resources from a previous partially-failed run if non-empty.
# Otherwise leave blank and new ones get created.
REUSE_VIDEO_ASSET = "customers/3152829803/assets/367428577991"
# Note: the prior orphan budget 15607521311 can't be reused because its
# explicitly_shared flag is immutable post-creation, and it was created
# as shared (the default). Leaving it orphaned is harmless (no campaign
# references it -> no spend). Create a fresh, non-shared budget below.
REUSE_BUDGET      = ""
# Campaign created in the partially-successful run that errored on
# criteria. Reuse it instead of making yet another duplicate.
REUSE_CAMPAIGN    = "customers/3152829803/campaigns/23888155116"

CAMPAIGN_NAME = "Belgium Concert - Official Trailer (May 2026)"
UTM_CAMPAIGN  = "belgium_official_trailer_dg"


def register_video_asset(client) -> str:
    if REUSE_VIDEO_ASSET:
        print(f"  Reusing existing video asset: {REUSE_VIDEO_ASSET}")
        return REUSE_VIDEO_ASSET
    asset_service = client.get_service("AssetService")
    op = client.get_type("AssetOperation")
    a = op.create
    a.name = f"Official Trailer - {VIDEO_ID}"
    a.youtube_video_asset.youtube_video_id = VIDEO_ID
    resp = asset_service.mutate_assets(customer_id=CID, operations=[op])
    return resp.results[0].resource_name


def create_campaign(client) -> str:
    # Reuse an already-created campaign if available.
    if REUSE_CAMPAIGN:
        print(f"  Reusing existing campaign: {REUSE_CAMPAIGN}")
        return REUSE_CAMPAIGN

    # Budget (reuse orphan if available — but make sure it's non-shared first,
    # since maximize_conversions on Demand Gen rejects shared budgets).
    if REUSE_BUDGET:
        budget_resource = REUSE_BUDGET
        budget_service = client.get_service("CampaignBudgetService")
        upd_op = client.get_type("CampaignBudgetOperation")
        upd_op.update.resource_name = budget_resource
        upd_op.update.explicitly_shared = False
        upd_op.update_mask.CopyFrom(field_mask_pb2.FieldMask(paths=["explicitly_shared"]))
        budget_service.mutate_campaign_budgets(customer_id=CID, operations=[upd_op])
        print(f"  Reusing existing budget (set to non-shared): {budget_resource}")
    else:
        budget_service = client.get_service("CampaignBudgetService")
        bop = client.get_type("CampaignBudgetOperation")
        b = bop.create
        b.name = f"Official Trailer Campaign Budget - {datetime.now().strftime('%Y%m%d')}"
        b.amount_micros = DAILY_BUDGET_MICROS
        b.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
        # maximize_conversions on Demand Gen requires a non-shared budget.
        b.explicitly_shared = False
        bresp = budget_service.mutate_campaign_budgets(customer_id=CID, operations=[bop])
        budget_resource = bresp.results[0].resource_name
        print(f"  Budget: {budget_resource}")

    # Campaign (PAUSED)
    camp_service = client.get_service("CampaignService")
    cop = client.get_type("CampaignOperation")
    c = cop.create
    c.name = CAMPAIGN_NAME
    c.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.DEMAND_GEN
    c.status = client.enums.CampaignStatusEnum.PAUSED
    c.campaign_budget = budget_resource
    c.maximize_conversions.target_cpa_micros = 0
    # Required since 2025 for any campaign that may serve in the EU under the
    # Digital Services Act / EU Political Advertising Regulation. This is not
    # political advertising, so set to False.
    c.contains_eu_political_advertising = (
        client.enums.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
    )
    cresp = camp_service.mutate_campaigns(customer_id=CID, operations=[cop])
    camp_resource = cresp.results[0].resource_name
    print(f"  Campaign: {camp_resource}  (status=PAUSED)")

    # Geo + language criteria
    crit_service = client.get_service("CampaignCriterionService")
    crit_ops = []
    for geo_id in GEO_TARGETS:
        op = client.get_type("CampaignCriterionOperation")
        c2 = op.create
        c2.campaign = camp_resource
        c2.location.geo_target_constant = f"geoTargetConstants/{geo_id}"
        crit_ops.append(op)
    for lang_id in LANGUAGE_IDS:
        op = client.get_type("CampaignCriterionOperation")
        c2 = op.create
        c2.campaign = camp_resource
        c2.language.language_constant = f"languageConstants/{lang_id}"
        crit_ops.append(op)
    crit_service.mutate_campaign_criteria(customer_id=CID, operations=crit_ops)
    print(f"  Geo + language targeting set")
    return camp_resource


def create_ad_group(client, camp_resource: str, name: str, audience_id: str,
                    utm_content_slug: str) -> str:
    ag_service = client.get_service("AdGroupService")
    op = client.get_type("AdGroupOperation")
    ag = op.create
    ag.name = name
    ag.campaign = camp_resource
    ag.status = client.enums.AdGroupStatusEnum.ENABLED
    ag.final_url_suffix = (
        f"utm_source=google&utm_medium=video"
        f"&utm_campaign={UTM_CAMPAIGN}"
        f"&utm_content={utm_content_slug}"
        f"&gad_campaignid={{campaignid}}"
        f"&gad_adgroupid={{adgroupid}}"
        f"&gad_creative={{creative}}"
    )
    resp = ag_service.mutate_ad_groups(customer_id=CID, operations=[op])
    ag_resource = resp.results[0].resource_name
    print(f"  Ad group '{name}': {ag_resource.split('/')[-1]}")

    agc_service = client.get_service("AdGroupCriterionService")
    agc_op = client.get_type("AdGroupCriterionOperation")
    agc = agc_op.create
    agc.ad_group = ag_resource
    agc.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
    agc.audience.audience = f"customers/{CID}/audiences/{audience_id}"
    agc_service.mutate_ad_group_criteria(customer_id=CID, operations=[agc_op])
    return ag_resource


def create_ad(client, ag_resource: str, video_asset: str, ad_name: str) -> str:
    aga_service = client.get_service("AdGroupAdService")
    op = client.get_type("AdGroupAdOperation")
    aga = op.create
    aga.ad_group = ag_resource
    aga.status = client.enums.AdGroupAdStatusEnum.ENABLED
    ad = aga.ad
    ad.name = ad_name
    ad.final_urls.append("https://belgium.musicalbasics.com")

    vra = ad.demand_gen_video_responsive_ad
    vra.business_name.text = "MusicalBasics"

    for text in ["Belgium Piano Concert", "Live in Zaventem June 11",
                 "MusicalBasics Live", "Solo Piano, June 11 2026",
                 "Reserve Your Seat Today"]:
        h = client.get_type("AdTextAsset"); h.text = text
        vra.headlines.append(h)

    lh = client.get_type("AdTextAsset")
    lh.text = "Lionel Yu performs his viral piano performance live in Zaventem, Belgium. June 11, 2026."
    vra.long_headlines.append(lh)

    d = client.get_type("AdTextAsset")
    d.text = "Reserve your seat for a piano concert near Brussels with Lionel Yu (MusicalBasics)"
    vra.descriptions.append(d)

    v = client.get_type("AdVideoAsset"); v.asset = video_asset
    vra.videos.append(v)

    logo = client.get_type("AdImageAsset"); logo.asset = LOGO_ASSET
    vra.logo_images.append(logo)

    cta = client.get_type("AdCallToActionAsset"); cta.asset = CTA_ASSET
    vra.call_to_actions.append(cta)

    resp = aga_service.mutate_ad_group_ads(customer_id=CID, operations=[op])
    return resp.results[0].resource_name


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true",
                        help="Actually create the campaign (otherwise dry-run print only)")
    args = parser.parse_args()

    print("=" * 60)
    print(f"Plan: create '{CAMPAIGN_NAME}'")
    print(f"  Video: https://youtu.be/{VIDEO_ID}")
    print(f"  utm_campaign: {UTM_CAMPAIGN}")
    print(f"  Budget: EUR{DAILY_BUDGET_MICROS / 1_000_000:.2f}/day")
    print(f"  Status: PAUSED (Lionel enables in UI after review)")
    print(f"  Geo: BE+NL+LU, Languages: EN/NL/FR")
    print(f"  Ad groups: subscribers_and_viewers, video_viewers_only")
    print("=" * 60)

    if not args.apply:
        print("\nDRY RUN. Re-run with --apply to actually create.")
        return

    client = google_ads_client.get_client()

    print("\n[1/4] Registering video asset...")
    video_asset = register_video_asset(client)
    print(f"  Video asset: {video_asset}")

    print("\n[2/4] Creating campaign (paused)...")
    camp_resource = create_campaign(client)

    print("\n[3/4] Creating ad groups...")
    sub_ag = create_ad_group(client, camp_resource,
                              "subscribers_and_viewers",
                              AUDIENCE_SUBSCRIBERS_ID,
                              "subscribers")
    view_ag = create_ad_group(client, camp_resource,
                               "video_viewers_only",
                               AUDIENCE_VIEWERS_ID,
                               "video_viewers")

    print("\n[4/4] Creating ads...")
    create_ad(client, sub_ag,  video_asset, "Official Trailer - subscribers")
    create_ad(client, view_ag, video_asset, "Official Trailer - video_viewers")

    print()
    print("=" * 60)
    print(f"CREATED (paused): {CAMPAIGN_NAME}")
    print(f"Campaign resource: {camp_resource}")
    print(f"Campaign id: {camp_resource.split('/')[-1]}")
    print()
    print("Next step: review in Google Ads UI, then enable manually.")
    print("=" * 60)


if __name__ == "__main__":
    main()
