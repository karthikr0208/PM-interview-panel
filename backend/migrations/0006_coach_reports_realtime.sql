-- 0006_coach_reports_realtime.sql — put coach_reports in the Realtime
-- publication.
--
-- Idempotent by the same guard 0001 uses: publication membership is NOT
-- idempotent in Postgres (adding a table twice errors), so the add is guarded
-- against pg_publication_tables. Safe to re-run via backend/scripts/migrate.py.
-- Never applied through the Supabase dashboard.
--
-- ── WHY THIS IS SEPARATE FROM 0005 ─────────────────────────────────────
-- 0005 created the table and gave it an RLS policy, which is what CLAUDE.md's
-- checklist names. It did NOT add it to the publication, and RLS membership
-- and publication membership are genuinely different things: the policy
-- decides which rows a subscriber may see, the publication decides whether
-- any change is broadcast at all. A table with a correct policy and no
-- publication row is silently read-only-on-load.
--
-- Caught on 2026-08-11 by querying pg_publication_tables on the LIVE database
-- rather than by reading the migrations -- 0005 looked complete on its face.
--
-- ── WHY IT MATTERS MORE HERE THAN FOR THE OTHER THREE ──────────────────
-- 0001's three tables are written repeatedly across an interview, so a
-- subscriber that missed the publication would still fill in on the next
-- render or the next mount. `coach_reports` is written ONCE, in the last node
-- of the graph, after the candidate has stopped interacting. The evaluation
-- column is already mounted and idle by then, so with no broadcast the
-- coaching notes never arrive at all and the candidate is looking at an empty
-- panel that says their notes will appear when the interview ends -- which it
-- already has. A manual refresh would be the only way to see them.
do $$
declare t text;
begin
  foreach t in array array['coach_reports'] loop
    if not exists (
      select 1 from pg_publication_tables
      where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = t
    ) then
      execute format('alter publication supabase_realtime add table public.%I', t);
    end if;
  end loop;
end $$;
