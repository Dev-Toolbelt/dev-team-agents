create table public.entitlement_rate_limits (
  user_id uuid primary key references auth.users (id) on delete cascade,
  window_started_at timestamptz not null default now(),
  issued_count integer not null default 0
);

alter table public.entitlement_rate_limits enable row level security;

revoke all on public.entitlement_rate_limits from anon, authenticated;

create function public.take_entitlement_slot(
  p_user_id uuid,
  p_limit integer,
  p_window_seconds integer
)
returns table (allowed boolean, retry_after integer)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_count integer;
  v_started timestamptz;
begin
  if p_user_id is null or p_limit is null or p_limit < 1
     or p_window_seconds is null or p_window_seconds < 1 then
    raise exception 'take_entitlement_slot: p_user_id, p_limit > 0 and p_window_seconds > 0 are required';
  end if;
  insert into public.entitlement_rate_limits as r (user_id, window_started_at, issued_count)
  values (p_user_id, now(), 1)
  on conflict (user_id) do update
    set window_started_at = case
          when r.window_started_at <= now() - make_interval(secs => p_window_seconds) then now()
          else r.window_started_at
        end,
        issued_count = case
          when r.window_started_at <= now() - make_interval(secs => p_window_seconds) then 1
          else r.issued_count + 1
        end
  returning r.issued_count, r.window_started_at into v_count, v_started;

  allowed := v_count <= p_limit;
  retry_after := greatest(
    1,
    ceil(extract(epoch from (v_started + make_interval(secs => p_window_seconds) - now())))::integer
  );
  return next;
end;
$$;

revoke all on function public.take_entitlement_slot(uuid, integer, integer) from public, anon, authenticated;
grant execute on function public.take_entitlement_slot(uuid, integer, integer) to service_role;
