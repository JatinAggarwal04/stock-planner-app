-- Enforce the 12-hour sign-in limit on TradeWise data inside Supabase itself.
-- The browser talks to these tables directly, so this is what stops an old
-- session from reading or writing data even if the frontend check is bypassed.
--
-- Run once in the Supabase dashboard: SQL Editor -> New query -> paste -> Run.
-- Safe to re-run. Existing policies are left in place; these are added on top.

-- True when the caller's session was created (i.e. the user signed in) less than 12 hours ago.
-- SECURITY DEFINER so it can read auth.sessions, which signed-in users can't query directly.
create or replace function public.session_is_fresh()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from auth.sessions s
    where s.id = nullif(auth.jwt() ->> 'session_id', '')::uuid
      and s.user_id = auth.uid()
      and s.created_at > now() - interval '12 hours'
  );
$$;

revoke all on function public.session_is_fresh() from public, anon;
grant execute on function public.session_is_fresh() to authenticated;

do $$
declare
  t text;
begin
  foreach t in array array['watchlists', 'portfolio', 'transactions'] loop
    execute format('alter table public.%I enable row level security', t);

    execute format('drop policy if exists "tradewise_own_rows" on public.%I', t);
    execute format('drop policy if exists "tradewise_fresh_session" on public.%I', t);

    -- Permissive: signed-in users can use their own rows (harmless if you already have an equivalent policy)
    execute format(
      $p$create policy "tradewise_own_rows" on public.%I
         for all to authenticated
         using ((select auth.uid())::text = user_id::text)
         with check ((select auth.uid())::text = user_id::text)$p$,
      t);

    -- Restrictive: ANDed with every other policy, so a broader policy can't bypass it.
    -- Applies to all roles: anonymous callers have no uid and are always refused.
    execute format(
      $p$create policy "tradewise_fresh_session" on public.%I
         as restrictive for all to public
         using ((select auth.uid())::text = user_id::text and (select public.session_is_fresh()))
         with check ((select auth.uid())::text = user_id::text and (select public.session_is_fresh()))$p$,
      t);
  end loop;
end $$;
