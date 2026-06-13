# Belgium Concert Campaign — Final Attribution & Lessons

Concert date: 2026-06-11. Campaign window: 2026-05-13 → 2026-06-13 (incl. post-concert overrun).

## Final numbers

| Metric | Value |
|---|---:|
| Total ad spend | **€2,214.69** |
| Ad-attributed revenue (Shopify landing_site) | €236.73 |
| Ad-attributed revenue (Google Ads gclid cookie) | €310.48 |
| Total revenue across ALL channels (paid + organic) | €1,121.00 |
| **ROAS (direct ad attribution)** | **0.11x – 0.14x** |
| ROAS if you credit ALL revenue to ads (charitable) | 0.51x |
| Net loss on ads alone | -€1,900 to -€1,978 |
| Post-concert wasted spend (6/12 + 6/13) | €148.74 |

## The 4 ad-attributed sales

| Order | Buyer | Date | Campaign | Click→buy | Total |
|---|---|---|---|---:|---:|
| #7167 | Minh Thái | 5/24 | belgium_new_creative_yt (YT) | 21h27m | €33.76 |
| #7182 | Olaf Jacobs (VIP) | 5/29 | belgium_original_dg | 1h43m | €68.85 |
| #7214 | Samyn Jeroen | 6/4 | belgium_new_creative_dg | 13min | €67.30 |
| #7242 | Frederic Marty | 6/7 | belgium_original_dg | – | €66.82 |

Plus 1 hidden via gclid cookie (Shopify said direct):
- #7171 Manu Brees, 5/27, belgium_new_creative_dg, €67.42

## Per-campaign post-mortem

### Winners
- **Belgium Concert - Original Creative (May 2026) (DG)** — 2 ad-attributed sales (Olaf VIP + Frederic). Original Moonlight Sonata V4/V5 trimmed creative did the closing.
- **Belgium Concert - New Creative (May 2026) (DG)** — 2 ad-attributed sales (Manu via cookie + Samyn). The new trailer ad (added 5/30) closed Samyn — first sale by that creative.

### Losers
- **belgium_new_creative_yt with cold audience** — €114 spent, 23k impressions, 0 sales. Pure waste.
- **belgium_new_creative_yt diaspora_fans** — €102 spent, 0 sales. "Belgians abroad" don't travel for niche events.
- **belgium_original_yt** (legacy VIDEO type) — €46 spent, 0 ad-attributed sales.
- **Belgium Campaign May 13** — paused early, never produced.

## Critical findings

### 1. Final-stretch (6/5 → 6/10) was the worst window
Spent **€579.94** for **1 ad-attributed sale (€66.82)**. ROAS = 0.12x. This is the opposite of what's expected — urgency conversions should peak in the final week. They didn't because the most likely buyer pool (Belgian email + YouTube subscribers) had already been exhausted by organic/email channels before urgency week.

**Implication for next event:** budgets should ramp DOWN as the event approaches, not stay flat or ramp up. Front-load spend in weeks 3-4 before event, taper in the final week.

### 2. The CTA quantity bug on variant M plausibly cost real revenue
On variant M:
- `m_sticky_mobile` → hardcodes `quantity=1` in the cart URL
- `m_hero_ticket` → hardcodes `quantity=1`
- `m_band_ticket` → quantity-selectable (correct)

Samyn tried 3 CTAs before getting to quantity=2. Most buyers wouldn't have. Estimated lost revenue: 1 extra ticket per "buying for 2" prospect on M who clicked sticky or hero first. Could be 3-5 additional tickets across the campaign.

### 3. Smart bidding learning phase ate ~10 days
Stacked changes within 72h on 5/27-5/29 (CTA Click goal demoted, DG budgets doubled, new Trailer launched, 2 YT campaigns paused) all reset `LEARNING_NEW`. Algorithm didn't fully exit learning until ~6/5, leaving only 6 days of "optimized" performance — which also flopped.

**Implication for next event:** make ONE change at a time, then wait 5-7 days. Don't stack changes ever.

### 4. CTA Click was inflating the conversions metric
Original conversion goal setup counted `CTA Click` (landing page button clicks) at €1 each as a primary conversion. Smart bidding was optimizing for cheap CTA clicks instead of actual ticket sales. Demoted 5/27 — should be primary=False from day 1 on any future campaign.

### 5. Legacy VIDEO campaigns are read-only via API
Cannot pause, cannot add new creative, cannot change status. Only DG campaigns are fully API-controllable in 2026. For all future events, **use Demand Gen only**.

### 6. The "audience" lever didn't deliver
- `subscribers_and_viewers` (warm) had the best per-click quality but ran out of buyers fast
- `video_viewers_only` (cold YouTube piano viewers) was wildly inconsistent — some closed sales (Rui, Frederic, Samyn) but mostly bouncy traffic
- `with cold audience` and `diaspora_fans` were pure money fires

The takeaway: **defining the audience as "people who watched piano content on YouTube" is way too broad.** It's the same as targeting "people interested in cooking" for a specific restaurant in Antwerp.

## Next-event playbook (Lionel's directive: $10/campaign, 1-2 campaigns max, highest-intent only)

### Realistic budget math at $10/day
At €10/day per campaign × 30 days = €300 total. To beat 1.0x ROAS, you need ~5 standard tickets (€33) OR 2-3 VIP tickets. That's achievable only if every paid click is high-intent.

**Caveat:** Demand Gen smart bidding officially needs €25-50/day minimum to converge. At €10/day you'll be in semi-permanent LEARNING. So accept that bidding will be noisier and put MORE weight on tight audience targeting to compensate.

### Audience segments ranked from best to worst for "highest intent"

#### TIER 1 — Use these. Highest intent.

1. **Website remarketing (LP visitors who didn't buy)** — set up Google Tag on belgium.musicalbasics.com, build "Site visitors past 30 days, no purchase event" audience. These people already saw your concert page and showed interest. Smallest audience, highest CTR, lowest CPC.

2. **Customer Match: past Musical Basics ticket buyers** — upload emails of anyone who bought a Belgium concert ticket (or earlier event ticket) to Google Ads via Customer Match. Their lifetime fan value is highest. Use them for the NEXT event.

3. **Customer Match: email-engaged subscribers** — upload emails of people who clicked or opened a Belgium-concert email but didn't buy. These are confirmed interested-but-undecided.

4. **YouTube engaged-view of your concert trailer** — viewers who watched ≥50% of YOUR concert trailer specifically (NOT generic piano content). Tight filter, real intent.

#### TIER 2 — Maybe. Lower intent but cheap.

5. **YouTube subscribers + 30-day video viewers** — your channel subscribers + recent video watchers. This is what `subscribers_and_viewers` was on this campaign. Has worked occasionally.

6. **Lookalike of past ticket buyers** — Google builds a similar-audience from your Customer Match upload. Use only after Tier 1 is exhausted.

#### TIER 3 — Skip these next time. They burned money this round.

7. ❌ Custom intent based on generic keywords like "piano", "classical music"
8. ❌ Affinity audiences ("Music Lovers")
9. ❌ "video viewers of piano content generally" — too broad
10. ❌ "Diaspora" / Belgians abroad — physically can't attend
11. ❌ Lookalike of YouTube subscribers — too dilute for niche local events

### Specific setup for $10/day, 1-2 campaigns

**Recommended config for next event:**
- **1 Demand Gen campaign** at €10/day
- **1 ad group** with audience = Tier 1.1 (website remarketing) + Tier 1.3 (email-engaged Customer Match) STACKED (Google ANDs them if both attached)
- **1 ad** with the most-proven creative (Moonlight Sonata V4 + the new Belgium Concert Trailer)
- **Geo**: BE + NL + LU only (tight)
- **Languages**: NL, FR, EN
- **Bidding**: Maximize Conversions, NOT target CPA (you don't have enough volume for target CPA to converge)
- **End date**: set at creation. Always. (Hard learned lesson — we missed €148 to this)
- **Primary conversion**: Shopify Purchase ONLY. Never CTA Click or Waitlist Signup as primary.

**If you have budget for a 2nd campaign:**
- Same structure but audience = Tier 1.4 (engaged-view of concert trailer)
- Lets you A/B which audience converts better

**Don't add a 3rd campaign during the run.** Each new entrant triggers ~7 days of re-learning on your other campaigns.

## Operational rules learned (do these every time)

1. Set `campaign.end_date_time` at creation. The DG creation scripts in this repo currently DON'T — fix that before next event.
2. Set `campaign.contains_eu_political_advertising` (required for any EU-serving campaign).
3. Set `campaign_budget.explicitly_shared = False` for DG + maximize_conversions (required, immutable post-create).
4. Add geo + language criteria at the **ad group level** (`ad_group_criterion`), NOT campaign level. DG rejects campaign-level.
5. Only ONE primary conversion action. Demote everything else.
6. ONE change at a time, then wait 5-7 days for learning to stabilize.
7. Daily post-flight check: confirm bidding status, spend trajectory, and ad-attributed conversion count. Don't wait for the user to notice problems.
