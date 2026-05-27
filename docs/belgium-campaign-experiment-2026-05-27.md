# Belgium Concert — Active Campaign Experiment (snapshot 2026-05-27)

Concert date: **2026-06-11**. Decision review date: **2026-06-01** (5 days from snapshot).

## Live campaigns

| # | Campaign | ID | Channel | Strategy | Budget | Audience | Geo | AE | Hypothesis |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `belgium_new_creative_yt` | 23873822810 | VIDEO | TARGET_CPV $0.30 | $40/day | warm: YT subs + video viewers | BE | OFF | Control. Produced thaituanminh55 ($33.76). |
| 2 | `belgium_new_creative_yt added NL` | 23884972699 | VIDEO | TARGET_CPV | (check) | warm: same as #1 | BE + NL | **ON** | Does Audience Expansion + NL grow the warm pool profitably, or dilute it? |
| 3 | `belgium_new_creative_yt with cold audience` | 23875386621 | VIDEO | TARGET_CPV $0.30 | $15/day | Custom Intent (cold): "belgium piano concert", "musicalbasics", etc. (audience id 980902472) | BE + NL + LU | ON | Can cold custom-intent searchers convert at acceptable CPA? |
| 4 | `Belgium Concert - New Creative (May 2026)` | 23871037379 | DEMAND_GEN | MAXIMIZE_CONVERSIONS | $40/day | YT video viewers | (DG default) | n/a | Produced hiamusic ($67.42 view-through). Re-enabled 2026-05-27 after analytics caught the missed attribution. |

## Paused (do not unpause without re-evaluating)

| Campaign | ID | Why paused |
|---|---|---|
| `belgium_original_yt` | 23868517434 | User paused — old creative |
| `Belgium Concert - Original Creative (May 2026)` | 23875661669 | DG with original creative, $35 spent / 0 attributed sales |
| `Belgium Campaign May 13` | 23837741178 | TARGET_SPEND blew $41 in 1 day with 0 conversions |

## Conversion tracking — closed-loop as of 2026-05-27

- Landing page (belgium.musicalbasics.com) captures `gclid` / `wbraid` / `gbraid` from URL → sessionStorage on first visit
- All CTAs forward the click id into the Shopify checkout URL
- Shopify order's `landingPageUrl` preserves the click id
- Vercel cron (every 2h) on `google-ads-app` pulls Shopify orders + Supabase analytics events containing any click id, uploads as Google Ads offline conversions
- **Conversion action**: `Shopify Purchase` (id 7623562550, UPLOAD_CLICKS / PURCHASE category) — Primary under the Purchases goal across all 7 campaigns
- Demoted to Secondary: `YouTube follow-on views`, `YouTube channel subscriptions` (engagement noise)
- Seeded with 2 historical purchases manually:
  - thaituanminh55 ($33.76 via wbraid → campaign #1)
  - hiamusic ($67.42 via gclid → campaign #4)

**Known gap**: Shopify orders that arrive with no click id (because the customer returned "directly" on a later session) are NOT auto-uploaded by the cron. hiamusic's purchase fell into this gap and had to be uploaded manually. To close this fully, the cron would need to look up the buyer's analytics history by email/IP and recover the original click id — not yet built.

## Decision rules for 2026-06-01

Apply after the 4 live campaigns have ~5 days of post-tracking-fix data.

### Warm campaigns (#1 vs #2 — the AE+NL test)

- If **#2 (`added NL`)** has **lower CPV AND ≥1 attributed Shopify Purchase** → **keep #2, pause #1.** AE+NL won the warm A/B.
- If **#2 has higher CPV OR zero conversions while #1 has any** → **pause #2, keep #1.** AE diluted; revert to tight warm targeting.
- If both look similar (no attributed purchases either way) → keep the cheaper-CPV one, pause the other.

### Cold campaign (#3)

- ≥1 attributed Shopify Purchase by 06-01 → scale to $30/day, leave AE on.
- 0 purchases but CTA-click rate ≥ 0.5% → give it 3 more days at current budget.
- 0 purchases and CTA-click rate < 0.5% → pause. Cold custom-intent didn't fire in the available window.

### Demand Gen (#4)

- Now that purchase tracking is closed-loop, MAX_CONVERSIONS should optimize on real sales rather than YT follow-on views.
- If by 06-01 attributed CPA ≤ $30 → keep at $40/day or scale to $60.
- If attributed CPA > $50 → drop budget to $20/day, do not pause yet (may improve as bidder learns from offline purchase uploads, which take 24–72h to influence bidding).
- If 0 attributed sales by 06-01 → pause again. The hiamusic conversion was a single data point.

## Things NOT to do before 2026-06-01

- Don't add a second Demand Gen campaign with "different creative". MAX_CONVERSIONS needs consolidated conversion data; splitting it slows learning.
- Don't pause anything for "consolidation" reasons — TARGET_CPV doesn't fragment learning the way MAX_CONVERSIONS does. Pause based on data, not symmetry.
- Don't change the bidding strategy on #4 to TARGET_CPA yet. TARGET_CPA needs 10–30 conversions of history to function; we have 2 seeds.

## Things still pending (manual / not yet done)

- WEBPAGE_CODELESS "Purchase" action (id 7608410110) is still set as Primary in the Purchases goal alongside Shopify Purchase. It never fires (no tag on eu.musicalbasics.com checkout). Optional cleanup: demote it to Secondary so the goal optimizes purely on Shopify Purchase.
- "Lost-attribution" purchases (orders with no click id, where buyer was previously tagged in analytics) — pipeline doesn't recover these automatically. If a high-value sale falls into this gap, upload manually using the analytics gclid/wbraid.

## Key facts to remember in 4 days

- thaituanminh55 = **warm campaign #1**, wbraid (iOS), $33.76
- hiamusic = **DG campaign #4**, gclid, $67.42 — **view-through attribution** (clicked ad on day 1, bought on day 2 from a "direct" session). Analytics caught it via anonymous_id continuity; Shopify alone would have called this "direct/organic".
- Both purchases are now uploaded as Shopify Purchase conversions and should be visible in Google Ads reports within 24h of 2026-05-27.

## Quick API commands for the 06-01 review

```bash
# From google-ads-app/
source .venv/bin/activate

# Pull campaign performance, last 7 days
python3 -c "
import sys; sys.path.insert(0,'.')
from dotenv import load_dotenv; load_dotenv('.env.local')
from api._lib.google_ads_client import get_client, customer_id
client = get_client(); svc = client.get_service('GoogleAdsService')
q = '''SELECT campaign.id, campaign.name, campaign.status, metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.ctr, metrics.conversions, metrics.conversions_value FROM campaign WHERE campaign.name LIKE \\'%elgium%\\' AND segments.date DURING LAST_7_DAYS'''
for r in svc.search(customer_id=customer_id(), query=q):
    m = r.metrics
    print(f'{r.campaign.name[:45]:<45} | {r.campaign.status.name:<7} | spend=\${m.cost_micros/1_000_000:>6.2f} | conv={m.conversions:>4.1f} | val=\${m.conversions_value:>6.2f} | ctr={(m.ctr or 0)*100:.2f}%')
"
```

```bash
# Re-check engagement / dwell for ad sessions (from belgium-concert-landing-page/)
# (see analytics_logs analysis in this conversation for the query)
```
