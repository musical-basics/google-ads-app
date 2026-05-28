# Belgium Concert — Active Campaign Experiment (snapshot 2026-05-27)

Concert date: **2026-06-11**.
Decision review date: **2026-05-30** (interim, when credit likely activates) → **2026-06-01** (full prune).

## Google Ads credit milestone — DO NOT lower budgets before this

Active Google Ads promo: **spend $500 → receive $1000 ad credit**.

- Lifetime spend as of 2026-05-27 = **$328.29**
- Need ~$172 more to trigger credit
- At current ~$70–90/day run rate, hits threshold around **2026-05-29 or 2026-05-30**
- **Do not lower any budgets before reaching $500.** Lowering delays the trigger; doesn't save real money.
- **Do not artificially accelerate either.** Google's offers care about hitting the threshold, not speed.

### Verify before relying on the credit

In Google Ads UI: **Billing → Promotions**. Confirm:
- The offer is active on this account
- You're within the eligibility window (typically "first 60 days of spend")
- The redemption mechanic (email link, promo code, etc.)
- The credit's usage window once issued (typically 60–90 days)

### When the credit lands (probably 2026-05-29 / 05-30)

- Effective budget jumps from ~$80/day real spend to ~$160/day total ($80 real + $80 credit) for the remaining ~12 days
- **Don't spread the $1000 across all 4 campaigns evenly.** Use the 3 days of conversion data (May 27–30) to identify the campaign with the best real-money CPA, and concentrate the credit into the winner. Concentrated bets win in short windows.
- Update budget table here when the credit hits + winner is chosen.

## Live campaigns

| # | Campaign | ID | Channel | Strategy | Budget | Audience | Geo | AE | Hypothesis |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `belgium_new_creative_yt` | 23873822810 | VIDEO | TARGET_CPV $0.30 | $40/day | warm: YT subs + video viewers | BE | OFF | Control. Produced thaituanminh55 ($33.76). |
| 2 | `belgium_new_creative_yt diaspora_fans` (renamed from `added NL` 2026-05-28) | 23884972699 | VIDEO | TARGET_CPV | $40/day | warm: YT subscribers only (video_viewers ad group PAUSED 2026-05-28) | BE + NL + LU + UK + FR + DE | **ON** | Find more Dianas — confirmed MB fans (YT subscribers) anywhere within Eurostar/Thalys range to Zaventem. Inspired by Diana Krilova ($134 VIP, London, organic via uk.musicalbasics.com). |
| 3 | `belgium_new_creative_yt with cold audience` | 23875386621 | VIDEO | TARGET_CPV $0.30 | $15/day | Custom Intent (cold): "belgium piano concert", "musicalbasics", etc. (audience id 980902472) | BE + NL + LU | ON | Can cold custom-intent searchers convert at acceptable CPA? |
| 4 | `Belgium Concert - New Creative (May 2026)` | 23871037379 | DEMAND_GEN | MAXIMIZE_CONVERSIONS | $40/day | YT video viewers | BE+NL+LU+UK+FR+DE | n/a | Produced hiamusic ($67.42 view-through). Re-enabled 2026-05-27. Geo expanded from BE+LU to 6-country reasonable-travel range on 2026-05-28. |
| 5 | `Belgium Concert - Original Creative (May 2026)` | 23875661669 | DEMAND_GEN | MAXIMIZE_CONVERSIONS | $20/day | YT video viewers | BE+NL+LU+UK+FR+DE | n/a | Re-enabled 2026-05-27. Geo expanded from BE+LU+NL to 6-country range on 2026-05-28. |

**Important: DG campaigns set geo at the ad-group level, NOT campaign level.** Query `ad_group_criterion` (not `campaign_criterion`) to inspect, and mutate via `AdGroupCriterionService` to update. `campaign_criterion` is empty for DG = misleading — looks like global targeting but isn't.

## Paused (do not unpause without re-evaluating)

| Campaign | ID | Why paused |
|---|---|---|
| `belgium_original_yt` | 23868517434 | User paused — old creative |
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

## Decision rules

### Audience Expansion monitoring rule for `belgium_new_creative_yt diaspora_fans` (added 2026-05-28)

This campaign has Audience Expansion ON in the `subscribers_and_viewers` ad group, so Google will reach beyond your YT subscriber seed to "people similar to subscribers" in the 6 included countries. That's intentional — the whole point is to find more Dianas.

**Review on 2026-05-29** (1 day after geo expansion). Pull AE off if EITHER:

- New visitors from UK / FR / DE arrive but median dwell is <15s and zero CTA clicks. That means Google's "similar to subscriber" definition is too loose for these geos and we're paying for low-interest fans-of-fans-of-fans.
- Spend ramps significantly (e.g., >$25/day on this campaign) while CTR drops below 0.3% across the campaign. AE is finding cheap inventory at the cost of fan quality.

If either trigger fires, turn AE off in the ad group (UI: Ad groups → subscribers_and_viewers → Settings → Audience expansion → Off). With AE off, the campaign will only serve to your literal YT subscriber list across the 6 geos — much tighter, much smaller, but very high-intent.

### Cold custom intent campaign — kill switch on 2026-05-29

`belgium_new_creative_yt with cold audience` (id 23875386621) was reduced to $20/day on 2026-05-28. User's assessment: cold custom intent is producing noise, not Dianas. If by EOD 2026-05-29 it has 0 attributed Shopify Purchase conversions, **pause it** and move that budget to the diaspora campaign.

### Interim check on 2026-05-30 (when credit likely lands)

Use 3 days of conversion data (post-tracking-fix on 05-27) to **pick the campaign to concentrate the $1000 credit into**.

- **Decision is data-driven — don't pre-commit to a channel.** Wait to see which campaign(s) actually produce Shopify Purchase conversions in the May 27–30 window before allocating.
- **Best campaign** = lowest CPA on Shopify Purchase conversions
- If no campaign has any conversions by 05-30: rank by Shopify-CTA-click rate; if still tied, rank by engagement (≥30s session %) from analytics_logs
- Bump the winner's budget by **+$80/day** for the next ~12 days (eating the credit)
- Leave the other campaigns at current budgets so the A/B test continues to surface signal

### Note: DG vs VIDEO so far (48h sample, small N — informational only)

In the 48h before snapshot, DG outperformed VIDEO on every dimension that matters:
- Deep engagement rate (≥30s): DG 33% vs VIDEO 22%
- CTA click rate: DG 67% vs VIDEO 11%
- Per-session conversion rate: DG 16.7% vs VIDEO 5.6%
- Per-session revenue: DG $11.20 vs VIDEO $1.87

This is **informational, not deciding**. N = 6 DG sessions vs 18 VIDEO; one outlier (3,745s tab-left-open) inflates DG. But there's a structural reason DG could be better: MAX_CONVERSIONS selects for likely-buyers, while TARGET_CPV selects for cheap-watchers. Worth keeping an eye on this when the 05-30 conversion data comes in.

### Full prune on 2026-06-01 (5 days post-snapshot)

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

- **Don't lower any campaign budgets before lifetime spend hits $500** — would delay the credit trigger.
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
