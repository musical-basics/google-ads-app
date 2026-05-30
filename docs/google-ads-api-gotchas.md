# Google Ads API Gotchas — Belgium Campaign

Documented during the Belgium Concert campaign setup (May 2026).
These are hard-won lessons from using the Google Ads Python client library (v24)
to build and manage a **Demand Gen** campaign programmatically.

---

## 1. EU Political Ads Requirement (`contains_eu_political_advertising`)

**Problem:** Creating ANY campaign targeting EU countries requires
`contains_eu_political_advertising` to be explicitly set on the Campaign
proto. If omitted, the API returns `REQUIRED field not present` and refuses
to create the campaign.

**Gotcha:** It is **not a boolean** — it is an **enum** (`EuPoliticalAdvertisingStatus`).
Setting `campaign.contains_eu_political_advertising = False` silently does nothing
(proto3 default-value is invisible on the wire), so the server still sees it as
"not set."

**Fix:**
```python
# Inspect the enum values first
eu_enum = client.enums.EuPoliticalAdvertisingStatusEnum
# Our existing campaign returned value 3 = NOT_APPLICABLE
campaign.contains_eu_political_advertising = 3   # NOT_APPLICABLE
```

---

## 2. Demand Gen Campaigns: Geo & Language Targeting Must Be at Ad Group Level

**Problem:** For Demand Gen campaigns, setting geo/language criteria at the
**campaign level** via `CampaignCriterionService` consistently fails with:

```
"The error code is not in this version." trigger: "OWNED_AND_OPERATED"
```

This is a v24 client library mismatch — the server returns an error code the
client doesn't know about. The underlying issue is that Demand Gen campaigns
use a different targeting architecture.

**Also:** The Google Ads UI will block campaign-level location saves with:
> *"Locations cannot be added at the campaign level because this campaign
> has locations set at the ad group level."*

**Fix:** Set geo targeting at the **ad group level** using `AdGroupCriterionService`:
```python
op = client.get_type('AdGroupCriterionOperation')
op.create.ad_group = ad_group_resource
op.create.negative = False
op.create.location.geo_target_constant = 'geoTargetConstants/2056'  # Belgium
agc_service.mutate_ad_group_criteria(customer_id=cid, operations=[op])
```
This works cleanly. Do it for every ad group individually.

**Note:** The original campaign (23837741178) was created via the UI — that's
why it has campaign-level location criteria. Campaigns created via API get
ad-group level targeting instead.

---

## 3. `maximize_conversions` Is Incompatible With Shared Budgets

**Problem:** Creating a campaign with `maximize_conversions` bidding and
a **shared** budget object returns:
```
BIDDING_STRATEGY_TYPE_INCOMPATIBLE_WITH_SHARED_BUDGET
```

**Fix:** Set `budget.explicitly_shared = False` when creating the budget:
```python
budget.explicitly_shared = False   # non-shared = compatible with maximize_conversions
```

---

## 4. Ad `name` Field Is Required on Creation

**Problem:** Creating an `AdGroupAd` without setting `ad.name` returns:
```
field_error: REQUIRED — The required field was not present.
location: operations[0] > create > ad > name
```

**Fix:** Always set `ad.name` explicitly:
```python
ad.name = 'My Ad Name'
```

---

## 5. `demand_gen_multi_asset_ad` vs `demand_gen_video_responsive_ad`

**Problem:** The existing ads were queried assuming `demand_gen_multi_asset_ad`
field name. The GAQL query silently returned empty fields because the ad type
was actually `DEMAND_GEN_VIDEO_RESPONSIVE_AD`, not `DEMAND_GEN_MULTI_ASSET_AD`.

**Fix:** Check `ad_group_ad.ad.type` first:
```python
# Correct GAQL for video responsive ads:
SELECT ad_group_ad.ad.demand_gen_video_responsive_ad.headlines,
       ad_group_ad.ad.demand_gen_video_responsive_ad.videos, ...
FROM ad_group_ad WHERE ...
```

For multi-asset ads use `demand_gen_multi_asset_ad.*` instead.

---

## 6. RepeatedComposite Fields: Use `.append()` Not `.add()`

**Problem:** Proto repeated fields (headlines, videos, etc.) in the Python
client do NOT have an `.add()` method. Calling `.add()` raises `AttributeError`.

**Fix:** Create the sub-type separately, then `.append()`:
```python
# WRONG:
h = vra.headlines.add()
h.text = "My Headline"

# CORRECT:
h = client.get_type('AdTextAsset')
h.text = "My Headline"
vra.headlines.append(h)
```

Same pattern for `AdVideoAsset`, `AdImageAsset`, `AdCallToActionAsset`.

---

## 7. YouTube Subscriber/Viewer Lists Require EU Political Ads Confirmation

**Problem:** In-market and YouTube remarketing lists (subscribers, viewers)
were showing as "Eligible (limited)" with 0 audience size. The root cause
was missing **EU political ads confirmation** at the account level.

**Fix:** In Google Ads UI → Admin → Account settings → EU Political Advertising
policy → confirm the account is NOT doing political advertising. After
confirmation, remarketing lists began populating within hours.

**Note:** This is account-level and only needs to be done once.

---

## 8. YouTube Channel Must Be Linked to the Specific Ad Account

**Problem:** Even with EU political ads confirmed, YouTube subscriber/viewer
lists showed 0 users. The YouTube channel was linked to the MCC/manager
account but NOT to the sub-account (3152829803) running the campaign.

**Fix:** In the sub-account (not the MCC):
> Google Ads → Tools → Linked accounts → YouTube → Link channel

After re-linking the channel directly to the sub-account, lists propagated
within 24 hours.

---

## 9. `CampaignBudget` Names Must Be Globally Unique

**Problem:** Re-running a campaign creation script after a partial failure
raised `DUPLICATE_NAME` because the budget was created on the first attempt
(before the campaign failed).

**Fix:** Use a timestamp in budget names:
```python
import time
budget.name = f'My Campaign Budget {int(time.time())}'
```

---

## 10. `login_customer_id` Must Match the Sub-Account, Not the MCC

**Problem:** API calls succeeded for reads but failed for writes with
permission errors when `login_customer_id` was set to the MCC ID while
`customer_id` was the sub-account.

**Fix:** Set both to the same sub-account ID (3152829803):
```yaml
# google-ads.yaml
login_customer_id: 3152829803
```
Only use the MCC `login_customer_id` if you are explicitly managing
sub-accounts from the manager level.

---

## 11. `final_url_suffix` on Ad Groups for UTM A/B Attribution

To distinguish which ad group drove a Shopify ticket purchase, set
`final_url_suffix` per ad group (not per ad, not per campaign):

```python
op = client.get_type('AdGroupOperation')
ag = op.create
ag.final_url_suffix = 'utm_content=subscribers'   # or 'utm_content=video_viewers'
```

This appends to the final URL automatically on every click, so Shopify
sees `?utm_source=google&utm_medium=video&utm_campaign=belgium_tickets_be_2606
&utm_content=subscribers` for attribution.

---

## 12. Demand Gen Audience Targeting via `AdGroupCriterion.audience`

Audiences (YouTube subscribers, custom intent, etc.) are attached to ad groups
via `AdGroupCriterionService`, not at the campaign level:

```python
op = client.get_type('AdGroupCriterionOperation')
op.create.ad_group = ad_group_resource
op.create.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
op.create.audience.audience = f'customers/{cid}/audiences/{audience_id}'
agc_service.mutate_ad_group_criteria(customer_id=cid, operations=[op])
```

Audience IDs are fetched via:
```python
SELECT user_list.id, user_list.name FROM user_list
```

---

## 13. Legacy `VIDEO` Channel-Type Campaigns Are Effectively Read-Only via API

**Problem:** Any campaign with `campaign.advertising_channel_type == VIDEO`
(the legacy YouTube channel type, predecessor to Demand Gen) rejects
mutations via the API. In this account that's `belgium_original_yt`,
`belgium_new_creative_yt`, `..._with_cold_audience`, `..._diaspora_fans`.

Confirmed blocked operations (verified 2026-05-29 → 2026-05-30):

| Operation | Service | Error |
|---|---|---|
| Pause / re-enable campaign | `CampaignService.MutateCampaigns` | `MUTATE_NOT_ALLOWED, trigger=VIDEO` (clean) |
| Change campaign-level budget link | `CampaignService.MutateCampaigns` | same |
| Create a new ad in an ad group | `AdGroupAdService.MutateAdGroupAds` | `REQUIRED at video_responsive_ad` (misleading) |

The `CampaignBudgetService` itself still works (you can update budget amount),
but anything that mutates the `Campaign` object or its ads is rejected.

**The misleading-error pattern:** when v24 doesn't allow an operation on a
legacy resource type, it sometimes returns `field_error: REQUIRED` on a
parent message with **no specific subfield path**, instead of the clean
`MUTATE_NOT_ALLOWED`. Same pattern as the `OWNED_AND_OPERATED` rejection
on DG `campaign_criterion` (see Gotcha #2). **Diagnostic:** if you get
`REQUIRED` on a parent proto message with no child field indicated, and
adding obvious missing fields doesn't change the error, stop trying
variants — the operation is genuinely not permitted on that resource type.

**Workaround:** all changes to VIDEO campaigns (pause, ad creation,
creative refresh) must be done in the Google Ads UI. The campaigns
themselves still serve and spend normally.

**Tried and confirmed not to work** for ad creation on VIDEO campaigns:
- `video_responsive_ad` with 1, 3, 5 headlines
- with and without `logo_images`
- with and without `companion_banners`
- with breadcrumbs set (also has its own constraints: no `.`, max ~15 chars)
- `in_feed_video_ad` (not even a valid field on `Ad` in v24)

---

## 14. `campaign_budget.explicitly_shared` Is Immutable Post-Creation

**Problem:** Demand Gen campaigns with `maximize_conversions` bidding
**require** `campaign_budget.explicitly_shared = False`. The default when
creating a budget is `True` (shared), which causes campaign creation to
fail with `BIDDING_STRATEGY_TYPE_INCOMPATIBLE_WITH_SHARED_BUDGET`.

**Gotcha:** This flag **cannot be changed after the budget is created**.
Attempting to `mutate_campaign_budgets` with `update.explicitly_shared = False`
on an existing shared budget returns:

```
"The error code is not in this version." location: explicitly_shared
```

(another instance of the misleading-error pattern from Gotcha #13).

**Fix:** Always set `explicitly_shared = False` at create time:
```python
budget.amount_micros = 20_000_000
budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
budget.explicitly_shared = False   # required for DG + maximize_conversions
```

If you forget, the orphan budget cannot be salvaged — create a fresh one
and leave the orphan unreferenced. Orphan budgets don't spend (no campaign
links to them) but they clutter the account; delete in the UI if you care.

---

## 15. Ads Are Immutable Post-Creation — To "Update" an Ad, Create a New One

**Problem:** Once an `AdGroupAd` is created, you cannot modify its creative
content — headlines, descriptions, videos, logos, CTAs are all locked. Only
`status`, `final_urls`, `tracking_url_template`, and `url_custom_parameters`
can be updated. Trying to add a video to an existing ad's `videos` list
via update isn't possible.

**Workaround:** Create a NEW ad in the same ad group with the additional
creative. Both ads serve in parallel and Google's optimizer picks winners.
This is what `scripts/add_trailer_to_other_campaigns.py` does — it adds a
trailer-video ad alongside the existing trimmed-creative ad in each ad
group, so each ad group ends up with 2 ads competing.

This is intentional design from Google: the only way to "test" a new
creative is to run it as a parallel ad, which gives Google's smart bidding
clean A/B signal.
