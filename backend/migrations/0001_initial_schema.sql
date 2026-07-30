-- 0001_initial_schema.sql — the six application tables, per ARCHITECTURE.md §5.
--
-- Idempotent: safe to re-run. Applied with backend/scripts/migrate.py over the
-- SESSION pooler on port 5432. Never the transaction pooler on 6543.
--
-- LangGraph's own checkpoints / checkpoint_writes / checkpoint_blobs tables are
-- NOT created here. They are created by checkpointer.setup() via
-- scripts/init_db.py in story 0.5, and must not be hand-written — their shape
-- belongs to LangGraph and changes with its version.

-- ── sessions ──────────────────────────────────────────────────────────
-- user_id is nullable because V1 requires no signup. Phase 1 fills it from
-- Supabase anonymous sign-in, which is what makes the RLS policies at the
-- bottom of this file possible. See DEV-STATE 2026-07-30.
create table if not exists sessions (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid null references auth.users,
  status      text not null default 'created',
  level       text,
  created_at  timestamptz not null default now()
);

-- ── resumes ───────────────────────────────────────────────────────────
create table if not exists resumes (
  id           uuid primary key default gen_random_uuid(),
  session_id   uuid not null references sessions on delete cascade,
  storage_path text not null,
  parsed_text  text,
  profile      jsonb
);

-- ── case_worlds ───────────────────────────────────────────────────────
-- Immutable after the Case Architect writes it. Nothing enforces that in the
-- database; it is a graph-level invariant (ARCHITECTURE.md §4). This row is
-- the audit copy — the working copy lives in graph state.
create table if not exists case_worlds (
  id         uuid primary key default gen_random_uuid(),
  session_id uuid not null references sessions on delete cascade,
  world      jsonb not null
);

-- ── transcript_turns ──────────────────────────────────────────────────
-- unique (session_id, idx) is what makes a replayed turn a conflict rather
-- than a duplicate. LangGraph re-runs a node from the top on resume, so an
-- append that is not keyed by idx would silently double the transcript.
create table if not exists transcript_turns (
  id         uuid primary key default gen_random_uuid(),
  session_id uuid not null references sessions on delete cascade,
  idx        int  not null,
  role       text not null,                       -- interviewer | candidate | system
  kind       text not null,                       -- question | followup | answer | clarify | meta
  content    text not null,
  created_at timestamptz not null default now(),
  unique (session_id, idx)
);

-- ── answer_evaluations ────────────────────────────────────────────────
-- The length(evidence_quote) > 0 check enforces the PRD guarantee that no
-- score ships without evidence, at the database rather than in prompt text.
-- An agent that stops quoting fails loudly here instead of producing a
-- confident scorecard with nothing behind it.
--
-- turn_idx references transcript_turns.idx, which is how a score in the
-- scorecard links back to the exact turn it was drawn from.
create table if not exists answer_evaluations (
  id             uuid primary key default gen_random_uuid(),
  session_id     uuid not null references sessions on delete cascade,
  turn_idx       int  not null,
  dimension      text not null,
  score          int  not null check (score between 1 and 4),
  evidence_quote text not null check (length(evidence_quote) > 0)
);

-- ── agent_events ──────────────────────────────────────────────────────
-- Powers the orchestration column and doubles as the debugging audit log.
-- summary is human-readable; never raw JSON (ARCHITECTURE.md §5).
create table if not exists agent_events (
  id          uuid primary key default gen_random_uuid(),
  session_id  uuid not null references sessions on delete cascade,
  agent       text not null,
  status      text not null,                      -- started | done | error
  summary     text,
  duration_ms int,
  tokens      int,
  created_at  timestamptz not null default now()
);

-- ── Indexes ───────────────────────────────────────────────────────────
-- Postgres does not index foreign keys automatically. Every read in this
-- application filters by session_id, and the realtime tables are additionally
-- read in insertion order.
create index if not exists resumes_session_id_idx            on resumes (session_id);
create index if not exists case_worlds_session_id_idx        on case_worlds (session_id);
create index if not exists transcript_turns_session_idx      on transcript_turns (session_id, idx);
create index if not exists answer_evaluations_session_id_idx on answer_evaluations (session_id);
create index if not exists agent_events_session_created_idx  on agent_events (session_id, created_at);

-- ── Row Level Security ────────────────────────────────────────────────
-- Enabled on every table. `public` is exposed through the Data API, so a
-- table without RLS here is a table readable by anyone holding the
-- publishable key — and that key ships inside the browser bundle by design.
--
-- DELIBERATELY NO POLICIES IN PHASE 0.
-- RLS with zero policies denies every role except those that bypass it
-- (service_role, postgres). The backend uses the service key, so it is
-- unaffected; browsers can reach nothing. That is the correct posture while
-- the frontend is still a Vite placeholder.
--
-- Phase 1 adds Supabase anonymous sign-in, which gives each candidate a real
-- auth.uid(), and only then can policies scope rows to their owner:
--
--   create policy "own session" on transcript_turns
--     for select to authenticated
--     using (session_id in (
--       select id from sessions where user_id = (select auth.uid())
--     ));
--
-- Writing `using (true)` instead would expose every candidate's transcript to
-- anyone who opens devtools. See DEV-STATE 2026-07-30 for the decision.
alter table sessions           enable row level security;
alter table resumes            enable row level security;
alter table case_worlds        enable row level security;
alter table transcript_turns   enable row level security;
alter table answer_evaluations enable row level security;
alter table agent_events       enable row level security;

-- ── Realtime ──────────────────────────────────────────────────────────
-- The three tables the three-column UI subscribes to. Without membership here
-- the middle column stays permanently empty, which reads as an agent bug
-- rather than a missing publication.
--
-- Publication membership is not idempotent in Postgres — adding a table twice
-- errors — so each add is guarded against pg_publication_tables.
do $$
declare t text;
begin
  foreach t in array array['transcript_turns', 'answer_evaluations', 'agent_events'] loop
    if not exists (
      select 1 from pg_publication_tables
      where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = t
    ) then
      execute format('alter publication supabase_realtime add table public.%I', t);
    end if;
  end loop;
end $$;

-- ── Storage ───────────────────────────────────────────────────────────
-- Private. Resumes are personal data; the backend mints signed URLs with the
-- service key rather than serving them publicly.
insert into storage.buckets (id, name, public)
values ('resumes', 'resumes', false)
on conflict (id) do nothing;
