-- Belgium concert ad agent - minimal schema
-- Run once against the target Supabase project. Idempotent.

create table if not exists belgium_campaign_state (
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

create table if not exists belgium_daily_performance (
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

create table if not exists belgium_ticket_sales (
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

create table if not exists belgium_agent_log (
  id uuid primary key default gen_random_uuid(),
  ran_at timestamptz default now(),
  action text,
  details jsonb,
  success boolean
);

create index if not exists idx_belgium_daily_performance_date on belgium_daily_performance (date);
create index if not exists idx_belgium_ticket_sales_ordered_at on belgium_ticket_sales (ordered_at);
create index if not exists idx_belgium_agent_log_ran_at on belgium_agent_log (ran_at desc);
