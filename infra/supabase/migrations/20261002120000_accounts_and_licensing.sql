create table public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  display_name text check (display_name is null or char_length(display_name) between 1 and 80),
  signup_method text not null default 'email',
  last_seen_at date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.licenses (
  user_id uuid primary key references auth.users (id) on delete cascade,
  plan text not null default 'free' check (plan in ('free', 'premium')),
  status text not null default 'active' check (status in ('active', 'banned')),
  features text[] not null default '{}',
  trial_started_at timestamptz,
  banned_at timestamptz,
  ban_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check ((status = 'banned') = (banned_at is not null))
);

create table public.app_config (
  id boolean primary key default true check (id),
  trial_enabled boolean not null default false,
  trial_days integer not null default 5 check (trial_days between 1 and 365),
  max_offline_days integer not null default 7 check (max_offline_days between 1 and 30),
  updated_at timestamptz not null default now()
);

insert into public.app_config (id) values (true);

create table public.banned_identities (
  email_hmac bytea primary key check (octet_length(email_hmac) = 32),
  reason text not null,
  created_at timestamptz not null default now()
);

create table public.trial_consumed (
  email_hmac bytea primary key check (octet_length(email_hmac) = 32),
  trial_started_at timestamptz not null,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null default (now() + interval '12 months')
);

create index trial_consumed_expires_at_idx on public.trial_consumed (expires_at);

create function public.touch_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger profiles_touch_updated_at
  before update on public.profiles
  for each row execute function public.touch_updated_at();

create trigger licenses_touch_updated_at
  before update on public.licenses
  for each row execute function public.touch_updated_at();

create trigger app_config_touch_updated_at
  before update on public.app_config
  for each row execute function public.touch_updated_at();

create function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, display_name, signup_method)
  values (
    new.id,
    nullif(left(btrim(coalesce(new.raw_user_meta_data ->> 'display_name', '')), 80), ''),
    coalesce(new.raw_app_meta_data ->> 'provider', 'email')
  )
  on conflict (id) do nothing;
  insert into public.licenses (user_id) values (new.id) on conflict (user_id) do nothing;
  return new;
end;
$$;

revoke all on function public.handle_new_user() from public, anon, authenticated;
revoke all on function public.touch_updated_at() from public, anon, authenticated;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

alter table public.profiles enable row level security;
alter table public.licenses enable row level security;
alter table public.app_config enable row level security;
alter table public.banned_identities enable row level security;
alter table public.trial_consumed enable row level security;

revoke all on public.profiles, public.licenses, public.app_config,
  public.banned_identities, public.trial_consumed from anon, authenticated;

alter default privileges in schema public revoke all on tables from anon, authenticated;
alter default privileges in schema public revoke all on functions from anon, authenticated;

grant select on public.profiles to authenticated;
grant update (display_name) on public.profiles to authenticated;
grant select (user_id, plan, status, features, trial_started_at, created_at, updated_at)
  on public.licenses to authenticated;

create policy profiles_select_own on public.profiles
  for select to authenticated
  using (id = (select auth.uid()));

create policy profiles_update_own on public.profiles
  for update to authenticated
  using (id = (select auth.uid()))
  with check (id = (select auth.uid()));

create policy licenses_select_own on public.licenses
  for select to authenticated
  using (user_id = (select auth.uid()));

create function public.purge_expired_data(p_batch integer default 5000)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_deleted integer;
begin
  if p_batch is null or p_batch < 1 then
    raise exception 'p_batch must be a positive integer';
  end if;
  delete from public.trial_consumed where expires_at < now();
  if to_regclass('auth.audit_log_entries') is null then
    raise warning 'auth.audit_log_entries not found: the 90-day audit-log purge did nothing';
    return;
  end if;
  loop
    delete from auth.audit_log_entries
    where ctid in (
      select ctid from auth.audit_log_entries
      where created_at < now() - interval '90 days'
      limit p_batch
    );
    get diagnostics v_deleted = row_count;
    exit when v_deleted < p_batch;
  end loop;
end;
$$;

revoke all on function public.purge_expired_data(integer) from public, anon, authenticated, service_role;

do $$
begin
  if exists (select 1 from pg_available_extensions where name = 'pg_cron') then
    begin
      create extension if not exists pg_cron with schema pg_catalog;
      perform cron.schedule('purge-expired-data', '17 3 * * *', 'select public.purge_expired_data()');
    exception when others then
      raise notice 'pg_cron could not be enabled (%): schedule public.purge_expired_data() daily from an external job', sqlerrm;
    end;
  else
    raise notice 'pg_cron unavailable: schedule public.purge_expired_data() daily from an external job';
  end if;
end;
$$;

-- The ban (SR-34, SR-35): one call does every database step, so the runbook cannot skip one.
-- The email HMAC is written by the ban-user Edge Function, the only holder of the pepper.
create function public.ban_user(p_user_id uuid, p_reason text)
returns text
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_email text;
begin
  if p_user_id is null or coalesce(btrim(p_reason), '') = '' then
    raise exception 'ban_user: a user id and a reason are required';
  end if;
  update public.licenses
    set status = 'banned', banned_at = coalesce(banned_at, now()), ban_reason = p_reason
    where user_id = p_user_id;
  -- A far-future timestamp, not 'infinity': GoTrue scans banned_until into a Go time.
  update auth.users set banned_until = '2999-12-31 00:00:00+00' where id = p_user_id
    returning email into v_email;
  delete from auth.sessions where user_id = p_user_id;
  return v_email;
end;
$$;

revoke all on function public.ban_user(uuid, text) from public, anon, authenticated;
grant execute on function public.ban_user(uuid, text) to service_role;
