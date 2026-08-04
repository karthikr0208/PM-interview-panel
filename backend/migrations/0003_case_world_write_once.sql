-- 0003_case_world_write_once.sql — make `case_world` immutability enforceable.
--
-- Idempotent: `create unique index if not exists` is safe to re-run via
-- backend/scripts/migrate.py. Never applied through the Supabase dashboard.
--
-- ── WHY THIS EXISTS ────────────────────────────────────────────────────
-- 0001_initial_schema.sql says of case_worlds, in its own words:
--
--   "Immutable after the Case Architect writes it. Nothing enforces that in
--    the database; it is a graph-level invariant (ARCHITECTURE.md §4)."
--
-- That was honest and it was the problem. ARCHITECTURE §2 calls `case_world`
-- the load-bearing artifact of the product -- it is what stops the Interviewer
-- contradicting itself forty minutes in -- and PHASE-2-SPEC §2.3 requires the
-- write-once rule to be FALSIFIABLE, not asserted by comment. On 2026-08-04 it
-- was neither: no constraint, no state guard, no test. A second insert would
-- simply have succeeded and left two worlds for one session, with whichever
-- row a later `select` happened to return winning.
--
-- This follows the precedent already set two tables down in 0001, for exactly
-- the same reason:
--
--   "unique (session_id, idx) is what makes a replayed turn a conflict rather
--    than a duplicate. LangGraph re-runs a node from the top on resume, so an
--    append that is not keyed by idx would silently double the transcript."
--
-- The same hazard applies here. A `generate_case_world` node that re-runs must
-- fail loudly rather than quietly write a second, DIFFERENT world -- these are
-- generative agents, so the second row would not even match the first, and the
-- audit copy would disagree with the working copy in graph state.
--
-- One session has exactly one case world, so uniqueness on session_id is the
-- semantic constraint, not a trick to make a test pass.
--
-- Safe to apply: `case_worlds` was empty (0 rows, 0 duplicate sessions,
-- measured 2026-08-04) when this was written.

create unique index if not exists case_worlds_session_id_key
  on case_worlds (session_id);

-- The non-unique index from 0001 is now redundant: the unique index above
-- covers the same column and serves the same lookups. Two indexes on one
-- column is write cost for nothing.
drop index if exists case_worlds_session_id_idx;
