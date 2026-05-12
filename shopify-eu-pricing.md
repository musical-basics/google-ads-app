# Shopify EU Pricing Setup

How we set fixed EUR prices (€29 Standard, €59 VIP) for the Belgium concert on a USD-base store.

This doc exists because it took ~3 hours of wrong turns to figure out. Read the gotchas section first if you're doing anything similar again.

---

## TL;DR

Prices aren't on products/variants anymore. They live in a chain:

```
Market → Catalog → PriceList → fixed prices per variant
```

Our final state:

```
EU market (eu.musicalbasics.com)
└── ACTIVE catalog "EU EUR Catalog"
    └── PriceList "EU EUR Fixed Prices" (EUR, 2 fixed prices)
        ├── Standard variant 43946996957227 → €29.00
        └── VIP variant 43962297974827 → €59.00
```

Landing page checkout URLs hit `eu.musicalbasics.com/cart/<variantId>:<qty>`, which resolves to EU market → EUR fixed prices.

---

## The Architecture (current, API 2025-10+)

Prices are **contextual**. When a customer arrives:

1. Shopify resolves their **Market** (via IP geolocation, URL path, or explicit country selector).
2. The market's **webPresence** determines the domain/subfolder they land on (e.g. `eu.musicalbasics.com`).
3. The market's **ACTIVE catalog** determines which products are visible and which price list applies.
4. The catalog's **PriceList** provides fixed currency overrides. Variants not in the list fall back to FX conversion from base currency.

```
┌─────────────┐       ┌──────────────┐       ┌──────────────────┐
│   Market    │──1:1──│    Catalog   │──1:1──│    PriceList     │
│ (geography, │       │ (visibility, │       │ (currency +      │
│  routing,   │       │  status,     │       │  fixed prices)   │
│  webPres.)  │       │  publication)│       │                  │
└─────────────┘       └──────────────┘       └──────────────────┘
```

Key schema constraints:

- A market can have multiple catalogs but typically one is ACTIVE at a time.
- A PriceList can only attach to **one** catalog (enforced — "Price list has already been taken").
- A Market without `webPresence` has no URL; customers can't reach it through normal browsing.

---

## Gotchas (save yourself hours)

### 1. Dev dashboard custom apps use Client Credentials grant

Shopify killed classic "Develop apps → reveal `shpat_` token once" on **January 1, 2026**. New custom apps are created at `dev.shopify.com/dashboard/...` and only give you a Client ID + Client Secret.

To get an Admin API token, POST to the store's OAuth endpoint:

```bash
curl -X POST "https://{shop}.myshopify.com/admin/oauth/access_token" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "...",
    "client_secret": "...",
    "grant_type": "client_credentials"
  }'
```

Returns `{ access_token: "shpat_...", scope, expires_in: 86399 }`. **Token is short-lived (~24h)** — re-run the exchange per session. See `refreshAccessToken()` in [scripts/shopify/_client.mjs](../scripts/shopify/_client.mjs).

### 2. `PriceListCreateInput.contextRule` is gone in 2025-10

Many public blog posts and ChatGPT answers still tell you to do this:

```graphql
priceListCreate(input: {
  name: "...",
  currency: EUR,
  contextRule: { marketId: "..." }   # ← DOES NOT EXIST in 2025-10
}) { ... }
```

This returns `Field is not defined on PriceListCreateInput`. The correct shape is:

```graphql
priceListCreate(input: {
  name: "...",
  currency: EUR,
  parent: { adjustment: { type: PERCENTAGE_DECREASE, value: 0.0 } },
  catalogId: "..."   # ← optional, attach to existing catalog
})
```

If you don't have a catalog yet, create the price list first (no `catalogId`), then create a catalog with that `priceListId`.

### 3. A PriceList can only attach to ONE Catalog

Trying to point two catalogs at the same price list:

```
"message": "Price list has already been taken", "code": "TAKEN"
```

If you need fixed prices on two markets with the same currency, either duplicate the price list or move the one catalog that references it.

### 4. A Market with `webPresence: null` is unreachable

We originally bound our EUR catalog to the `belgium` market, which has no webPresence. Result:
- Price list and catalog were structurally correct
- But Belgian IPs got routed to the **European Union** market (which includes BE as a region and has `eu.musicalbasics.com`)
- So our €29/€59 prices were set but no customer traffic ever hit them

Check each market's webPresence before binding:

```graphql
{
  markets(first: 50) {
    nodes {
      handle
      webPresence { id rootUrls { url locale } }
    }
  }
}
```

If a market is `webPresence: null`, it shares the primary domain OR is inert. Stores with a broader market that covers the same regions (e.g. "European Union" covering BE) usually win the routing.

### 5. `PriceList.prices` returns ALL effective prices, not just your fixed ones

If your PriceList has `parent.adjustment = PERCENTAGE_DECREASE, value: 0.0`, the `prices` connection returns base USD prices for every variant in the catalog. Your fixed EUR prices are mixed in but may be paginated off-screen.

**Don't verify by paginating `prices`.** Use `fixedPricesCount` instead:

```graphql
{
  priceList(id: "...") {
    fixedPricesCount  # synchronous, accurate
    currency
  }
}
```

### 6. Writes have eventual consistency on reads

Right after `priceListFixedPricesAdd`, an immediate re-read may not show the new price. `fixedPricesCount` DOES update immediately, so rely on that for verification within the same script.

### 7. Shopify normalizes amount strings

You POST `"29.00"`, the response echoes `"29.0"`. Don't do strict string comparison — parse to number or compare semantically.

### 8. API-created products are NOT auto-published to sales channels

This burned us on the livestream product. After `productCreate` returns `status: ACTIVE` and the variant has a price, the product is **still invisible** on every storefront (`musicalbasics.com`, `eu.musicalbasics.com`, etc.) until you explicitly publish it to the **Online Store** publication.

Symptom: cart URL `eu.musicalbasics.com/cart/<variantId>:1` returns Shopify's "Link no longer exists." page even though the variant exists and is `ACTIVE`.

Fix: after `productCreate`, run `publishablePublish`:

```graphql
mutation($id: ID!, $input: [PublicationInput!]!) {
  publishablePublish(id: $id, input: $input) {
    publishable { ... on Product { id title } }
    userErrors { field message }
  }
}
```

with `input: [{ publicationId: <Online Store publication GID> }]`. Find the publication ID via `{ publications(first: 30) { nodes { id name } } }` and pick the one named `"Online Store"`.

Requires scopes: `read_publications` + `write_publications` (these are NOT in the original 6 scopes — adding them needs a new app version on dev.shopify.com plus a clean app reinstall on the store, since managed-installation tokens only carry the scopes consented at install time).

Reusable script: [scripts/shopify/10-publish-product.mjs](../scripts/shopify/10-publish-product.mjs). Run with `node --env-file=.env.local scripts/shopify/10-publish-product.mjs gid://shopify/Product/<id>`.

### 9. Adding scopes to a managed-install app requires a clean reinstall

Just bumping the app version with new scopes on dev.shopify.com is not enough. The store's existing install was authorized for the OLD scope set, and `client_credentials` tokens issued against it will still only carry the old scopes. Symptom: token response only shows the original scopes, and queries that need new scopes return `Access denied`.

Fix: **uninstall the app from the store admin first**, then reinstall from dev.shopify.com. The "Install app" button alone won't trigger re-consent if the app is still installed — Shopify silently uses the existing authorization. After uninstall + reinstall, the next `client_credentials` grant returns a token with the full new scope set.

Also: if "Use legacy install flow" is checked, the install requires an actual OAuth code-exchange handler at the redirect URL. With `https://example.com/auth/callback` as the redirect, the install rolls back silently because example.com can't complete the handshake. **Uncheck "Use legacy install flow"** for managed-install custom apps with no real backend, and reinstall succeeds.

---

## Mutations in order (copy-paste reference)

### Step 1 — Create the EUR price list (no catalog yet)

```graphql
mutation($input: PriceListCreateInput!) {
  priceListCreate(input: $input) {
    priceList { id name currency }
    userErrors { field message code }
  }
}
```

Variables:

```json
{
  "input": {
    "name": "EU EUR Fixed Prices",
    "currency": "EUR",
    "parent": { "adjustment": { "type": "PERCENTAGE_DECREASE", "value": 0.0 } }
  }
}
```

Save the returned `priceList.id` — needed for step 2.

### Step 2 — Create catalog bound to the target market, with the price list

```graphql
mutation($input: CatalogCreateInput!) {
  catalogCreate(input: $input) {
    catalog { id title status }
    userErrors { field message code }
  }
}
```

Variables (bound to EU market):

```json
{
  "input": {
    "title": "EU EUR Catalog",
    "status": "ACTIVE",
    "context": { "marketIds": ["gid://shopify/Market/10924720171"] },
    "priceListId": "gid://shopify/PriceList/<from step 1>"
  }
}
```

### Step 3 — Add fixed prices for specific variants

```graphql
mutation($priceListId: ID!, $prices: [PriceListPriceInput!]!) {
  priceListFixedPricesAdd(priceListId: $priceListId, prices: $prices) {
    prices { variant { id } price { amount currencyCode } }
    userErrors { field message code }
  }
}
```

Variables:

```json
{
  "priceListId": "gid://shopify/PriceList/...",
  "prices": [
    {
      "variantId": "gid://shopify/ProductVariant/43946996957227",
      "price": { "amount": "29.00", "currencyCode": "EUR" }
    },
    {
      "variantId": "gid://shopify/ProductVariant/43962297974827",
      "price": { "amount": "59.00", "currencyCode": "EUR" }
    }
  ]
}
```

Verify via `priceList(id).fixedPricesCount` — should equal the number you just added.

### Step 4 (if needed) — Move an existing catalog between markets

If you bound the catalog to the wrong market (we did: bound to `belgium`, needed `european-union`):

```graphql
mutation($catalogId: ID!, $add: CatalogContextInput, $remove: CatalogContextInput) {
  catalogContextUpdate(catalogId: $catalogId, contextsToAdd: $add, contextsToRemove: $remove) {
    catalog { id title status }
    userErrors { field message code }
  }
}
```

Variables:

```json
{
  "catalogId": "gid://shopify/MarketCatalog/<our catalog id>",
  "add":    { "marketIds": ["gid://shopify/Market/<NEW_MARKET>"] },
  "remove": { "marketIds": ["gid://shopify/Market/<OLD_MARKET>"] }
}
```

### Step 5 (if needed) — Archive the market's pre-existing catalog

If the target market already had a default catalog (ours did — EU market's "European Union" catalog with USD price list), archive it so only your new catalog is ACTIVE:

```graphql
mutation($id: ID!, $input: CatalogUpdateInput!) {
  catalogUpdate(id: $id, input: $input) {
    catalog { id title status }
    userErrors { field message code }
  }
}
```

Variables: `{ "id": "...", "input": { "status": "ARCHIVED" } }`.

**Don't use `catalogDelete`** — CLAUDE.md forbids delete mutations; archiving is safer and reversible.

---

## Scripts in this repo

All run via `node --env-file=.env.local scripts/shopify/<name>.mjs`.

| Script | Purpose |
|---|---|
| `_client.mjs` | GraphQL helper + `refreshAccessToken()` |
| `_introspect.mjs <TypeName>` | Print any schema type's input fields |
| `01-auth-check.mjs` | Smoke test: `shop { name primaryDomain }` |
| `02-backup-catalog.mjs` | Full product JSON snapshot → `/backups/` |
| `03-read-belgium-prices.mjs` | Dump markets/catalogs/price-list state |
| `04-propose-mutations.mjs` | Dry-run print of writes (no execution) |
| `05-apply-belgium-prices.mjs` | Execute the create-price-list + create-catalog + add-prices flow |
| `07-move-price-list-to-eu.mjs` | Rebind catalog from one market to another + archive the old one |

---

## Verification checklist

1. `node --env-file=.env.local scripts/shopify/01-auth-check.mjs` → shop name returns.
2. Query `priceList(id).fixedPricesCount` → matches the number of overrides you set.
3. Query `market(id)` for target market → `catalogs.nodes[]` includes your catalog as `ACTIVE`, with your price list, currency EUR.
4. Open `eu.musicalbasics.com/cart/<variantId>:1` in incognito → cart shows EUR at the fixed price.
5. Verify a non-target market is unchanged (e.g. `musicalbasics.com/cart/<variantId>:1` → still USD).

---

## Checkout URLs in the landing page

See [src/lib/checkout.ts](../src/lib/checkout.ts).

`buildCheckoutUrl()` returns `https://eu.musicalbasics.com/cart/${variantId}:${quantity}?...` — hardcoded to the EU web presence so every landing-page Buy button hits the EU market, regardless of the visitor's IP. Belgian/EU customers get EUR native; US customers also get EUR (charged in EUR on their card) — acceptable for a Belgium-specific concert page.

If you later want IP-based routing (US → USD checkout, EU → EUR checkout), add geolocation in `middleware.ts` and branch the host.

---

## Adding fixed prices for another market (e.g. UK in GBP)

Same recipe:

1. Find the UK market ID from `{ markets(first: 50) { nodes { handle id } } }`.
2. Create a GBP price list (step 1 above, `currency: GBP`).
3. UK market already has a catalog at `uk.musicalbasics.com`. Either:
   - Update the existing UK catalog's `priceListId` to your new GBP list (cleaner), or
   - Create a new UK catalog with your GBP list and archive the old one (same as our EU approach).
4. Add fixed GBP prices per variant (step 3).
5. Landing-page checkout URL for UK visitors → `uk.musicalbasics.com/cart/...`.

---

## Undo

To restore FX-converted pricing for EU:

1. Archive our catalog: `catalogUpdate(id: "<our catalog id>", input: { status: "ARCHIVED" })`
2. Reactivate the old EU catalog: `catalogUpdate(id: "<old EU catalog>", input: { status: "ACTIVE" })`

Belgian/EU customers are back on FX-converted USD. No other market is affected.

---

## Current IDs (as of 2026-04-23, after cleanup)

```
EU market:    gid://shopify/Market/10924720171
Catalog:      gid://shopify/MarketCatalog/159716507691   "EU EUR Catalog" (ACTIVE, on EU)
Price list:   gid://shopify/PriceList/18476171307        "EU EUR Fixed Prices" (EUR, 2 fixed)
Standard:     gid://shopify/ProductVariant/43946996957227 → €29.00
VIP:          gid://shopify/ProductVariant/43962297974827 → €59.00
```

Deleted on 2026-04-23 (kept here for audit trail):
- `gid://shopify/Market/111020867627` — Belgium market (empty, unreachable because no webPresence; removed to avoid confusion)
- `gid://shopify/MarketCatalog/11000840235` — old default EU catalog (USD, ARCHIVED)
- `gid://shopify/PriceList/18473549867` — old default EU price list (USD, 0 fixed — cascade-deleted with its catalog)

IDs don't change unless you delete and recreate.
