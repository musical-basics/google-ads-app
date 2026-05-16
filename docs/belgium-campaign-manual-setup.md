# Belgium concert ad campaign: manual UI setup spec

Copy-pasteable spec of every Google Ads UI field for the Belgium concert
campaign. If you have to recreate the campaign in a different account, or
hand the setup to someone else, work through this top to bottom.

This complements `MusicalBasics-Productions-Google-Ads-API-Design-Doc.pdf`
(the original build spec) and `shopify-eu-pricing.md` (the variant + checkout
URL story). When the production Google Ads developer token approves we will
replace this manual flow with `/api/campaign/create`, but for now the
campaign is built by clicking through the UI.

Concert: solo piano, **2026-06-11**, CC De Factorij, Zaventem, Belgium.
Venue capacity 100 seats. Standard €29, VIP €59.

---

## 1. Pick the right Google Ads account

Three accounts in play. Pick one based on availability of warm targeting.

| Customer ID | Name | Role | YouTube linked? |
|---|---|---|---|
| 392-212-3197 | MusicalBasics (old) | Standalone ad account | Yes, fully propagated |
| 669-230-9699 | MusicalBasics (manager) | MCC, no campaigns directly | Yes, recently linked (propagating) |
| 315-282-9803 | Lionel Yu Concerts | Sub-account under 669 | Pending propagation |

**Use 392-212-3197 if YouTube subscriber/viewer targeting is needed today.**
It already has the YouTube data segments available and historical ad-spend
reputation. The Belgium campaign should live here for fastest launch.

**Use 315-282-9803 only if 392 is unavailable** (billing issue, suspended
account, etc.). Falls back to custom-segment targeting until YouTube link
propagates.

The ticket-sale certification is per-account. Whichever account is used,
file the cert application at:
`https://support.google.com/adspolicy/contact/event_ticket_request`
as **Primary seller** for MusicalBasics Productions LLC.

---

## 2. Campaign settings

Create a new campaign. Pick **Demand Gen** (Video Action campaigns were
retired and auto-upgrade to Demand Gen).

### Campaign name

```
belgium_tickets_be_2606
```

(Matches `CAMPAIGN_NAME` in `api/_lib/config.py`. Will be re-used by the
API when developer token approves.)

### Campaign goal

**Conversions** is the default selector, but pick **Clicks** for this run.

Rationale: at $18/day with no working conversion tracking through
Shopify-Google integration (Brand Account identity mismatch blocks it),
Maximize Conversions has nothing to optimize on. Maximize Clicks gives
predictable cost per click. Real-world attribution comes through UTMs
into Supabase, not Google's conversion pixel.

### Bidding

**Maximize clicks**, no Target CPC. Leave the optional Target CPC box
unchecked so Google has full flexibility to find cheap inventory.

### Budget and dates

| Field | Value |
|---|---|
| Budget type | Daily |
| Daily amount | $18.00 USD (~€16-17, calibrated to €500 total over 29 days) |
| Start date | The day of launch (e.g. 2026-05-13) |
| End date | **2026-06-10** (day before concert) |

The end date is non-negotiable. Belt and suspenders with the
`/api/guardrails/check` hard rule that pauses after `CONCERT_DATE - 1`.

### Customer acquisition

Leave **unchecked**. Requires Customer Match list, which we don't have.

### Brand guidelines

Optional. If filling: Main color = MB brand yellow, Accent = black,
Font = any. Skip if no time.

### EU political ads

**No, this campaign doesn't have EU political ads.** Required field
under EU regulation. Concert promotion is not political ad content.

### Location and language

Toggle **"Use campaign location and language settings"** ON so it overrides
ad group defaults.

**For any selected locations, use**:
- **Presence: People in or regularly in your included location** (NOT
  "Presence or interest" - we want people who can physically attend).

**Locations** (4 total, all "country" or "region" granularity):

| Location | Type | Reach (approx) |
|---|---|---|
| Belgium | Country | 11.7M |
| Netherlands | Country | 34.2M |
| Luxembourg | Country | 1.0M |
| Hauts-de-France | Region of France | varies |

Hauts-de-France covers Lille / Roubaix / Valenciennes area, the
driving-distance slice of France from Zaventem. Don't add the whole of
France or Grand Est - dilutes budget on people too far to drive.

**Languages** (add 3):
- English
- Dutch
- French

Do NOT default to "All languages" - wastes impressions on people who
can't read the ad copy.

### Devices

Leave default: **All eligible devices** (computers, mobile, tablet, TV).

### Ad schedule

**All day**.

### Third-party measurement

Skip.

### Campaign URL options

**Tracking template**: leave blank.

**Final URL suffix**: paste exactly this (one line, no spaces):

```
utm_source=google&utm_medium=video&utm_campaign=belgium_tickets_be_2606&utm_content={adgroupid}&utm_term={creative}
```

The `{adgroupid}` and `{creative}` are Google's ValueTrack placeholders.
They get substituted per click with real numeric IDs. These flow through
to `belgium_ticket_sales.utm_content` and `utm_term` in Supabase via the
`/api/sync/shopify` pipeline.

**Custom parameters**: empty.

**Companion banner**: Autogenerate using your channel banner (uses MB
YouTube channel banner for the desktop sidebar slot).

### IP exclusions

None.

---

## 3. Ad group

One ad group only. The spec called for two (warm + lookalike) but on
$18/day budget there is no headroom to split. Run one warm-focused group
and evaluate at 14-day mark whether to expand to cold.

### Ad group name

```
subscribers_and_viewers
```

### Channels

**All Google channels** (default). Do NOT check "Include Google Display
Network" - that adds banner inventory on random sites which burns budget
on irrelevant placements.

### Audience

This is the load-bearing setting. Two paths depending on which account
is in use.

**Path A: account 392 (YouTube linked, working)**

Create a new audience with name `MB Belgium concert (warm)`:

- **Custom segments** (always do this regardless of path): add search
  terms below.
- **Your data → YouTube users** segment:
  - Channel: Musical Basics
  - Segment: People who subscribed + People who viewed any video, last 90 days
- **Interests & detailed demographics**: Classical music, Piano,
  Concerts & musical events, Music lovers

**Path B: account 315 (YouTube data not yet propagated)**

Same as Path A but skip the "Your data → YouTube users" segment. Add the
YouTube users segment later via "Edit audience" when the link propagates
(checked at https://ads.google.com/aw/admin/linkedaccounts).

**Custom segment search terms** (paste each as a separate keyword):

```
piano concert belgium
rachmaninoff live
chopin piano concert
classical piano live
musical basics
lionel yu
piano concert brussels
classical music belgium
piano recital
moonlight sonata
```

**Custom segment URLs** (sites people visit):

```
musicalbasics.com
youtube.com/@musicalbasics
bachtrack.com
concertgebouw.nl
```

### Optimized targeting

**Unchecked.** Enabling it lets Google ignore your selected audience and
serve to people it predicts "might convert" outside the audience. That
defeats warm retargeting and pisses away budget on random users.

### Ad group URL options

Leave **empty**. The campaign-level UTM suffix cascades down. Adding
suffix here would double-append UTMs and break attribution.

---

## 4. Ad creative

Single ad. No rotation, no A/B test (per spec).

### Ad type

**Video ad** (NOT Single image / Carousel image).

### Ad name

```
belgium_concert_video_v1
```

### Final URL

```
https://belgium.musicalbasics.com
```

### Display URL paths (optional polish)

| Path 1 | Path 2 |
|---|---|
| `tickets` | `june-11` |

Makes displayed URL read `belgium.musicalbasics.com/tickets/june-11`.
Cosmetic only.

### Videos (paste all 4 YouTube URLs)

```
https://youtu.be/w_dl1Zadb7k       # 45s landscape (primary)
https://youtu.be/73-DQLkHgmw       # 15s landscape
https://youtube.com/shorts/Q0UWYfaM-Zw    # 45s portrait
https://youtube.com/shorts/4knXOmkKUrg    # 15s portrait
```

Demand Gen auto-pairs format to placement (portrait → Shorts, landscape →
in-feed and in-stream). Leave **"Choose where your videos show"** OFF.

### Logos

Upload MB channel logo (square).

### Short headlines (40 chars max, 3-5)

```
Belgium Piano Concert
Live in Zaventem June 11
Musical Basics Live
Solo Piano, June 11 2026
Reserve Your Seat Today
```

### Long headline (90 chars max)

```
Lionel Yu plays solo piano live in Zaventem, Belgium. June 11, 2026.
```

### Descriptions (90 chars max, 2-3)

```
Reserve your seat for a one-night solo piano concert near Brussels.
100 seats, June 11 only. Standard €29, VIP €59.
From the Musical Basics channel. An evening of classical piano.
```

### Business name

```
MusicalBasics
```

### Call to action

```
Book now
```

### Sitelinks

Skip. Single-event campaign with one product, sitelinks add no value.

### Asset optimization

Click **Manage** and turn OFF all three sub-toggles:

- Shorter videos: OFF (Google's auto-cuts on music produce bad freeze frames)
- Resized videos: OFF (you have manual portrait variants already)
- Landing page previews: OFF (legal risk on image rights, and quality varies)

### URL and other options (ad-level)

Leave tracking template, final URL suffix, and custom parameters blank
at the ad level. Campaign-level handles UTMs.

---

## 5. Pre-launch checklist

Before flipping to ENABLED:

- [ ] Ticket-sale certification approved (check Policy Manager → Ads tab).
      Disapproved ads with `Event ticket sale` policy will not serve.
      Apply at https://support.google.com/adspolicy/contact/event_ticket_request
      as Primary seller with venue contract proof.
- [ ] Refund / cancellation policy visible on belgium.musicalbasics.com.
      Required for the cert application to pass.
- [ ] Billing method set on the chosen account (Tools → Billing → Summary).
- [ ] Conversion action exists (Tools → Conversions). Even though we
      bid on Clicks, having Purchases conversion firing lets us see ROAS
      in Google Ads UI as a sanity check against Supabase.
- [ ] Ad strength shows Good or Excellent.
- [ ] Daily budget cap matches plan ($18) and end date is 2026-06-10.
- [ ] UTM suffix saved at campaign level (not ad-group or ad level).
- [ ] All 4 videos uploaded and Public or Unlisted on YouTube (NOT
      Private - Google can't serve a private video).
- [ ] Audience has at least one signal (custom segment, interests, or
      YouTube data).

---

## 6. Post-launch monitoring

The agent calls these endpoints automatically once the production
developer token approves. Until then, monitor via the Google Ads UI and
the `/api/sync/shopify` endpoint manually.

| When | Action |
|---|---|
| Daily 06:00 ET | `POST /api/sync/shopify` |
| Daily 07:00 ET | `POST /api/notify/daily_summary` |
| Manual | Check Google Ads UI for spend, CTR, CPC |
| 2026-06-10 23:59 Brussels | Pause campaign (or rely on the end date) |

### Hand-pause conditions

If any of these tripwires fire before the agent automates pausing, pause
manually in the UI:

- Spend reaches $475 (95% of $500 cap)
- Any single day spends > $24 (130% of daily $18)
- 48 hours with $50+ spent and zero ad-attributed orders in
  `belgium_ticket_sales`
- 7-day average CPA > €30 (above ticket price)

---

## 7. Decisions log

Why each choice was made.

**Demand Gen instead of Video Action.** Google retired Video Action in
2024. Demand Gen is the auto-migration target and what's available in
the UI now. Functionally equivalent for our purpose with the added side
effect of also serving on Discover and Gmail (acceptable drift from the
spec's "YouTube only").

**Clicks bidding, not Conversions.** $18/day is too small for Google's
Conversions ML to learn (needs ~30 conversions to find a pattern). And
Shopify-Google conversion tracking is unreliable due to the Brand
Account identity mismatch. UTM attribution into Supabase is the truth
signal for this campaign.

**One ad group, not two.** Spec called for warm + lookalike. At $500
total budget, splitting between warm and cold testing means neither tier
gets enough impressions to learn. Run only warm; if budget remains
after 14 days, consider opening a second ad group with cold targeting.

**Optimized targeting OFF.** Defeats the entire point of warm-audience
retargeting. Don't let Google expand outside the selected audience.

**No Display Network.** Spec is explicit about YouTube focus. Display
Network adds bad banner inventory at low CPM that doesn't convert for a
classical piano concert.

**Asset optimization OFF.** For a creative-controlled music ad,
auto-generated cuts and resizes produce inconsistent quality. You
manually uploaded properly-framed videos at both durations and both
orientations; Google's variants would only dilute.

**No sitelinks.** One landing page, one product, single-decision moment.
Sitelinks make sense for multi-product retailers.

**Final URL suffix at campaign level only.** Cascades to ad groups and
ads automatically. Duplicating at lower levels causes double UTM keys in
the destination URL, which `parse_qs` in Python handles inconsistently.

**€18/day, not €17.** Account billing is in USD even though the budget
is in EUR. $18 USD × 29 days ≈ €475 at current FX, just under the €500
target with margin for end-of-day Google overspend.

**End date 2026-06-10.** Day before concert. Belt and suspenders
alongside `/api/guardrails/check` auto-pause. Even if our automation
fails, Google itself refuses to serve after the end date.

**Hauts-de-France, not full France.** Driving distance from Zaventem
caps at roughly Lille / Reims. Adding all of France dilutes budget on
people physically unable to attend.

**Presence-only location targeting, not Presence + Interest.** "Interest"
adds people in California who watched a Belgium travel video, which is
useless for ticket sales.

---

## 8. When the production developer token approves

The manual setup becomes the baseline. The API replaces it:

1. Set `GOOGLE_ADS_CUSTOMER_ID` env to the account that hosts the
   campaign (392 or 315).
2. Set `AUDIENCE_SUBSCRIBERS_ID` and `AUDIENCE_CUSTOM_INTENT_ID` env to
   the user-list IDs of the audiences you built manually (find them in
   Tools → Audience manager → Audience lists → [your audience] → URL
   has the numeric ID).
3. Call `POST /api/campaign/create` with `dry_run: true` to inspect the
   plan. If the plan looks like a duplicate of this manual setup, flip
   `dry_run: false` to create the campaign via API (probably pause the
   manual one first to avoid running two side by side).
4. Existing manual campaign's performance data does NOT carry over to
   the API-created campaign. Plan for ~3 days of re-learning when
   switching.

In practice you may just keep the manual campaign for the duration of
the Belgium concert and use the API path for the next campaign. This
codebase is throwaway per the build spec.
