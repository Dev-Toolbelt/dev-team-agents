-- SR-31, SR-32: row-level security and grants, exercised as the roles a client really has.
-- Run with `supabase test db` against a local stack (CI job `supabase-db`).
begin;
create extension if not exists pgtap with schema extensions;
select plan(16);

insert into auth.users (id, email, raw_user_meta_data, raw_app_meta_data, aud, role)
values
  ('11111111-1111-1111-1111-111111111111', 'one@example.com', '{"display_name":"One"}', '{"provider":"email"}', 'authenticated', 'authenticated'),
  ('22222222-2222-2222-2222-222222222222', 'two@example.com', '{}', '{"provider":"github"}', 'authenticated', 'authenticated');

select is((select count(*)::int from public.profiles), 2, 'the signup trigger creates a profile per user');
select is((select count(*)::int from public.licenses), 2, 'the signup trigger creates a license per user');

set local role authenticated;
select set_config('request.jwt.claims', '{"sub":"11111111-1111-1111-1111-111111111111","role":"authenticated"}', true);

select is((select count(*)::int from public.profiles), 1, 'a user reads only their own profile');
select is((select id::text from public.profiles), '11111111-1111-1111-1111-111111111111', 'and it is theirs');
select is((select count(*)::int from public.licenses), 1, 'a user reads only their own license');
select lives_ok($$ select user_id, plan, status, features, trial_started_at from public.licenses $$, 'the license columns a client needs are readable');
select throws_ok($$ select ban_reason from public.licenses $$, '42501', null, 'ban_reason is not readable by a client');
select throws_ok($$ select banned_at from public.licenses $$, '42501', null, 'banned_at is not readable by a client');

update public.profiles set display_name = 'Renamed' where id = '22222222-2222-2222-2222-222222222222';
select lives_ok($$ update public.profiles set display_name = 'Mine' $$, 'a user may rename themselves');
select throws_ok($$ update public.profiles set signup_method = 'x' $$, '42501', null, 'display_name is the only writable column');
select throws_ok($$ update public.licenses set plan = 'premium' $$, '42501', null, 'a client cannot write its license');
select throws_ok($$ select * from public.app_config $$, '42501', null, 'app_config is not readable by a client');
select throws_ok($$ select * from public.banned_identities $$, '42501', null, 'the ban list is not readable by a client');
select throws_ok($$ select * from public.trial_consumed $$, '42501', null, 'the trial markers are not readable by a client');
select throws_ok($$ select public.take_entitlement_slot('11111111-1111-1111-1111-111111111111', 1, 60) $$, '42501', null, 'the rate limiter is service-role only');

reset role;
select is(
  (select display_name from public.profiles where id = '22222222-2222-2222-2222-222222222222'),
  null,
  'the other user''s profile was not renamed'
);

select * from finish();
rollback;
