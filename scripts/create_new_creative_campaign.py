"""
Creates a NEW campaign (New Creative - May 2026) identical in structure to the
existing Belgium campaign, but using new trimmed video assets.

Usage:
    python3 scripts/create_new_creative_campaign.py \
        --horizontal  <YouTube video ID>  \
        --portrait    <YouTube video ID>  \
        --short       <YouTube video ID>

The 3 video IDs come from YouTube Studio after uploading the trimmed MP4s.
"""
import argparse
import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "api"))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(HERE, "..", ".env.local"))
except ImportError:
    pass

from api._lib import google_ads_client, config
from google.ads.googleads.v24.common.types import audiences as audiences_pb
from google.protobuf import field_mask_pb2

CID = "3152829803"
EXISTING_CAMPAIGN_ID = "23837741178"   # Belgium Campaign May 13 (original creatives)

# Audience IDs (same as original campaign)
AUDIENCE_SUBSCRIBERS_ID = "347448305"  # MB Belgium Concert (YouTube subscribers)
AUDIENCE_VIEWERS_ID     = "347677581"  # MB Belgium Concert (video viewers only)
CUSTOM_AUDIENCE_RESOURCE = f"customers/{CID}/customAudiences/977585709"

# Same logo asset
LOGO_ASSET = "customers/3152829803/assets/360332176594"
CTA_ASSET  = "customers/3152829803/assets/360340411444"

GEO_TARGETS = ["2056", "2528", "2442"]   # Belgium, Netherlands, Luxembourg
LANGUAGE_IDS = ["1000", "1010", "1002"]  # English, Dutch, French

DAILY_BUDGET_MICROS = 20_000_000  # $20/day


def make_asset_resource(yt_video_id: str, client) -> str:
    """Upload a YouTube video as a Google Ads asset. Returns resource name."""
    asset_service = client.get_service("AssetService")
    op = client.get_type("AssetOperation")
    asset = op.create
    asset.name = f"New Creative - {yt_video_id}"
    asset.youtube_video_asset.youtube_video_id = yt_video_id
    resp = asset_service.mutate_assets(customer_id=CID, operations=[op])
    return resp.results[0].resource_name


def create_campaign(client) -> str:
    """Create a new Demand Gen campaign with shared budget."""
    # Budget
    budget_service = client.get_service("CampaignBudgetService")
    bop = client.get_type("CampaignBudgetOperation")
    budget = bop.create
    budget.name = f"New Creative Campaign Budget - {datetime.now().strftime('%Y%m%d')}"
    budget.amount_micros = DAILY_BUDGET_MICROS
    budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
    bresp = budget_service.mutate_campaign_budgets(customer_id=CID, operations=[bop])
    budget_resource = bresp.results[0].resource_name
    print(f"  Budget: {budget_resource}")

    # Campaign
    camp_service = client.get_service("CampaignService")
    cop = client.get_type("CampaignOperation")
    camp = cop.create
    camp.name = "Belgium Concert - New Creative (May 2026)"
    camp.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.DEMAND_GEN
    camp.status = client.enums.CampaignStatusEnum.ENABLED
    camp.campaign_budget = budget_resource
    camp.maximize_conversions.target_cpa_micros = 0

    cresp = camp_service.mutate_campaigns(customer_id=CID, operations=[cop])
    camp_resource = cresp.results[0].resource_name
    print(f"  Campaign: {camp_resource}")

    # Geo + language criteria
    crit_service = client.get_service("CampaignCriterionService")
    crit_ops = []
    for geo_id in GEO_TARGETS:
        op = client.get_type("CampaignCriterionOperation")
        c = op.create
        c.campaign = camp_resource
        c.location.geo_target_constant = f"geoTargetConstants/{geo_id}"
        crit_ops.append(op)
    for lang_id in LANGUAGE_IDS:
        op = client.get_type("CampaignCriterionOperation")
        c = op.create
        c.campaign = camp_resource
        c.language.language_constant = f"languageConstants/{lang_id}"
        crit_ops.append(op)
    crit_service.mutate_campaign_criteria(customer_id=CID, operations=crit_ops)
    print(f"  Geo + language targeting set")

    return camp_resource


def create_ad_group(client, camp_resource: str, name: str, audience_resource: str,
                    utm_content: str) -> str:
    """Create an ad group with audience + final_url_suffix."""
    ag_service = client.get_service("AdGroupService")
    op = client.get_type("AdGroupOperation")
    ag = op.create
    ag.name = name
    ag.campaign = camp_resource
    ag.status = client.enums.AdGroupStatusEnum.ENABLED
    ag.final_url_suffix = utm_content
    resp = ag_service.mutate_ad_groups(customer_id=CID, operations=[op])
    ag_resource = resp.results[0].resource_name
    ag_id = ag_resource.split("/")[-1]
    print(f"  Ad group '{name}': id={ag_id}")

    # Attach audience as criterion
    agc_service = client.get_service("AdGroupCriterionService")
    agc_op = client.get_type("AdGroupCriterionOperation")
    agc = agc_op.create
    agc.ad_group = ag_resource
    agc.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
    agc.audience.audience = audience_resource
    agc_service.mutate_ad_group_criteria(customer_id=CID, operations=[agc_op])

    return ag_resource


def create_ad(client, ag_resource: str, video_assets: list[str], ad_name: str) -> str:
    """Create a Demand Gen Video Responsive ad."""
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
                 "MusicalBasics Live", "Solo Piano, June 11 2026", "Reserve Your Seat Today"]:
        h = client.get_type("AdTextAsset")
        h.text = text
        vra.headlines.append(h)

    lh = client.get_type("AdTextAsset")
    lh.text = "Lionel Yu performs his viral piano performance live in Zaventem, Belgium. June 11, 2026."
    vra.long_headlines.append(lh)

    d = client.get_type("AdTextAsset")
    d.text = "Reserve your seat for a piano concert near Brussels with Lionel Yu (MusicalBasics)"
    vra.descriptions.append(d)

    for asset_resource in video_assets:
        v = client.get_type("AdVideoAsset")
        v.asset = asset_resource
        vra.videos.append(v)

    logo = client.get_type("AdImageAsset")
    logo.asset = LOGO_ASSET
    vra.logo_images.append(logo)

    cta = client.get_type("AdCallToActionAsset")
    cta.asset = CTA_ASSET
    vra.call_to_actions.append(cta)

    resp = aga_service.mutate_ad_group_ads(customer_id=CID, operations=[op])
    return resp.results[0].resource_name


def main():
    parser = argparse.ArgumentParser(description="Create new creative campaign")
    parser.add_argument("--horizontal", required=True, help="YouTube video ID for horizontal ad")
    parser.add_argument("--portrait",   required=True, help="YouTube video ID for long portrait ad")
    parser.add_argument("--short",      required=True, help="YouTube video ID for short portrait ad")
    args = parser.parse_args()

    client = google_ads_client.get_client()

    print("=" * 60)
    print("Creating: Belgium Concert - New Creative (May 2026)")
    print("=" * 60)

    # Step 1: Upload YouTube videos as Google Ads assets
    print("\n[1/4] Registering YouTube videos as assets...")
    horizontal_asset = make_asset_resource(args.horizontal, client)
    portrait_asset   = make_asset_resource(args.portrait,   client)
    short_asset      = make_asset_resource(args.short,      client)
    print(f"  Horizontal: {horizontal_asset}")
    print(f"  Portrait:   {portrait_asset}")
    print(f"  Short:      {short_asset}")

    # Step 2: Campaign
    print("\n[2/4] Creating campaign...")
    camp_resource = create_campaign(client)

    # Step 3: Two ad groups (mirrors existing campaign)
    print("\n[3/4] Creating ad groups...")
    sub_ag = create_ad_group(
        client, camp_resource,
        name="subscribers_and_viewers",
        audience_resource=f"customers/{CID}/audiences/{AUDIENCE_SUBSCRIBERS_ID}",
        utm_content="utm_content=subscribers",
    )
    view_ag = create_ad_group(
        client, camp_resource,
        name="video_viewers_only",
        audience_resource=f"customers/{CID}/audiences/{AUDIENCE_VIEWERS_ID}",
        utm_content="utm_content=video_viewers",
    )

    # Step 4: Ads
    print("\n[4/4] Creating ads...")
    all_assets = [horizontal_asset, portrait_asset, short_asset]

    create_ad(client, sub_ag,  all_assets, "New Creative - subscribers - Belgium Concert")
    create_ad(client, view_ag, all_assets, "New Creative - video_viewers - Belgium Concert")

    print()
    print("=" * 60)
    print("✅ NEW CREATIVE CAMPAIGN IS LIVE!")
    print()
    print("Campaign: Belgium Concert - New Creative (May 2026)")
    print("Budget:   $20/day (same as original campaign)")
    print("Ad groups: subscribers_and_viewers | video_viewers_only")
    print()
    print("A/B TEST:")
    print("  Original campaign (May 13) → old creative (full intro)")
    print("  New campaign (May 2026)    → trimmed creative (no 'We Are One')")
    print()
    print("Check Google Ads UI in ~30 minutes for approval status.")


if __name__ == "__main__":
    main()
