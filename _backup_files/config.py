"""
Static config and constants for the Belgium concert campaign.
Variant IDs and EU market info come from shopify-eu-pricing.md.
"""
import os

CAMPAIGN_NAME = os.environ.get("CAMPAIGN_NAME", "belgium_tickets_be_2606")
CAMPAIGN_END_DATE = os.environ.get("CAMPAIGN_END_DATE", "2026-06-10")
CONCERT_DATE = os.environ.get("CONCERT_DATE", "2026-06-11")
LANDING_URL = os.environ.get("LANDING_URL", "https://belgium.musicalbasics.com")
TIMEZONE = os.environ.get("TIMEZONE", "Europe/Brussels")

# Shopify variant IDs from shopify-eu-pricing.md
VARIANT_STANDARD = "43946996957227"
VARIANT_VIP = "43962297974827"
TICKET_TIERS = {
    VARIANT_STANDARD: "standard",
    VARIANT_VIP: "vip",
}
TIER_PRICE_CENTS = {
    "standard": 2900,
    "vip": 5900,
}

# Google Ads location IDs (geoTargetConstants/<id>)
GEO_TARGET_IDS = {
    "Belgium": "2056",
    "Netherlands": "2528",
    "Luxembourg": "2442",
    "Hauts-de-France": "20496",
    "Grand Est": "20492",
}

# Google Ads language constant IDs (languageConstants/<id>)
LANGUAGE_IDS = {
    "English": "1000",
    "Dutch": "1010",
    "French": "1002",
}

# UTM convention — shared across both campaigns
UTM_SOURCE = "google"
UTM_MEDIUM = "video"

# Campaign 1 — original creative (Belgium Campaign May 13, id=23837741178)
CAMPAIGN_1_ID   = "23837741178"
UTM_CAMPAIGN_1  = "belgium_original"
# Ad group IDs — Campaign 1
AG1_SUBSCRIBERS = "196557300716"   # subscribers_and_viewers
AG1_VIEWERS     = "193972785582"   # video_viewers_only

# Campaign 2 — new creative trimmed (Belgium Concert - New Creative May 2026, id=23871037379)
CAMPAIGN_2_ID   = "23871037379"
UTM_CAMPAIGN_2  = "belgium_new_creative"
# Ad group IDs — Campaign 2
AG2_SUBSCRIBERS = "195468564846"   # subscribers_and_viewers
AG2_VIEWERS     = "195468560286"   # video_viewers_only

# Campaign 3 — original creative new targeting (Belgium Concert - Original Creative May 2026, id=23875661669)
CAMPAIGN_3_ID   = "23875661669"
UTM_CAMPAIGN_3  = "belgium_original_dg"
# Ad group IDs — Campaign 3
AG3_SUBSCRIBERS = "195520511703"   # subscribers_and_viewers
AG3_VIEWERS     = "197105972095"   # video_viewers_only

ACTIVE_CAMPAIGNS = [CAMPAIGN_2_ID, CAMPAIGN_3_ID]

# UTM content values (shared naming across both campaigns)
UTM_CONTENT_SUBSCRIBERS = "subscribers"
UTM_CONTENT_VIEWERS     = "video_viewers"

# Full final_url_suffix per ad group (source of truth — matches what's set in Google Ads)
FINAL_URL_SUFFIX = {
    AG1_SUBSCRIBERS: f"utm_source={UTM_SOURCE}&utm_medium={UTM_MEDIUM}&utm_campaign={UTM_CAMPAIGN_1}&utm_content={UTM_CONTENT_SUBSCRIBERS}",
    AG1_VIEWERS:     f"utm_source={UTM_SOURCE}&utm_medium={UTM_MEDIUM}&utm_campaign={UTM_CAMPAIGN_1}&utm_content={UTM_CONTENT_VIEWERS}",
    AG2_SUBSCRIBERS: f"utm_source={UTM_SOURCE}&utm_medium={UTM_MEDIUM}&utm_campaign={UTM_CAMPAIGN_2}&utm_content={UTM_CONTENT_SUBSCRIBERS}",
    AG2_VIEWERS:     f"utm_source={UTM_SOURCE}&utm_medium={UTM_MEDIUM}&utm_campaign={UTM_CAMPAIGN_2}&utm_content={UTM_CONTENT_VIEWERS}",
    AG3_SUBSCRIBERS: f"utm_source={UTM_SOURCE}&utm_medium={UTM_MEDIUM}&utm_campaign={UTM_CAMPAIGN_3}&utm_content={UTM_CONTENT_SUBSCRIBERS}",
    AG3_VIEWERS:     f"utm_source={UTM_SOURCE}&utm_medium={UTM_MEDIUM}&utm_campaign={UTM_CAMPAIGN_3}&utm_content={UTM_CONTENT_VIEWERS}",
}

# Attribution lookup: utm_campaign+utm_content → human label
UTM_ATTRIBUTION = {
    (UTM_CAMPAIGN_1, UTM_CONTENT_SUBSCRIBERS): "Camp1 / Subscribers",
    (UTM_CAMPAIGN_1, UTM_CONTENT_VIEWERS):     "Camp1 / Video Viewers",
    (UTM_CAMPAIGN_2, UTM_CONTENT_SUBSCRIBERS): "Camp2 New Creative / Subscribers",
    (UTM_CAMPAIGN_2, UTM_CONTENT_VIEWERS):     "Camp2 New Creative / Video Viewers",
    (UTM_CAMPAIGN_3, UTM_CONTENT_SUBSCRIBERS): "Camp3 Original Creative / Subscribers",
    (UTM_CAMPAIGN_3, UTM_CONTENT_VIEWERS):     "Camp3 Original Creative / Video Viewers",
}

# Legacy alias kept for backwards compat
UTM_CAMPAIGN = UTM_CAMPAIGN_1
AD_GROUP_SUBSCRIBERS = AG1_SUBSCRIBERS
AD_GROUP_VIEWERS     = AG1_VIEWERS
AD_GROUP_NAMES = {
    AG1_SUBSCRIBERS: "subscribers",
    AG1_VIEWERS:     "video_viewers",
    AG2_SUBSCRIBERS: "subscribers_new_creative",
    AG2_VIEWERS:     "video_viewers_new_creative",
    AG3_SUBSCRIBERS: "subscribers_original_dg",
    AG3_VIEWERS:     "video_viewers_original_dg",
}

# Hard guardrails
HARD_SPEND_CAP_PCT = 0.95
HARD_DAILY_OVERSPEND_PCT = 1.30

# Soft guardrails
SOFT_DAILY_OVERSPEND_PCT = 1.10
SOFT_NO_CONVERSION_HOURS = 48
SOFT_NO_CONVERSION_MIN_SPEND_CENTS = 5000
SOFT_CPA_ALERT_CENTS = 3000
SOFT_PACING_MIN_CONVERSIONS_BY_CONCERT = 50
