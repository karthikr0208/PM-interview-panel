-- 0005_coach_reports.sql — the Coach's three improvements, one row each.
--
-- Idempotent: `create table if not exists` and the drop-then-create policy
-- shape from 0002. Safe to re-run via backend/scripts/migrate.py. Never
-- applied through the Supabase dashboard, or Render cannot recreate it.
--
-- ── WHY THIS EXISTS ────────────────────────────────────────────────────
-- `app/graph/state.py` has carried `coach_report: dict | None` since Phase 0
-- and the schema has never had anywhere to put one. Story 4.3 had the
-- opposite problem and it was the easier one: there the DDL had already
-- decided the output's shape and the work was to read it before designing a
-- second one. Here nothing was decided, which means the shape gets decided by
-- whatever the first insert happens to pass -- so it is decided here, before
-- the agent exists. See PHASE-5-SPEC.md § 1.
--
-- ONE ROW PER IMPROVEMENT, not a JSON blob, for the same reason
-- answer_evaluations is one row per (turn, dimension): a blob cannot be
-- constrained, cannot be queried, and cannot enforce anything.
--
-- ── THE TWO KINDS, AND WHY THE CHECK IS SCOPED ─────────────────────────
-- Karthik's call 2026-08-11: three improvements, always. That is achievable
-- without padding only because improvements are not all one shape.
--
--   moment  "here is what you said, here is a stronger version"
--           quotes the candidate -- FEWER available when coverage is thin
--
--   gap     "you never took a position on the market at all"
--           quotes nothing, because nothing was said -- MORE available when
--           coverage is thin
--
-- A dimension in `not_assessed` is not an absence of coaching material; it is
-- among the most useful things a coach can say. PHASE-4-SPEC § 1 measured a
-- real interview producing two of them.
--
-- 🔴 The naive schema for this is `anchor_quote text not null check (length >
-- 0)`, matching answer_evaluations.evidence_quote, and it CANNOT hold for a
-- gap row -- there is no quote of a thing the candidate never said. The wrong
-- fix is to drop the constraint, which surrenders the table's strongest
-- guarantee for every row including the ones that could honour it. So the
-- check is SCOPED to the kind it applies to. A `moment` still cannot exist
-- without a verbatim quote, enforced in Postgres rather than by convention,
-- which is the same guarantee PRD §8 makes for scores.
--
-- A gap is falsifiable too, just from a different column: its `dimension`
-- must genuinely be absent from that session's answer_evaluations. That is
-- not expressible as a table constraint (it spans rows in another table), so
-- it is asserted in the agent's tests instead -- see PHASE-5-SPEC 5.2. A gap
-- claiming the candidate never addressed something they were scored on is the
-- same fabrication as an invented quote, in the other direction.
create table if not exists coach_reports (
  id               uuid primary key default gen_random_uuid(),
  session_id       uuid not null references sessions on delete cascade,

  -- 0, 1, 2 -- the order the candidate reads them in. Not a score and not a
  -- ranking of severity; the Coach decides the order and it is preserved.
  idx              int  not null check (idx >= 0),

  kind             text not null check (kind in ('moment', 'gap')),

  -- Nullable at the column level, mandatory for a `moment` via the scoped
  -- check below. NEVER normalised on the way in: this is compared to the
  -- transcript byte for byte, and transcript_turns holds the candidate's text
  -- unnormalised. Normalising one side of that comparison turns a faithful
  -- quote into a mismatch -- the rule build.py already follows for
  -- evidence_quote.
  anchor_quote     text,

  -- Set on a `gap`, naming which rubric dimension went unevidenced. Null on a
  -- `moment`, which anchors to a quote instead.
  dimension        text,

  -- Prose the candidate reads. Normalised for em-dashes at the graph
  -- boundary, like answer_evaluations.reasoning -- CLAUDE.md's ban covers
  -- anything a candidate reads.
  stronger_version text not null check (length(stronger_version) > 0),
  drill            text not null check (length(drill) > 0),

  created_at       timestamptz not null default now(),

  -- One improvement per slot per session. Makes a double-write a loud error
  -- rather than a duplicated card.
  unique (session_id, idx),

  -- 🔴 The load-bearing line. A `moment` without a verbatim quote cannot be
  -- written at all.
  constraint coach_reports_moment_needs_a_quote
    check (kind <> 'moment' or (anchor_quote is not null and length(anchor_quote) > 0)),

  -- The mirror: a `gap` names a dimension instead. Without this, a gap row
  -- with neither a quote nor a dimension would satisfy every other constraint
  -- and carry no evidence of any kind.
  constraint coach_reports_gap_needs_a_dimension
    check (kind <> 'gap' or (dimension is not null and length(dimension) > 0))
);

-- Postgres does not index foreign keys automatically, and every read filters
-- by session_id then orders by idx.
create index if not exists coach_reports_session_idx on coach_reports (session_id, idx);

-- ── RLS ───────────────────────────────────────────────────────────────
-- Same shape as 0002's other five scoped tables: join back to sessions,
-- `to authenticated` (anonymous sign-in issues `authenticated`, NOT `anon` --
-- verified live 2026-07-31; a policy written `to anon` is valid and inert).
-- Never `using (true)`.
--
-- Re-run `node frontend/scripts/probe_realtime.mjs` after applying this, per
-- CLAUDE.md's rule for anything touching RLS or the realtime publication.
alter table coach_reports enable row level security;

drop policy if exists "own session coach reports" on coach_reports;
create policy "own session coach reports" on coach_reports
  for select to authenticated
  using (session_id in (
    select id from sessions where user_id = (select auth.uid())
  ));
