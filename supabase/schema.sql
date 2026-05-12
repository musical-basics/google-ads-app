-- Belgium concert ad agent. Minimal schema.
-- All tables live under the `ads` schema so other ad-related tooling can share it.
-- Idempotent. Safe to re-run.

create schema if not exists ads;

-- Schema-level access (must come before table grants stick on existing tables)
grant usage on schema ads to postgres, anon, authenticated, service_role;

create table if not exists ads.belgium_campaign_state (
  id uuid primary key default gen_random_uuid(),
  campaign_id text unique,
  resource_name text,
  ad_group_subscribers_id text,
  ad_group_lookalike_id text,
  status text,
  daily_budget_cents int,
  total_budget_cents int,
  spend_to_date_cents int default 0,
  conversions_to_date numeric default 0,
  revenue_to_date_cents int default 0,
  video_id_landscape text,
  video_id_portrait text,
  created_at timestamptz default now(),
  last_synced_at timestamptz
);

create table if not exists ads.belgium_daily_performance (
  date date,
  campaign_id text,
  ad_group_id text,
  impressions int default 0,
  views int default 0,
  clicks int default 0,
  cost_cents int default 0,
  conversions numeric default 0,
  conversion_value_cents int default 0,
  primary key (date, campaign_id, ad_group_id)
);

create table if not exists ads.belgium_ticket_sales (
  shopify_order_id text primary key,
  order_name text,
  customer_email text,
  ticket_tier text,
  amount_cents int,
  currency text,
  utm_source text,
  utm_medium text,
  utm_campaign text,
  utm_content text,
  utm_term text,
  landing_site text,
  ordered_at timestamptz,
  ad_attributed boolean default false,
  raw jsonb
);

create table if not exists ads.belgium_agent_log (
  id uuid primary key default gen_random_uuid(),
  ran_at timestamptz default now(),
  action text,
  details jsonb,
  success boolean
);

create index if not exists idx_belgium_daily_performance_date on ads.belgium_daily_performance (date);
create index if not exists idx_belgium_ticket_sales_ordered_at on ads.belgium_ticket_sales (ordered_at);
create index if not exists idx_belgium_agent_log_ran_at on ads.belgium_agent_log (ran_at desc);

-- Lock down with RLS. service_role bypasses RLS by design so the server-side
-- code keeps full access. anon and authenticated get nothing because no
-- policies are defined for them.
alter table ads.belgium_campaign_state enable row level security;
alter table ads.belgium_daily_performance enable row level security;
alter table ads.belgium_ticket_sales enable row level security;
alter table ads.belgium_agent_log enable row level security;

-- service_role full access on existing tables + sequences
grant all on all tables in schema ads to service_role;
grant all on all sequences in schema ads to service_role;
grant all on all functions in schema ads to service_role;

-- service_role full access on future tables + sequences (in case more get added)
alter default privileges in schema ads grant all on tables to service_role;
alter default privileges in schema ads grant all on sequences to service_role;
alter default privileges in schema ads grant all on functions to service_role;

-- postgres role keeps ownership-level access (Supabase SQL editor runs as postgres)
grant all on all tables in schema ads to postgres;
grant all on all sequences in schema ads to postgres;
alter default privileges in schema ads grant all on tables to postgres;
alter default privileges in schema ads grant all on sequences to postgres;
