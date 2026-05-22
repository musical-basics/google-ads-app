"""
Google Ads client wrapper for the Belgium concert campaign.

Scope: VIDEO campaign (Drive Conversions / VIDEO_ACTION subtype), maximize_conversions
bidding, geo + language targeting, two ad groups with audiences attached, one video ad
referencing an existing YouTube asset, UTM suffix on the final URL.

Reads env vars at client construction. Pass `dry_run=True` on creation to skip writes.
"""
import os
from datetime import datetime, date as date_cls
from typing import Iterable

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from . import config


def _required_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise RuntimeError(f"{name} is missing from environment")
    return val


def get_client() -> GoogleAdsClient:
    """
    Build a Google Ads client from env vars. Raises if any required field is missing
    or if the developer token still looks like a placeholder.
    """
    dev_token = _required_env("GOOGLE_ADS_DEVELOPER_TOKEN")
    if dev_token.startswith("PENDING_APPROVAL"):
        raise RuntimeError(
            f"developer token is still a placeholder ({dev_token}) - "
            "approval has not landed yet, blocking all Google Ads calls"
        )
    cfg = {
        "developer_token": dev_token,
        "client_id": _required_env("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": _required_env("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": _required_env("GOOGLE_ADS_REFRESH_TOKEN"),
        "use_proto_plus": os.environ.get("GOOGLE_ADS_USE_PROTO_PLUS", "true").lower() == "true",
    }
    login_cid = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "").strip()
    if login_cid:
        cfg["login_customer_id"] = login_cid
    return GoogleAdsClient.load_from_dict(cfg)


def customer_id() -> str:
    return _required_env("GOOGLE_ADS_CUSTOMER_ID")


def get_campaign_status(client: GoogleAdsClient, campaign_resource: str) -> dict:
    ga_service = client.get_service("GoogleAdsService")
    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.start_date,
            campaign.end_date,
            campaign_budget.amount_micros,
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversions_value
        FROM campaign
        WHERE campaign.resource_name = '{campaign_resource}'
    """
    rows = ga_service.search(customer_id=customer_id(), query=query)
    for row in rows:
        return {
            "id": str(row.campaign.id),
            "name": row.campaign.name,
            "status": row.campaign.status.name,
            "start_date": row.campaign.start_date,
            "end_date": row.campaign.end_date,
            "daily_budget_cents": row.campaign_budget.amount_micros // 10_000,
            "total_spend_cents": row.metrics.cost_micros // 10_000,
            "total_conversions": row.metrics.conversions,
            "total_revenue_cents": int(row.metrics.conversions_value * 100),
        }
    return {}


def pull_performance(client: GoogleAdsClient, campaign_id: str, since: str) -> list[dict]:
    """
    Pull per-ad-group daily performance from `since` (YYYY-MM-DD) through today.

    Note: metrics.video_views is Video Action-specific and not available on Demand Gen
    campaigns (the successor type). We use metrics.interactions instead, which covers
    the equivalent engagement signals on Demand Gen (clicks + video engagements).
    """
    ga_service = client.get_service("GoogleAdsService")
    query = f"""
        SELECT
            segments.date,
            campaign.id,
            ad_group.id,
            metrics.impressions,
            metrics.interactions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversions_value
        FROM ad_group
        WHERE campaign.id = {campaign_id}
            AND segments.date >= '{since}'
            AND segments.date <= '{date_cls.today().isoformat()}'
    """
    rows = ga_service.search(customer_id=customer_id(), query=query)
    out = []
    for row in rows:
        out.append({
            "date": row.segments.date,
            "campaign_id": str(row.campaign.id),
            "ad_group_id": str(row.ad_group.id),
            "impressions": int(row.metrics.impressions),
            "views": int(row.metrics.interactions),  # interactions = engagement on Demand Gen
            "clicks": int(row.metrics.clicks),
            "cost_cents": int(row.metrics.cost_micros) // 10_000,
            "conversions": float(row.metrics.conversions),
            "conversion_value_cents": int(row.metrics.conversions_value * 100),
        })
    return out


def pause_campaign(client: GoogleAdsClient, campaign_resource: str) -> str:
    return _set_campaign_status(client, campaign_resource, "PAUSED")


def resume_campaign(client: GoogleAdsClient, campaign_resource: str) -> str:
    return _set_campaign_status(client, campaign_resource, "ENABLED")


def _set_campaign_status(client: GoogleAdsClient, campaign_resource: str, status_str: str) -> str:
    campaign_service = client.get_service("CampaignService")
    op = client.get_type("CampaignOperation")
    campaign = op.update
    campaign.resource_name = campaign_resource
    campaign.status = client.enums.CampaignStatusEnum[status_str]
    fm = client.get_type("FieldMask")
    fm.paths.append("status")
    op.update_mask.CopyFrom(fm)
    res = campaign_service.mutate_campaigns(customer_id=customer_id(), operations=[op])
    return res.results[0].resource_name


def create_campaign(
    client: GoogleAdsClient,
    daily_budget_cents: int,
    video_id_landscape: str,
    video_id_portrait: str | None,
    audience_subscribers_id: str | None,
    audience_lookalike_id: str | None,
    audience_custom_intent_id: str | None,
    dry_run: bool = False,
) -> dict:
    """
    Create the full campaign tree. Returns a dict of created resource names.
    On dry_run, returns the planned operations without writing.
    """
    cid = customer_id()
    plan = {
        "dry_run": dry_run,
        "campaign_name": config.CAMPAIGN_NAME,
        "daily_budget_cents": daily_budget_cents,
        "end_date": config.CAMPAIGN_END_DATE,
        "video_id_landscape": video_id_landscape,
        "audience_subscribers_id": audience_subscribers_id,
        "audience_lookalike_id": audience_lookalike_id,
        "audience_custom_intent_id": audience_custom_intent_id,
        "geo_targets": list(config.GEO_TARGET_IDS.keys()),
        "languages": list(config.LANGUAGE_IDS.keys()),
    }
    if dry_run:
        return plan

    # 1. Budget
    budget_service = client.get_service("CampaignBudgetService")
    budget_op = client.get_type("CampaignBudgetOperation")
    budget = budget_op.create
    budget.name = f"{config.CAMPAIGN_NAME}_budget"
    budget.amount_micros = daily_budget_cents * 10_000
    budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
    budget.explicitly_shared = False
    budget_res = budget_service.mutate_campaign_budgets(customer_id=cid, operations=[budget_op])
    budget_resource = budget_res.results[0].resource_name

    # 2. Campaign
    campaign_service = client.get_service("CampaignService")
    campaign_op = client.get_type("CampaignOperation")
    campaign = campaign_op.create
    campaign.name = config.CAMPAIGN_NAME
    campaign.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.VIDEO
    campaign.advertising_channel_sub_type = client.enums.AdvertisingChannelSubTypeEnum.VIDEO_ACTION
    campaign.status = client.enums.CampaignStatusEnum.PAUSED  # start paused; enable explicitly
    campaign.campaign_budget = budget_resource
    campaign.start_date = date_cls.today().strftime("%Y-%m-%d")
    campaign.end_date = config.CAMPAIGN_END_DATE
    campaign.maximize_conversions = client.get_type("MaximizeConversions")
    campaign.final_url_suffix = (
        f"utm_source={config.UTM_SOURCE}"
        f"&utm_medium={config.UTM_MEDIUM}"
        f"&utm_campaign={config.UTM_CAMPAIGN}"
        f"&utm_content={{adgroupid}}"
        f"&utm_term={{creative}}"
    )
    network = campaign.network_settings
    network.target_google_search = False
    network.target_search_network = False
    network.target_content_network = False
    network.target_partner_search_network = False
    network.target_youtube = True
    campaign_res = campaign_service.mutate_campaigns(customer_id=cid, operations=[campaign_op])
    campaign_resource = campaign_res.results[0].resource_name
    campaign_id = campaign_resource.split("/")[-1]

    # 3. Geo + language targeting
    cct_service = client.get_service("CampaignCriterionService")
    cct_ops = []
    for geo_id in config.GEO_TARGET_IDS.values():
        op = client.get_type("CampaignCriterionOperation")
        c = op.create
        c.campaign = campaign_resource
        c.location.geo_target_constant = f"geoTargetConstants/{geo_id}"
        cct_ops.append(op)
    for lang_id in config.LANGUAGE_IDS.values():
        op = client.get_type("CampaignCriterionOperation")
        c = op.create
        c.campaign = campaign_resource
        c.language.language_constant = f"languageConstants/{lang_id}"
        cct_ops.append(op)
    cct_service.mutate_campaign_criteria(customer_id=cid, operations=cct_ops)

    # 4. Ad groups
    ag_service = client.get_service("AdGroupService")

    def make_ag(name: str) -> str:
        op = client.get_type("AdGroupOperation")
        ag = op.create
        ag.name = name
        ag.campaign = campaign_resource
        ag.type_ = client.enums.AdGroupTypeEnum.VIDEO_RESPONSIVE
        ag.status = client.enums.AdGroupStatusEnum.ENABLED
        res = ag_service.mutate_ad_groups(customer_id=cid, operations=[op])
        return res.results[0].resource_name

    ag_subs_resource = make_ag(f"{config.CAMPAIGN_NAME}_subscribers_and_viewers")
    ag_look_resource = make_ag(f"{config.CAMPAIGN_NAME}_similar_audiences")

    # 5. Attach audiences to ad groups (skip if id not provided)
    agc_service = client.get_service("AdGroupCriterionService")

    def attach_user_list(ag_resource: str, user_list_id: str):
        op = client.get_type("AdGroupCriterionOperation")
        c = op.create
        c.ad_group = ag_resource
        c.user_list.user_list = f"customers/{cid}/userLists/{user_list_id}"
        agc_service.mutate_ad_group_criteria(customer_id=cid, operations=[op])

    if audience_subscribers_id:
        attach_user_list(ag_subs_resource, audience_subscribers_id)
    if audience_lookalike_id:
        attach_user_list(ag_look_resource, audience_lookalike_id)
    if audience_custom_intent_id:
        # Attach custom audience (intent) as second criterion on lookalike ad group
        op = client.get_type("AdGroupCriterionOperation")
        c = op.create
        c.ad_group = ag_look_resource
        c.custom_audience.custom_audience = (
            f"customers/{cid}/customAudiences/{audience_custom_intent_id}"
        )
        agc_service.mutate_ad_group_criteria(customer_id=cid, operations=[op])

    # 6. Video asset + ad
    asset_service = client.get_service("AssetService")
    asset_op = client.get_type("AssetOperation")
    asset = asset_op.create
    asset.youtube_video_asset.youtube_video_id = video_id_landscape
    asset.name = f"{config.CAMPAIGN_NAME}_video_landscape"
    asset_res = asset_service.mutate_assets(customer_id=cid, operations=[asset_op])
    video_asset_resource = asset_res.results[0].resource_name

    ad_service = client.get_service("AdGroupAdService")

    def make_video_ad(ag_resource: str) -> str:
        op = client.get_type("AdGroupAdOperation")
        aga = op.create
        aga.ad_group = ag_resource
        aga.status = client.enums.AdGroupAdStatusEnum.ENABLED
        aga.ad.final_urls.append(config.LANDING_URL)
        aga.ad.video_responsive_ad.videos.add().asset = video_asset_resource
        ha = aga.ad.video_responsive_ad.headlines.add()
        ha.text = "Belgium Piano Concert"
        la = aga.ad.video_responsive_ad.long_headlines.add()
        la.text = "Live solo piano in Zaventem, by Musical Basics"
        da = aga.ad.video_responsive_ad.descriptions.add()
        da.text = "Reserve your seat for the June 11 concert."
        ca = aga.ad.video_responsive_ad.call_to_actions.add()
        ca.text = "Book now"
        res = ad_service.mutate_ad_group_ads(customer_id=cid, operations=[op])
        return res.results[0].resource_name

    ad_subs_resource = make_video_ad(ag_subs_resource)
    ad_look_resource = make_video_ad(ag_look_resource)

    return {
        "campaign_resource": campaign_resource,
        "campaign_id": campaign_id,
        "budget_resource": budget_resource,
        "ad_group_subscribers": ag_subs_resource,
        "ad_group_lookalike": ag_look_resource,
        "video_asset": video_asset_resource,
        "ad_subscribers": ad_subs_resource,
        "ad_lookalike": ad_look_resource,
    }
