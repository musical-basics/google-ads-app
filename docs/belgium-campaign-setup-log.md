# Belgium Concert — Full Ad Campaign Setup Log

Everything we built from scratch to get the Belgium Concert (June 11, 2026)
ads live and tracked. Covers Google Ads campaign setup, API integration,
Shopify attribution, analytics, and the A/B test structure.

---

## The Goal

Sell tickets to a solo piano concert at CC De Factorij, Zaventem, Belgium.

| Detail | Value |
|---|---|
| Date | June 11, 2026, 19:30 CEST |
| Venue | Theaterzaal Maupertuis, Zaventem |
| Standard ticket | €29 |
| VIP ticket | €59 |
| Livestream | $5 (global) |
| Total capacity | ~100 seats |
| Landing page | https://belgium.musicalbasics.com |
| Shopify store | https://eu.musicalbasics.com |

---

## Architecture Overview

```
Google Ads (Demand Gen)
    └── Campaign 1: "Belgium Campaign May 13"     ← original, old creative
    └── Campaign 2: "Belgium Concert - New Creative (May 2026)" ← new creative, A/B

          Each campaign has 2 ad groups:
          ├── subscribers_and_viewers   (YouTube subscriber audience)
          └── video_viewers_only        (YouTube video viewer audience)

          Each ad group has:
          ├── 3 video assets (horizontal, portrait, short)
          ├── 1 logo asset
          ├── 1 CTA asset
          └── utm_content tag for attribution

                        ↓ click
Landing Page: belgium.musicalbasics.com (Next.js, Vercel)
                        ↓ "Get Tickets" button
Shopify: eu.musicalbasics.com/cart/...?utm_source=google&utm_medium=video
                        ↓ purchase
Supabase: belgium_daily_performance + belgium_campaign_state
                        ↓
Daily email summary → Lionel Yu
```

---

## Step 1: Google Ads Account Setup

### The account situation
- **392-212-3197** — original MusicalBasics account (fully working, YouTube linked)
- **669-230-9699** — MCC/manager account
- **315-282-9803** — sub-account "Lionel Yu Concerts" (where we ran the campaign)

We used **315-282-9803** because the campaign was already set up there.

### EU Political Advertising Confirmation
Required for ANY account targeting EU countries. Without it:
- YouTube subscriber/viewer lists show 0 users
- Remarketing audiences show "Eligible (limited)"

Fix: Google Ads UI → Admin → Account settings → EU Political Advertising → Confirm not doing political ads.

### YouTube Channel Linking
The YouTube channel must be linked **to the specific sub-account** (not just the MCC).

Fix: Google Ads (sub-account) → Tools → Linked accounts → YouTube → link channel directly.

After both of the above: lists populated within ~24 hours.

### Audiences Created
| Audience Name | Type | ID |
|---|---|---|
| MusicalBasics YouTube Subscribers | YouTube subscriber list | 347448305 |
| MusicalBasics Video Viewers | YouTube viewer list | 347677581 |
| Lookalike: Belgium Subscribers | Google-managed lookalike | auto |

---

## Step 2: Original Campaign (Campaign 1)

**Created via Google Ads UI** on May 13, 2026.

| Setting | Value |
|---|---|
| Campaign name | Belgium Campaign May 13 |
| Campaign ID | 23837741178 |
| Type | Demand Gen |
| Budget | $20/day |
| Bidding | Maximize Conversions |
| Geo | Belgium, Netherlands, Luxembourg |
| Languages | English, Dutch, French |

### Ad Groups (Campaign 1)

Two ad groups, mirroring the two audience strategies:

**1. `subscribers_and_viewers`**
- Audience: YouTube Subscribers (347448305)
- UTM: `utm_content=subscribers`

**2. `video_viewers_only`**
- Audience: YouTube Video Viewers (347677581)
- UTM: `utm_content=video_viewers`

### Video Assets (Original Creative)
- Horizontal: `https://youtu.be/1oR8bPstNtk`
- Long Portrait: `https://youtube.com/shorts/_ecW9Khci7o`
- Short Portrait: `https://youtube.com/shorts/eSvZxFWvPno`

These videos started with "We Are One" (old brand intro) in the first second.

---

## Step 3: API Integration (google-ads-app)

The `google-ads-app` repo provides:
- Daily performance sync to Supabase
- Spend/conversion tracking
- Daily email summary

### Key files
| File | Purpose |
|---|---|
| `api/_lib/google_ads_client.py` | Google Ads API client wrapper |
| `api/_lib/shopify_client.py` | Shopify order parser for UTM attribution |
| `api/_lib/supabase_client.py` | Supabase read/write |
| `api/_lib/config.py` | Constants (campaign IDs, UTM strings, etc.) |
| `api/_lib/summary_text.py` | Builds the daily email text |
| `scripts/seed_campaign.py` | One-time seed of existing campaign into Supabase |

### Google Ads Credentials
- Developer token: Test tier initially, applied for Basic after
- OAuth: Service account (`client_secret_...json`)
- `login_customer_id`: 3152829803 (sub-account, NOT the MCC)
- `google-ads.yaml` in project root (gitignored)

### Supabase Tables
```sql
belgium_campaign_state     -- campaign metadata + rolling totals
belgium_daily_performance  -- one row per campaign per day
```

### Attribution Flow
Shopify orders are matched to ad groups by `utm_content`:
```python
# In shopify_client.py
if 'utm_content=subscribers' in referrer:
    source = 'subscribers'
elif 'utm_content=video_viewers' in referrer:
    source = 'video_viewers'
```

Orders without UTM params are counted as organic.

---

## Step 4: New Creative Campaign (Campaign 2) — A/B Test Setup

### Why a new campaign?
The original videos started with "We Are One" (old brand). We trimmed 1 second
off the start of each video to create clean new creative for A/B testing.

### Video Processing
```bash
# Trim 1 second off start of each video
ffmpeg -i input.mp4 -ss 1 -c copy output_trimmed.mp4
```

Videos stored in `New Ads/` (gitignored due to large file size).

### New Creative Registered as YouTube Assets
The trimmed videos were uploaded to YouTube and registered as Google Ads assets:
| Asset | YouTube ID | Google Ads Asset ID |
|---|---|---|
| Horizontal | 1oR8bPstNtk | 363376199141 |
| Long Portrait | _ecW9Khci7o | 363376199216 |
| Short Portrait | eSvZxFWvPno | 363376163750 |

Assets registered via `AssetService.MutateAssets` with `YoutubeVideoAsset`.

### Campaign 2 Creation (via API)
Script: `scripts/create_new_creative_campaign.py`

| Setting | Value |
|---|---|
| Campaign name | Belgium Concert - New Creative (May 2026) |
| Campaign ID | 23871037379 |
| Type | Demand Gen |
| Budget | $20/day (non-shared) |
| Bidding | Maximize Conversions |
| EU political ads | NOT_APPLICABLE (value = 3) |

**Key API quirks hit during creation:**
1. `contains_eu_political_advertising` is an enum, not bool → must set to `3`
2. `explicitly_shared = False` on budget → required for Maximize Conversions
3. Campaign-level geo criteria rejected → set at ad group level instead
4. Budget name must be unique → use timestamp suffix

### Campaign 2 Ad Groups
Same structure as Campaign 1:

| Ad Group | Audience | UTM | Geo |
|---|---|---|---|
| subscribers_and_viewers (195468564846) | 347448305 | utm_content=subscribers | BE, NL, LU (ad group level) |
| video_viewers_only (195468560286) | 347677581 | utm_content=video_viewers | BE, NL, LU (ad group level) |

Geo was set at the **ad group level** (not campaign level) because Demand Gen
campaigns created via API do not accept campaign-level location criteria in v24.
See `docs/google-ads-api-gotchas.md` item #2 for full explanation.

---

## Step 5: Landing Page Performance Fixes

After ads went live, analytics showed 100% bounce rate:
- All visitors: 1 page hit, 0 seconds time on page
- All traffic from mobile
- UTM params confirmed ads were serving

**Root causes found:**

### Fix 1: Countdown showed 00:00:00 on load
The `Countdown` component initialized state as `null` and fell back to
`{ days: 0, hours: 0, mins: 0, secs: 0 }` until JS hydrated. On slow mobile
connections (2-5s for JS bundle), visitors saw `00:00:00` in giant numbers
and assumed the concert had already ended.

**Fix:** Initialize with `useState<Parts>(() => compute())` — real value from
frame 1, no zero flash.

### Fix 2: Hero background image was 2.2MB
`og-concert.jpg` (2.2MB) as a full-screen background caused 2-5s blank screen
on mobile before anything visible.

**Fix:** Compressed to 115KB using ffmpeg:
```bash
ffmpeg -i og-concert.jpg -vf "scale='min(1600,iw)':-2" -q:v 4 og-concert-opt.jpg
```
**20x size reduction**, no visible quality loss on mobile.

### Fix 3: Stage photos were 1.7MB PNGs
`lionel-barbican-barbara.png` (1.7MB) and `lionel-speaking-onstage.png` (1.7MB)
converted to JPEG at 85% quality, 1400px max width:
- `lionel-barbican-barbara.jpg` → 104KB
- `lionel-speaking-onstage.jpg` → 75KB

---

## Current State (May 22, 2026)

| Item | Status |
|---|---|
| Campaign 1 (original creative) | ✅ Live, $20/day |
| Campaign 2 (new creative, trimmed) | ✅ Live, $20/day |
| Total daily spend | $40/day |
| Geo targeting (both) | Belgium + Netherlands + Luxembourg |
| Organic ticket sales | 9 (pre-ads, not attributed to Google) |
| Attribution tracking | Working (Shopify UTM → Supabase) |
| Daily email summary | Working |
| Landing page bounce fix | ✅ Deployed |

### Remaining TODO
- [ ] Add geo targeting to Google Ads UI for Campaign 2 at campaign level (if needed)  
      *(workaround: already set at ad group level via API)*
- [ ] Set up Vercel cron jobs for automated daily sync
- [ ] Test `/api/sync/shopify` endpoint end-to-end
- [ ] Monitor Campaign 1 vs Campaign 2 performance (A/B: old vs trimmed creative)

---

## A/B Test Interpretation Guide

The two campaigns will show performance separately in Google Ads and in the daily email.

| Signal | What it means |
|---|---|
| Campaign 2 CTR > Campaign 1 | Trimmed creative (no "We Are One") is more compelling |
| Campaign 2 conversions higher | New creative drives more ticket purchases |
| `utm_content=subscribers` converting | YouTube subscriber audience is worth the spend |
| `utm_content=video_viewers` not converting | Video viewer lookalike may need refinement |

Let campaigns run for at least 7-10 days before drawing conclusions.
Google's bid strategy learning phase needs ~50 conversions to exit.
