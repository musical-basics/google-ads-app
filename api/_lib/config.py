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

# UTM convention
UTM_CAMPAIGN = "belgium_tickets_be_2606"
UTM_SOURCE = "google"
UTM_MEDIUM = "video"

# Ad group IDs and UTM content values (set as final_url_suffix per ad group)
AD_GROUP_SUBSCRIBERS = "196557300716"       # subscribers_and_viewers
AD_GROUP_VIEWERS     = "193972785582"       # video_viewers_only
UTM_CONTENT_SUBSCRIBERS = "subscribers"     # utm_content value for subscribers ad group
UTM_CONTENT_VIEWERS     = "video_viewers"   # utm_content value for viewers ad group
AD_GROUP_NAMES = {
    "196557300716": "subscribers",
    "193972785582": "video_viewers",
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
