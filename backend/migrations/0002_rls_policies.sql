-- 0002_rls_policies.sql — scoped RLS policies for the six app tables.
--
-- Idempotent: Postgres has no "create policy if not exists", so every policy
-- is dropped first, then recreated. Safe to re-run via
-- backend/scripts/migrate.py. Never applied through the Supabase dashboard.
--
-- ── THE FACT THAT SHAPES EVERY POLICY BELOW ─────────────────────────────
-- Supabase anonymous sign-in issues the `authenticated` role, NOT `anon`.
-- Verified live 2026-07-31 (DEV-STATE § Blockers): a freshly minted anonymous
-- session's JWT carries `role: authenticated`. Every policy here therefore
-- targets `to authenticated`. A policy written `to anon` would be syntactically
-- valid and completely inert — the real browser path would stay wide open
-- while a test that only probed the `anon` role went green.
--
-- `anon` and `authenticated` already hold table-level SELECT/INSERT/UPDATE/
-- DELETE grants on all six tables (Supabase's default in `public`). Grants
-- control whether a table is *reachable*; RLS controls which *rows* come
-- back. Phase 0 shipped RLS enabled with zero policies, which denies every
-- row despite the open grants. The policies below are what open the door —
-- scoped, deliberately, to the row's owning session. Never `using (true)`.

-- ── sessions ──────────────────────────────────────────────────────────
-- Scopes directly on its own user_id column — the one place ownership is
-- recorded. Every other table below scopes via a join back to this one.
drop policy if exists "own session select" on sessions;
create policy "own session select" on sessions
  for select to authenticated
  using (user_id = (select auth.uid()));

-- with check, not using: this runs against the ROW BEING INSERTED, so a
-- browser cannot create a session claiming to belong to a different uid.
-- Postgres rejects the insert outright ("new row violates row-level
-- security policy") rather than silently rewriting the value.
drop policy if exists "own session insert" on sessions;
create policy "own session insert" on sessions
  for insert to authenticated
  with check (user_id = (select auth.uid()));

-- ── resumes ───────────────────────────────────────────────────────────
drop policy if exists "own session resumes" on resumes;
create policy "own session resumes" on resumes
  for select to authenticated
  using (session_id in (
    select id from sessions where user_id = (select auth.uid())
  ));

-- ── case_worlds ───────────────────────────────────────────────────────
drop policy if exists "own session case_worlds" on case_worlds;
create policy "own session case_worlds" on case_worlds
  for select to authenticated
  using (session_id in (
    select id from sessions where user_id = (select auth.uid())
  ));

-- ── transcript_turns ──────────────────────────────────────────────────
drop policy if exists "own session transcript_turns" on transcript_turns;
create policy "own session transcript_turns" on transcript_turns
  for select to authenticated
  using (session_id in (
    select id from sessions where user_id = (select auth.uid())
  ));

-- ── answer_evaluations ────────────────────────────────────────────────
drop policy if exists "own session answer_evaluations" on answer_evaluations;
create policy "own session answer_evaluations" on answer_evaluations
  for select to authenticated
  using (session_id in (
    select id from sessions where user_id = (select auth.uid())
  ));

-- ── agent_events ──────────────────────────────────────────────────────
drop policy if exists "own session agent_events" on agent_events;
create policy "own session agent_events" on agent_events
  for select to authenticated
  using (session_id in (
    select id from sessions where user_id = (select auth.uid())
  ));

-- ── Deliberately no other policies ───────────────────────────────────
-- No INSERT/UPDATE/DELETE policies on resumes, case_worlds, transcript_turns,
-- answer_evaluations, or agent_events for `authenticated`. Every write to
-- those five tables happens server-side, through the backend's service-role
-- connection, which bypasses RLS entirely (rolbypassrls = true on the pooler
-- role — see DEV-STATE 2026-07-30). Adding browser write policies here would
-- be attack surface with no product requirement behind it.
--
-- LangGraph's checkpoint% tables get NO policies here, deliberately. They
-- hold the entire interview state — resume text, full transcript, every
-- evaluation — and nothing in a browser should ever read them. They are
-- owned by scripts/init_db.py, not this migration.
