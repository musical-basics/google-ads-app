# google-ads-app

API-only Google Ads driver for the Belgium concert on 2026-06-11. Deployed on Vercel.
Lionel's personal AI agent calls these endpoints on a schedule; this service is stateless
except for Supabase storage. No cron jobs run here.

Scope is intentionally one-off - see `shopify-eu-pricing.md` and the original build spec
for context. Do not generalize into a multi-product ad system.

## Stack

- Next.js 15 app router (read-only dashboard at `/`)
- Python 3.12 serverless functions in `api/*.py` (Vercel Python runtime)
- Supabase for state (4 tables in `supabase/schema.sql`)
- Resend for daily-summary email
- Shopify Admin GraphQL via the new `client_credentials` flow (see `shopify-eu-pricing.md`)

## Endpoints

All require `Authorization: Bearer $API_KEY`.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/prereqs/check` | Verify env / token / audience / video readiness. Returns `{ok, blockers[], info}`. |
| `POST` | `/api/campaign/create` | Create campaign in PAUSED state. Idempotent. Body: `{daily_budget_cents, total_budget_cents, video_id_landscape?, audience_*_id?, dry_run?}`. |
| `GET` | `/api/campaign/status` | Live status from Google Ads + Supabase snapshot. |
| `POST` | `/api/campaign/pause` | Body: `{reason}`. |
| `POST` | `/api/campaign/resume` | Body: `{reason?}`. |
| `POST` | `/api/sync/google_ads` | Body: `{since?: "YYYY-MM-DD"}`. Pulls per-ad-group performance + rolls up totals. |
| `POST` | `/api/sync/shopify` | Body: `{since?: "YYYY-MM-DD"}`. Pulls orders, parses UTMs, marks ad-attributed. |
| `POST` | `/api/guardrails/check` | Body: `{enforce?: bool}`. Evaluates hard + soft rules. If enforce=true and a hard rule fires, pauses. |
| `GET` | `/api/summary/daily?date=YYYY-MM-DD&format=json\|text` | Plain-text summary block. |
| `POST` | `/api/notify/daily_summary` | Body: `{date?, to?}`. Renders + emails via Resend. |

## Setup

### 1. Supabase

Run `supabase/schema.sql` in the Supabase SQL editor. Idempotent - safe to re-run.

### 2. Google Ads OAuth (one-time, local)

```bash
pip install google-auth-oauthlib
export GOOGLE_ADS_CLIENT_ID=...
export GOOGLE_ADS_CLIENT_SECRET=...
python3 scripts/get_refresh_token.py
```

Paste the printed refresh token into Vercel env as `GOOGLE_ADS_REFRESH_TOKEN`.

The developer token is set as a placeholder (`PENDING_APPROVAL_2026_05_12`) until Google
approves the Basic-access application. Every endpoint that calls Google Ads will return 503
with a clear blocker reason until you swap in the real token.

### 3. Shopify

The new `client_credentials` flow requires `SHOPIFY_CLIENT_ID` + `SHOPIFY_CLIENT_SECRET`
on a custom app created at `dev.shopify.com`. Token is exchanged at runtime - no long-lived
`shpat_` token is stored. See `shopify-eu-pricing.md` gotcha #9 for scope-change reinstall
behavior.

Scopes needed: `read_orders`.

### 4. Vercel env vars

Copy `.env.example` to Vercel project settings. Generate `API_KEY` with
`openssl rand -base64 32`. Set `NOTIFY_EMAIL_FROM` to an address on a Resend-verified domain.

### 5. Audiences (manual one-time setup in Google Ads UI or via API)

The campaign refuses to launch with zero audiences attached. Create at least one of:

- **Subscribers** (data segment of Musical Basics channel subscribers - requires the
  YouTube channel linked to your Google Ads account)
- **Lookalike** (similar audiences based on subscribers)
- **Custom intent** (people searching "classical piano concert", "Rachmaninoff live", etc.)

Capture the user-list IDs and store as `AUDIENCE_*_ID` env vars.

### 6. YouTube channel linking

YouTube Studio → Settings → Channel → Advanced → "Link a Google Ads account".
Without this link, subscriber/viewer audiences will not be available.

## Agent integration

The expected call pattern from Lionel's personal AI agent:

- **Every 4 hours**: `POST /api/sync/google_ads` then `POST /api/guardrails/check {enforce: true}`
- **Daily 06:00 ET**: `POST /api/sync/google_ads` (full prior day) + `POST /api/sync/shopify`
- **Daily 07:00 ET**: `POST /api/notify/daily_summary`
- **2026-06-10 23:59 Brussels**: `POST /api/campaign/pause {reason: "end of campaign"}`
- **Pre-launch**: `GET /api/prereqs/check`; refuse to call `POST /api/campaign/create` while
  blockers exist

## Local dev

```bash
npm install
npm run dev      # Next.js frontend at http://localhost:3000
vercel dev       # full stack including Python functions
```

## Deploy

Push to `main` - Vercel auto-deploys. The Python functions are detected by the file layout
under `api/`; the `vercel.json` pins `python3.12` and a 60s `maxDuration`.

## Style

- No em-dashes anywhere
- Direct API calls, no abstraction layers beyond the `google-ads` client
- Errors logged to `belgium_agent_log` with full traceback, never silently swallowed
- This codebase is throwaway. Do not pre-optimize for the future multi-product ads system.
