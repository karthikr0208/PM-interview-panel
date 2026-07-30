# Development State

**Last updated:** 2026-07-30 · Session 2

---

## Now

**Phase 0 — Walking skeleton.** Stories 0.1 through 0.6 complete and verified. Running FastAPI
backend, Vite frontend, full venv, secret-blocking pre-commit hook, ten tables live in Supabase
(six app + four LangGraph), a working Postgres checkpointer, a two-node graph that pauses on
`interrupt()` and resumes from a checkpoint, and 46 tests. The structured-output decision gate is
resolved: **validate-retry is mandatory and enforced in the LLM wrapper.** The interrupt-resume
constraint the entire conduct loop rests on is proven, and proven by a test shown to fail against
a violating graph.

Next is **story 0.7, interrupt/resume across two separate HTTP requests** — same property as 0.6
but with the API process restarted in between, which is the part that cannot be faked by process
memory. Then 0.8 (deploy).

**Carried into Phase 1, do not lose:** Supabase **anonymous sign-in must be wired before the
frontend reads any data.** Phase 0 ships RLS with zero policies, so browsers currently get
nothing — correct now, but it means the three-column UI will show an empty middle column until
sign-in plus scoped policies exist. See Decisions 2026-07-30.

---

## Phase status

| Phase | Status | Spec | Verified |
|---|---|---|---|
| Planning docs | ✅ complete | — | 2026-07-29 — PRD, ARCHITECTURE, CLAUDE.md, research all written |
| 0 Walking skeleton | 🟡 in progress | PHASE-0-SPEC.md | 2026-07-30 — 0.1 verified, output below |
| 1 Resume Analyst + design foundation | ⬜ not started | — | — |
| 2 Case Architect + Planner | ⬜ not started | — | — |
| 3 Interviewer + conduct loop | ⬜ not started | — | — |
| 4 Evaluator + scorecard | ⬜ not started | — | — |
| 5 Coach | ⬜ not started | — | — |
| 6 Orchestration depth | ⬜ not started | — | — |
| 7 Polish & hardening | ⬜ not started | — | — |

## Agent specs & golden cases

Specs are written at the top of the phase that builds each agent, not up front.

| Agent | Spec | Golden cases | Last prompt change |
|---|---|---|---|
| Resume Analyst | ⬜ (Phase 1) | — | — |
| Case Architect | ⬜ (Phase 2) | — | — |
| Planner | ⬜ (Phase 2) | — | — |
| Interviewer | ⬜ (Phase 3) | — | — |
| Evaluator | ⬜ (Phase 4) | — | — |
| Coach | ⬜ (Phase 5) | — | — |

---

## Current phase — story detail

Phase 0 stories are defined in `docs/specs/PHASE-0-SPEC.md`.

- [x] 0.1 ~~Repo scaffold, `.env` handling, `requirements.txt`, Vite app, secret-prefix pre-commit hook~~ — done 2026-07-30, all four acceptance boxes verified with output below
- [x] 0.2 ~~NVIDIA smoke test~~ — done 2026-07-30. Gate resolved: **not 10/10** (`deep` 7-9/10), so validate-retry is mandatory. Streaming, rate-limit logging, and the off-peak re-measure all done
- [x] 0.3 ~~Confirm build.nvidia.com account model~~ — done 2026-07-29: 40 RPM, no credits
- [x] 0.4a ~~Supabase project + connection verified~~ — done: Singapore, session pooler, Postgres 17.6, `check_db.py` connects
- [x] 0.4 ~~Supabase project + schema migration~~ — done 2026-07-30. Six tables, RLS on all, realtime publication, private `resumes` bucket, constraints proven by failed inserts
- [x] 0.5 ~~Postgres checkpointer wired via session pooler, `.setup()` run once~~ — done 2026-07-30. Idempotent, no collision, 6543 failure reproduced, **RLS added to LangGraph's tables**
- [x] 0.6 ~~Two-node graph with `interrupt()` / `Command(resume=...)`~~ — done 2026-07-30. All five boxes, and **the idempotency assertion was falsified against a deliberately wrong graph before being trusted**
- [ ] 0.7 Interrupt/resume proven across two separate HTTP requests   ← NEXT
- [ ] 0.8 Deploy backend to Render, frontend to Netlify, CORS wired, health check green

---

## Last session

**Session 2 — 2026-07-30. Stories 0.1, 0.2, 0.4, 0.5 complete.** Phase 0 went from nothing on
disk to a running backend, a Vite frontend, ten tables live in Supabase, a working Postgres
checkpointer, and 40 tests. Seven commits, all local — **no git remote is configured and nothing
has been pushed.**

Orchestrated: scaffolds and test files were built by delegated agents, and **every claim was
re-verified independently before being recorded here.** That mattered — it caught a false pass
in my own verification, a regression one agent introduced into another's tests, and two security
holes.

```
a52fc9c  0.1 repo scaffold, backend, frontend, secret hook
89d21fc  docs: close handoff gaps found auditing 0.1
79ef3cf  docs: per-story and per-phase update checklist
6ba182b  docs: close the session workflow loop, fix stale model in header
878c961  0.2 structured-output gate resolved, retry mandatory
f839f35  0.4 schema migration, RLS, realtime, resumes bucket
b65e097  0.5 checkpointer, plus RLS on LangGraph's own tables
```

### 0.6 interrupt / resume — observed output

`backend/app/graph/skeleton.py` (its own module, not `build.py`, so Phase 1 deletes it whole) and
`backend/tests/test_interrupt.py`.

```
tests/test_interrupt.py  6 passed in 17.96s
  test_graph_compiles_with_the_postgres_checkpointer
  test_ainvoke_runs_to_the_interrupt_and_returns_its_payload
  test_command_resume_makes_interrupt_return_the_passed_value
  test_get_state_next_is_the_paused_node
  test_checkpoint_rows_land_after_each_node
  test_llm_call_fires_exactly_once_across_interrupt_and_resume

full live suite:  46 passed in 319.60s (0:05:19)
offline suite  :  21 passed in 4.20s
```

The `conn` / `checkpointer` / `thread_ids` fixtures moved from `test_checkpointer.py` into
`tests/conftest.py`, which now also owns the Windows event-loop policy swap — conftest imports
before any test module, so the swap is guaranteed to precede psycopg. Moved rather than copied
because story 0.6 is the second caller, per CLAUDE.md § Style.

### 0.5 checkpointer — observed output

```
init_db.py, run twice:
  checkpoint_blobs         rls=True      checkpoint_writes        rls=True
  checkpoint_migrations    rls=True      checkpoints              rls=True

graph ran under RLS    : {'n': 42}
state reloaded from PG : {'n': 42}
checkpoint rows written: 3
  service role  : 3        anon : 0        authenticated : 0

full live suite:  19 passed in 426.55s (0:07:06)
offline suite  :  21 passed in 2.36s
```

**Two security holes found and fixed this session**, both the same shape — a table in `public`
reachable by `anon` because Supabase grants there by default. One in our own migration (fixed by
shipping zero policies), one in LangGraph's checkpoint tables (fixed in `init_db.py`).
**Checkpoints were the worse of the two: they hold the entire interview state.**

### 0.1 acceptance — observed output

`make dev-api` → `GET /health`:

```
HTTP/1.1 200 OK
server: uvicorn
content-type: application/json

{"status":"ok"}
```

`make dev-web` → Vite v8.1.5 ready in 347ms on `http://localhost:5173/`, confirmed serving real
HTML with the HMR client injected, not merely printing "ready".

`config.py` failure modes, each run in a subprocess so `backend/.env` was never edited:

```
two vars missing            exit=1
  ConfigError: Missing required environment variable(s): NVIDIA_MODEL_DEEP, SUPABASE_ANON_KEY.

transaction pooler (6543)   exit=1
  ConfigError: SUPABASE_DB_URL uses port 6543 (the transaction pooler). This breaks LangGraph's
  checkpointer with DuplicatePreparedStatement once connections are reused.

direct connection host      exit=1
  ConfigError: SUPABASE_DB_URL host 'db.someref.supabase.co' is not a Supabase pooler host.
```

`.env.example` and `backend/.env` both cover all 11 vars in `REQUIRED_VARS`.

Pre-commit hook, five cases: fake `nvapi-` blocked · fake `sb_secret_` blocked · real-shaped key
blocked · **live `backend/.env` blocked even when force-added past gitignore** · docs naming the
bare prefixes commit fine.

### 0.2 test suite — observed output

`make test-api` equivalent, live tests included. 5m35s, dominated by the 20 structured calls.

```
tests/test_llm.py::test_completion_returns_text PASSED
tests/test_llm.py::test_streaming_yields_multiple_chunks PASSED
tests/test_llm.py::test_structured_output_raw_pass_rate[fast]
  fast (nemotron-3-nano-30b-a3b) raw structured output: 10/10  median 7.2s  failures=none
PASSED
tests/test_llm.py::test_structured_output_raw_pass_rate[deep]
  deep (nemotron-3-super-120b-a12b) raw structured output: 9/10  median 9.2s
  failures=['#10 returned NoneType']
PASSED
tests/test_llm.py::test_retry_wrapper_converges PASSED
tests/test_llm.py::test_every_call_is_logged_with_a_timestamp PASSED
tests/test_llm.py::test_structured_calls_are_logged_too PASSED

7 passed, 13 deselected in 335.27s (0:05:35)
```

Non-live suite, `-m "not live"` — 21 tests, 0.6s:

```
tests/test_config.py .............   13 passed  (parametrized over all 11 REQUIRED_VARS)
tests/test_llm_retry.py ........      8 passed
```

`test_llm_retry.py` is deterministic and hits no network. It exists because
`test_retry_wrapper_converges` only exercises the retry branch when the first attempt happens to
fail — on `fast` that is almost never, so without these the retry logic was effectively untested.
It covers: `None` then valid · `None` twice raises · success does not retry · the instruction is
appended to both string and message-list inputs · **transport errors are re-raised, not
retried** · both attempts are logged.

### 0.4 schema — observed output

Applied with `python backend/scripts/migrate.py`, then re-run to prove idempotency (`ok` both
times). Migration is `backend/migrations/0001_initial_schema.sql`, checked in.

```
tables + RLS:
   agent_events         rls=True      sessions           rls=True
   answer_evaluations   rls=True      transcript_turns   rls=True
   case_worlds          rls=True      resumes            rls=True
   -> all six present: True   missing=None  extra=None

policies:          0  (deliberate — see Decisions)
realtime members:  ['agent_events', 'answer_evaluations', 'transcript_turns']
storage buckets:   [('resumes', False)]        <- private

as service role : 1 row(s) visible
as anon         : 0 row(s) visible
as authenticated: 0 row(s) visible

  empty evidence_quote         rejected: CheckViolation
  score out of range 1-4       rejected: CheckViolation
  duplicate (session_id,idx)   rejected: UniqueViolation

cascade delete  : 0 transcript rows remain after deleting the session
```

The empty-`evidence_quote` rejection is the PRD's "no score without evidence" guarantee enforced
in the database rather than in prompt text. An agent that stops quoting fails loudly here instead
of producing a confident scorecard with nothing behind it.

### Off-peak latency re-measure — model choice holds

Taken 2026-07-30 ~07:30 IST, against the single ~23:00 window everything previously rested on.

| Model | chat latency | structured output |
|---|---|---|
| `nemotron-3-nano-30b-a3b` | 0.4s | VALID |
| `nemotron-3-super-120b-a12b` | 0.4s | VALID |
| `openai/gpt-oss-20b` (backup) | 1.0s | VALID |
| `openai/gpt-oss-120b` | 45s timeout | — |
| `mistral-medium-3.5-128b` | 19.8s | — |
| `google/gemma-4-31b-it` | 26.4s | — |

`nemotron-3-ultra-550b-a55b` now answers in 1.3s and returns valid structured output; it was
`503 ResourceExhausted` on 2026-07-29. Availability moves. Not switching to it — nothing needs it.

### Session 1 — 2026-07-29

Planning, credentials, and de-risking. No application code yet.

Wrote PRD, ARCHITECTURE, CLAUDE.md, PHASE-0-SPEC. Three research agents ran; findings in
`docs/research/`. Installed 13 design skills plus Supabase's two.

Credentials all verified working, not merely present: Supabase recreated in Singapore
(`tnqfqsocoqythakwybsw`) after the first project turned out to be in Sydney, connection proven
against the session pooler, both API keys authenticating.

**The session's significant finding: GLM 5.2 queues ~230s on the free tier and is out.**
Replaced with `nemotron-3-nano-30b-a3b` (fast) and `nemotron-3-super-120b-a12b` (deep), both
3/3 strict structured output at 2–4s. See § Decisions.

Probe scripts kept in `backend/scripts/`: `check_env.py`, `check_db.py`, `probe_latency.py`,
`probe_models.py`, `probe_candidates.py`, `probe_structured.py`.

## Next session — start here

**Start with these two commands (~3 min), then read PHASE-0-SPEC story 0.7.**

```
python backend/scripts/check_env.py                        # nothing rotated overnight
cd backend && .venv/Scripts/python.exe -m pytest tests -q -m "not live"   # expect 21 passed
```

Everything is installed, the database is live, and the skeleton graph pauses and resumes
correctly. Remote is `https://github.com/karthikr0208/PM-interview-panel` (added 2026-07-30).

**Story 0.7 — interrupt/resume across two separate HTTP requests.** Acceptance is in
PHASE-0-SPEC.md. Build `POST /skeleton/start` and `POST /skeleton/resume` in `app/main.py` on top
of `app.graph.skeleton.build_skeleton_graph`, which is done and tested.

**The real test is the process restart between the two calls**, not that the two endpoints work.
An in-memory anything passes the happy path and fails this. `tests/test_api.py` must tear the app
object down and rebuild it between start and resume.

**You will hit the Windows event loop problem here** — uvicorn selects the proactor loop on
Windows unless told otherwise, and psycopg's async mode refuses it. `tests/conftest.py` already
does the swap for tests; `app/main.py` needs its own guarded swap for `make dev-api`.

**The checkpointer needs a lifespan, not a per-request connection.** `AsyncPostgresSaver.
from_conn_string` is an async context manager; opening one per request would open a pooler
connection per request. Open it in FastAPI's `lifespan` and hold it on `app.state`.

**CORS test: assert on preflight `OPTIONS`, never on a simple `GET` returning non-200.** A
disallowed simple GET returns 200 with the header absent. See Decisions 2026-07-30 — the wrong
assertion here encodes a false pass.

**Then 0.8.** It must re-measure checkpoint latency from the deployed Render service; the 298ms
measured locally is dev-machine-to-Singapore and says nothing about production. Render region
must be **Singapore**.

**Run first (~3 min):** `python backend/scripts/check_env.py`. It now checks all three models and
no longer probes `thinking`.

**Live tests cost about 5m35s and real rate budget.** Use `-m "not live"` (21 tests, 0.6s) while
iterating; run the full suite before handing anything over.

**Before touching agent code, remember the venv:** `backend/.venv/Scripts/python.exe`, or use the
`make` targets. The global interpreter has different versions of fastapi, pydantic, and openai
and does not have langgraph at all.

**On retesting GLM 5.2 — the bar, so it is not re-litigated each session.**
Retest opportunistically. **Correction 2026-07-30: `probe_candidates.py` does *not* test GLM** —
verified by grep; GLM appears only in `probe_models.py` and `probe_nvidia.py`. The retest policy
below therefore had nothing implementing it. Use `probe_models.py`, or add GLM to
`probe_candidates.py`'s model list.

But treat one fast sample as one sample, not as a reversal. The product runs interviews at
unpredictable hours, so a model that is 3s at 09:00 and 230s at 23:00 is unshippable — the
23:00 session is a broken product.

Switch back **only if** GLM is fast across several checks spread through a full day **and**
passes the same 3/3 strict structured-output test Nemotron already passes. Nemotron currently
meets every requirement, so the burden of proof sits with the change.

**Unverified assumption worth closing early:** `nemotron-3-super-120b-a12b` is assumed to have a
1M-token context window, taken from the tech research rather than its model card. The decision to
drop the transcript summarizer depends on it. Confirm from the model card, or measure, before
Phase 5.

---

## Decisions & deviations

Dated log of where reality diverged from the plan. **These entries supersede
`ARCHITECTURE.md` wherever they conflict.**

**2026-07-30 · STORY 0.6: the interrupt rule is real, but the reason written in the spec was
wrong. Breaking it duplicates SIDE EFFECTS, not state — so no state assertion can detect it.**

The idempotency test was falsified before being trusted. A deliberately wrong graph, with the LLM
call and the increment above `interrupt()` in one node, was driven through a full pause-and-resume
against the same `app.llm` call log:

```
llm calls at pause      : 1
llm calls after resume  : 2      <- the rule is load-bearing, confirmed
turn_count after resume : 1      <- NOT 2, which is the surprise
```

Two calls, so the assertion in `test_interrupt.py` genuinely discriminates rather than passing
because everything passes. **But `turn_count` stayed at 1.** LangGraph discards the state writes
of a node that interrupted and applies them only on the run that completes, so the double
execution is invisible in state.

**This changes what to guard against.** The cost of breaking the rule is not a corrupted counter,
which is what PHASE-0-SPEC implied and what I would have asserted on. It is duplicated *side
effects*: a burned LLM call against the 40 RPM ceiling, a doubled row in `transcript_turns`, a
doubled `agent_events` emission driving the UI's realtime rail, a doubled Supabase write. Those
all escape the graph, so nothing rolls them back.

**Consequence for Phase 3 and anything writing outside graph state:** a test that checks state
after a resume proves nothing about this. Assert on the call log or on row counts in the table
being written. The one-assertion version is what `test_interrupt.py` does.

**2026-07-30 · Story 0.5 broke two of story 0.4's tests, and only running the FULL suite caught
it. Worth changing how phases are handed over.**

`test_schema.py` asserted set equality on `pg_tables where schemaname='public'` against the six
app tables. Correct in 0.4. Then 0.5 ran `init_db.py`, LangGraph created four tables **in the
same schema**, and both assertions failed.

**Why it nearly shipped:** each agent verified only the file it wrote. The checkpointer work ran
`test_checkpointer.py` and `-m "not live"`, both green, and never ran `test_schema.py`. The
regression sat in a file nobody had reason to re-run.

**Rule, now in CLAUDE.md § What to update:** a story that creates database objects, or changes
anything shared, must run the **entire** live suite before handover, not just its own file. The
offline suite is not sufficient — it stayed green at 21 passed throughout.

The fix made the RLS test **stronger** rather than merely accommodating: it now asserts RLS on
every table in `public`, including tables we did not create, so a future LangGraph version adding
an unprotected table fails the suite. The table-set test still rejects unexpected tables; it just
permits the `checkpoint%` family.

**2026-07-30 · Checkpoint cost measured. One earlier claim of mine confirmed, one refuted, and
the headline latency number is NOT the production one.**

Earlier this session I argued against keeping interview state in Render's memory, and made two
claims from reasoning rather than measurement. Both are now tested, with a 20-turn graph carrying
an ~8KB immutable `case_world` plus a transcript that grows every turn.

**Confirmed — LangGraph versions blobs per channel; unchanged channels are not rewritten:**

```
channel                 rows       bytes
messages                  40     535,908
__start__                 20      14,761
case_world                 1       8,273     <- written ONCE across 20 turns
```

So withdrawing the proposed `case_world_id`-in-state optimisation was correct: it would have
added indirection for nothing. **`messages` is the real cost driver** — 40 rows and 536KB from
roughly 26KB of actual content, because the whole accumulated list is re-serialised each turn.
Quadratic in turn count, as predicted.

**Total 0.58 MB per 20-turn interview → about 869 interviews before Supabase's 500MB free cap.**
Comfortable, but not unlimited, and it is the checkpoints that fill it rather than the app tables.

**Refuted, and I want this stated plainly: my "~1% of turn latency" estimate was unverified and
the measurement does not support it.** Observed **~298ms per checkpoint**, roughly 60x the ~5ms
I asserted for an intra-region round trip.

**But that number is not the production path either.** It was measured from a Windows dev machine
in India to Supabase in Singapore, so it is dominated by home-internet latency. Render in
Singapore to Supabase in Singapore is the real path and remains **unmeasured**. Do not quote
either 298ms or 1% as fact. **Story 0.8 must re-measure from the deployed service** — that is the
first time the real number is obtainable.

**2026-07-30 · STORY 0.5 SECURITY: LangGraph creates its checkpoint tables WITHOUT RLS. Fixed
in `init_db.py`. This was the worst exposure found so far.**

`.setup()` created `checkpoints`, `checkpoint_writes`, `checkpoint_blobs`, and
`checkpoint_migrations` in `public` with `rowsecurity = false`. Supabase exposes `public` through
the Data API and grants `anon`/`authenticated` full DML there by default. Measured before the
fix — `set role anon; select count(*) from checkpoints` **succeeded**, and anon also held
`INSERT`, `UPDATE`, `DELETE`, and `TRUNCATE`.

**Checkpoints contain the entire interview state**: resume text, full transcript, every
evaluation. So this was simultaneously a complete read exposure and a route to truncating the
table and destroying every in-progress interview.

Note the spec says three checkpoint tables. **There are four** — `checkpoint_migrations` is
LangGraph's internal version tracking. Never delete its rows; that would make `.setup()` replay
its migrations.

Secured inside `init_db.py` immediately after `.setup()`, not as a migration, because ordering
would otherwise be a trap: `migrate.py` can run before these tables exist, silently no-op, and
leave them unprotected forever. The statement pattern-matches `checkpoint%` rather than
hardcoding names, so a table added by a future LangGraph version is covered instead of quietly
missed. Verified after the fix — service role sees 3 rows, anon and authenticated see 0, and the
graph still runs because the pooler role has `rolbypassrls = true`.

**2026-07-30 · The transaction pooler fails ONLY under concurrency, which makes it far more
dangerous than "it errors".**

Story 0.5 asks for the `DuplicatePreparedStatement` text on record. Getting it took three
attempts, and the failures are the finding:

```
sequential, 1 connection, prepare_threshold=1, 60 round trips on 6543
  -> no error at all

12 concurrent connections x 25 prepared round trips on 6543
  -> ok=11/12
  -> psycopg.errors.DuplicatePreparedStatement: prepared statement "_pg3_0" already exists

AsyncPostgresSaver driving a real graph on 6543
  -> psycopg.errors.DuplicatePreparedStatement: prepared statement "_pg3_0" already exists
```

**A developer testing locally on 6543 would see it work perfectly.** One connection doing
sequential transactions never collides, and even under concurrency only 1 of 12 workers failed.
It breaks in production, intermittently, under load — the worst possible failure shape. The
port-5432 rule is not superstition inherited from old pgbouncer advice; it is measured here.

`config.py` rejects 6543 before connecting, so reproducing this requires building the URL
directly rather than going through `settings`.

**2026-07-30 · Windows dev machines need a non-default asyncio event loop. Local only.**
psycopg's async mode refuses Windows' default ProactorEventLoop:

```
psycopg.InterfaceError: Psycopg cannot use the 'ProactorEventLoop' to run in async mode.
```

Fix, guarded by platform, needed anywhere `AsyncPostgresSaver` is used locally:

```python
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

**Render runs Linux, where the selector loop is already the default, so this is invisible in
production.** It is in `init_db.py` and the checkpointer tests. **Stories 0.6 and 0.7 will hit it
again** when the graph is wired into FastAPI — uvicorn on Windows selects the proactor loop
unless told otherwise.

**2026-07-30 · STORY 0.4 RLS: the spec's own acceptance box was self-contradictory. Resolved by
adopting Supabase anonymous sign-in in Phase 1; Phase 0 ships zero policies.**

PHASE-0-SPEC asked for "RLS enabled on every table with permissive `session_id`-scoped
policies." **Those two halves cannot both be true.** Scoping rows by `session_id` requires the
database to know which session the caller owns, which comes from an auth token. V1 has no login,
`sessions.user_id` is nullable, so there is no claim to scope by. The only literal reading is
`using (true)` for `anon` — and the publishable key ships inside the browser bundle by design,
so that makes **every candidate's transcript and scores readable by anyone who opens devtools**.
Not obscurity: no UUID guessing needed, the whole table is selectable.

**Karthik's call: Supabase anonymous sign-in, wired in Phase 1.** The browser silently obtains a
real identity token, no signup screen, the candidate notices nothing, and `auth.uid()` then makes
genuinely scoped policies possible. `sessions.user_id` already exists and is nullable, so the
schema needs no change to support it.

**Phase 0 therefore ships RLS enabled with ZERO policies, deliberately.** RLS with no policies
denies every role that does not bypass it. The backend uses the service key and is unaffected;
browsers get nothing. Correct posture while the frontend is still a Vite placeholder.

**A trap worth recording, because reasoning about it gives the wrong answer.** `anon` and
`authenticated` **do** hold table-level `SELECT`/`INSERT`/`UPDATE`/`DELETE` grants on all six
tables — Supabase adds those by default in `public`. Grants control whether the table is
*reachable*; RLS controls which *rows* come back. I initially recorded "browsers can reach
nothing" from the grant query, which was wrong. Verified empirically instead:

```
as service role : 1 row(s) visible
as anon         : 0 row(s) visible   <- RLS denies despite the SELECT grant
as authenticated: 0 row(s) visible
```

The consequence for Phase 1: adding a policy is what opens the door, and the grants are already
open behind it. A single over-broad policy exposes everything immediately. `test_schema.py`
asserts the empirical denial rather than merely that `rowsecurity = true`, so an accidentally
permissive policy fails the suite.

**2026-07-30 · STORY 0.2 DECISION GATE: structured output is 7/10 on `deep`. Validate-retry is
now mandatory, and it is enforced in the wrapper rather than left to each agent.**

Measured through `ChatNVIDIA`, N=10 per cell, same schema and prompt throughout:

| Model | `with_structured_output` | `bind(response_format=json_schema)` |
|---|---|---|
| `nemotron-3-nano` (fast) | **10/10** · median 7.4s · p90 14.2s | 9/10 · median 5.6s · p90 7.5s |
| `nemotron-3-super` (deep) | **7/10** · median 20.4s · max 41.6s | **4/10** · median 9.1s |

**Four runs of `with_structured_output`, all on 2026-07-30 within about ninety minutes.**
Recorded in full because the spread matters more than any single row:

| Run | `fast` | `deep` |
|---|---|---|
| probe 1 | 9/10 · median 12.8s | 8/10 · median 19.7s |
| head-to-head | 10/10 · median 9.5s | 8/10 · median 12.6s |
| clean rerun | 10/10 · median 7.4s | 7/10 · median 20.4s |
| live test suite | 10/10 · median 7.2s | 9/10 · median 9.2s |

`fast` 9–10/10. `deep` 7–9/10, **never 10/10**, with its median moving between 9.2s and 20.4s
inside an hour. The decision below rests on the aggregate, not on the worst run.

**Chosen: `with_structured_output()`.** More reliable than `bind` on both models, and it keeps
automatic Pydantic parsing. It is slower, and that was accepted deliberately.

**The reliability problem is the model, not the method.** `nano` is near-perfect at structured
output; `super` fails 3–6 times in 10 whichever way it is called. Its `with_structured_output`
failures return **`None`** rather than raising, which is why `llm.py` now logs `outcome=empty` —
otherwise the failure is completely silent.

**Karthik's call (2026-07-30): retry now, revisit the model assignment in Phase 2.** The
alternative was moving the Case Architect, Planner, and Evaluator from `super` to `nano`
immediately, which buys 10/10 and cuts the median from 20.4s to 7.4s. Rejected for now because
`super` was chosen for reasoning quality and **no quality comparison has been measured** —
reassigning would trade an unmeasured property for a measured one. Phase 2's golden cases are
the first real quality signal. Revisit there, with data.

**This is worth flagging for whoever picks up Phase 2:** ARCHITECTURE.md §4 assigns `deep` to
three of the four structured-output agents and `fast` only to the Interviewer. On reliability
grounds that assignment is backwards. It is deliberately left alone for now, not overlooked.

**No deviation from ARCHITECTURE.md.** Its §4 already specifies "schema validation failure
re-prompts once with the validation error appended, then fails the node." The implementation
matches exactly. What changed is status, not design: that behaviour was written as defence in
depth and the measurement makes it load-bearing.

Two things retry deliberately does **not** do. It does not retry transport failures — a 429,
503, or timeout needs backoff per ARCHITECTURE §9, and an immediate second call would double
load exactly when the endpoint is refusing it. And it does not swallow a double failure into
`None`; it raises `StructuredOutputError`, because an unparseable value entering graph state
surfaces as a confusing error several nodes downstream.

**Correction to an earlier hypothesis in this file, recorded so it is not repeated.** The 2–4s
structured-output figure from 2026-07-29 came from raw HTTP with a simpler schema. I predicted
LangChain's tool-calling path was the slow one and the raw `json_schema` path the fast one. The
first head-to-head showed the opposite. It also scored raw `json_schema` at 6/10 on `deep`, but
**three of those four failures were a bug in my probe**: the Pydantic model declared
`confidence` with `ge=0.0, le=1.0` while the hand-written JSON Schema said only
`{"type": "number"}`, so the model returned a percentage and Pydantic rejected a response the
endpoint was never told to bound. Corrected in the clean rerun above. Run-to-run noise on the
same model and method was 9/10 vs 10/10, comparable to the gap between methods — **treat any
single N=10 run here as one sample.**

**2026-07-30 · `reasoning_effort` enum resolved — the last LLM-side unknown is closed.**
Nemotron accepts it (unlike `thinking`, which it rejects with HTTP 400). Sending a deliberately
invalid value made the validator enumerate the whole set:

```
reasoning_effort=xyzzy -> HTTP 400
  unknown variant `xyzzy`, expected one of
  `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`
```

`low`, `medium`, `high`, `max`, and `none` each returned HTTP 200 on `nemotron-3-super`.
**`high` exists, so ARCHITECTURE.md's assumption for the Evaluator holds** and needs no change.

Two notes for whoever uses this. Latency showed no clear ordering across levels at n=1 (0.4–0.7s,
except `none` at 5.8s, which is almost certainly contention rather than signal) — **do not treat
the level as a latency lever without measuring it properly.** And the technique generalises:
when an enum is undocumented, send a junk value and read it off the validator rather than
guessing one at a time.

**2026-07-30 · Streaming through `ChatNVIDIA` confirmed working.** 128 chunks, first at 0.50s,
3.4s total for a 212-character answer. Worth holding next to the structured-output numbers:
first token in half a second means the models are not slow. Structured output specifically is.

**2026-07-30 · `with_structured_output()` bypassed the logging wrapper — real bug, fixed.**
The scaffold returned `self._client.with_structured_output(...)`, a runnable wired straight to
the underlying client. Every structured call skipped `LoggingChatNVIDIA` entirely. Since agents
use structured output almost exclusively, **nearly the whole application would have been
invisible to the rate-limit log while appearing to work** — against CLAUDE.md's "every LLM call
is logged with a timestamp", and the free tier's 40 RPM ceiling is the first thing that breaks
under a demo. `tests/test_llm.py::test_structured_calls_are_logged_too` is the regression guard.

**2026-07-30 · `openai==1.59.0` was never published. Pin corrected to `1.59.2`.**
PyPI's release train goes `1.58.1 → 1.59.2`; there is no `1.59.0`. `pip install -r
requirements.txt` failed outright on that line. Two things confirmed while fixing it:
`langchain-nvidia-ai-endpoints==1.4.3` declares `Requires-Dist: aiohttp, langchain-core,
requests` and **does not depend on `openai` at all** — it imports and runs fine with openai
absent. So this was a plain bad pin, not the dependency conflict it looked like. Kept the
package because story 0.2's decision gate allows dropping to the raw client for structured
output, and the probe scripts already use it. `pip check` now clean.

**2026-07-30 · GNU Make 4.4.1 installed via winget (`ezwinports.make`).** It was absent, which
blocked two 0.1 acceptance boxes written around `make`. Chosen over rewriting the command
interface because CLAUDE.md, PHASE-0-SPEC, and every future phase gate name `make` targets;
installing costs one command, rewriting costs doc churn in perpetuity. **Make has no deployment
impact** — Render runs `uvicorn` directly and Netlify runs `npm run build`; neither sees a
Makefile. Note for future sessions: winget modifies PATH but the change needs a new shell, so
`make` may appear missing until the terminal restarts. Binary is at
`%LOCALAPPDATA%\Microsoft\WinGet\Packages\ezwinports.make_*\bin\make.exe`.

All six targets verified on Windows. No `SHELL` override was needed — cmd.exe resolves the
forward-slash `.venv/Scripts/python.exe` path fine, which was the anticipated failure.

**2026-07-30 · `check_env.py` had drifted from the decisions in this file, and would have failed
every run.** It still required a single `NVIDIA_MODEL` var (replaced by the three-model split on
2026-07-29) and still probed `thinking: {"type": "disabled"}` (which Nemotron rejects with
`HTTP 400 Unsupported parameter(s)`, also recorded 2026-07-29). Both decisions were written down
correctly and the tooling was never updated to match. Now checks all three models, times each,
and flags any above 10s as contention rather than an env failure.

**The general lesson, worth more than the fix:** DEV-STATE was right and the script was wrong.
Scripts encode decisions too, and they drift silently because nothing re-reads them. When a
decision changes a variable name or an API parameter, grep `backend/scripts/` in the same commit.

**2026-07-30 · CORS "rejects an unlisted origin" needs the right assertion, or `test_api.py`
will encode a false pass.** A simple `GET` with a disallowed `Origin` returns **HTTP 200** with
the `access-control-allow-origin` header *absent* — the browser is what blocks it. Only a
**preflight `OPTIONS`** returns `400 Disallowed CORS origin`. Both observed:

```
GET     Origin: http://evil.example.com   -> 200, no access-control-allow-origin
OPTIONS Origin: http://evil.example.com   -> 400 Bad Request
OPTIONS Origin: http://localhost:5173     -> 200, access-control-allow-origin echoed
```

So the phase-spec test must assert on **preflight status** or on **header absence**, never on a
simple request returning non-200. Asserting the latter would fail against correct code and
invite someone to "fix" working CORS.

**2026-07-30 · Pre-commit hook lives in tracked `.githooks/`, not `.git/hooks/`.**
`core.hooksPath` is set to it, so the hook survives a clone. `.git/hooks/` is not version
controlled, which would have made the guard a matter of whoever set up the machine — the
opposite of the "structural rather than a matter of care" intent in story 0.3.

The hook matches each prefix **followed by 20+ characters of key material**, not the bare
prefix, because DEV-STATE.md, `check_env.py`, and `.env.example` all name `nvapi-` and
`sb_secret_` deliberately and must stay committable. It also filters placeholder forms:
`.env.example` ships `nvapi-xxxxxxxx...`, which is shape-identical to a real key. **Known
trade-off: a real key containing eight consecutive `x` characters would slip through.**

**2026-07-29 · Design skill: v1 governs this product, not v2.** All 13 skills from
`github.com/Leonxlnx/taste-skill` are installed. Note the plan's `--skill "taste-skill"` name
does not exist — skill names differ from directory names in that repo. Installing without
`--skill` takes all 13, which is what we did.

The important finding: **`design-taste-frontend` (v2) explicitly scopes itself out of this
product** in its own §13 — "Dashboards / dense product UI / admin panels… Multi-step forms /
wizards" — and instructs the agent to say so rather than apply it wholesale. But
**`design-taste-frontend-v1` still carries dedicated software-UI rules that v2 dropped** when
it was rewritten toward landing pages: serif banned on dashboards with two named sans pairings,
dashboard card-container hardening gated on density, a mandatory icon library, and mono for all
numbers.

**v1 is therefore the governing skill.** v2 contributes its expanded AI-tells list and the
em-dash ban. Reasoning and dial settings in `ARCHITECTURE.md` §8.

Also checked and rejected: `high-end-visual-design` is Awwwards/agency-tier and prescribes
`py-24`–`py-40` macro-whitespace, floating glass-pill navigation, and eyebrow tags — correct
for a marketing page, absurd for a three-column assessment tool. `minimalist-ui` and
`gpt-taste` are likewise landing-page oriented. `industrial-brutalist-ui` is the only other
one that names dashboards, but its aesthetic contradicts the brief. **`full-output-enforcement`
is not a design skill and is worth applying generally** — it bans `// ...` and "rest of code"
placeholder patterns in generated output.

**2026-07-29 · Dials set: VARIANCE 3 · MOTION 4 · DENSITY 6.** Motion deliberately below 5
to avoid v1's perpetual-micro-interaction mandate, which would fight the anti-jitter
requirement from UI research; the active-agent pulse is the one exception since it carries
real semantic state. Density at 6 keeps card containers legitimate — v1 bans them above 7,
which would contradict the brief. Cards are used for the three column surfaces and chat
messages; agent rows and score rows inside the rails are grouped with hairlines, not nested
cards.

**2026-07-29 · Icon library resolved: Phosphor, not Lucide.** Open question closed. v1 §2
mandates `@phosphor-icons/react` or `@radix-ui/react-icons`; v2 §3.C discourages Lucide;
`high-end-visual-design` §2 bans "standard thick-stroked Lucide" outright. Three independent
agreements. shadcn's Lucide default is swapped at scaffold time in Phase 1 —
`strokeWidth 1.5` standardized globally.

**2026-07-29 · Progress-bar question closed, no change needed.** v2's pre-flight bans
"scoring/progress bars with filled background tracks," but its own §9.F frames this as a
landing-page rule and calls the pattern "dashboard-UI clutter *on a landing page*." We are the
dashboard. The right panel's bars are correct as specified.

**2026-07-29 · Accent colour desaturated.** The plan's accent `#2C5FF6` is roughly 92%
saturation; the skills cap accents at 80%. Changed to `#3A63D0` light / `#6E92E8` dark.

**2026-07-29 · Serif dropped entirely; mono changed to Geist Mono.** An earlier draft paired
Geist with Fraunces for display headings. v2 §4.1 bans Fraunces and Instrument Serif by name
as the two LLM-favourite display serifs, and v1 §7 bans serif on dashboards outright. Mono
switched from JetBrains to **Geist Mono** to match v1's named pairing exactly.

**2026-07-29 · Two design rules constrain agent prompts, not just CSS.** v1 §7 bans
fake-round numbers (`99.99%`, `50%`, `$1M`) and generic names ("John Doe", "Sarah Chan"
register). These reach into the **Case Architect's spec**: generated financials must be
organic (`31.4%` market share, `$4.7M` ARR) and generated company, competitor, and persona
names must not sit in the banned register. The placeholder interviewer name "Maya Chen" used
in the architecture wireframes is itself in that register and must be replaced before Phase 3
ships.

**2026-07-29 · Transcript summarizer dropped from V1.** Interview research recommended one for
context management. GLM 5.2's 1M-token context makes it unnecessary at single-round scale.
Revisit only if multi-round sessions are added.

---

**2026-07-29 · NVIDIA account model resolved: pure rate limit, no credits.** Confirmed from the
account dashboard — **up to 40 RPM**, no credit balance anywhere. The credit-trial model
described in older forum sources is gone. This closes the blocker and, importantly, means
**there is no budget that can be exhausted mid-build**. The only constraint is concurrency,
which the architecture already handles. Story 0.3 can be marked complete without further work.

**2026-07-29 · MODEL CHANGED: GLM 5.2 → Nemotron 3 family. Latency, measured.**

GLM 5.2 is capable and its capability panel is accurate. It is also **unusable on the free
tier**: a trivial 3-token prompt took **~230 seconds**, of which ~228s was queueing and ~2s was
generation. Streaming proved it — HTTP 200 arrived at 229.9s, first token at 231.9s, complete at
232.1s. The model works; you just cannot get to it.

A discriminating test showed this is **per-model demand, not an account throttle**:

| Model | Latency (trivial prompt) |
|---|---|
| `z-ai/glm-5.2` | ~230s queued |
| `meta/llama-3.3-70b-instruct` | >75s queued |
| `openai/gpt-oss-120b` | >45s queued |
| `nvidia/nemotron-3-nano-30b-a3b` | **0.3s** |
| `nvidia/nemotron-3-super-120b-a12b` | **0.4s** |
| `openai/gpt-oss-20b` | **0.3s** |

Structured output, 3 trials per model per mode, `max_tokens 3000`, `temperature 0`:

| Model | `response_format: json_schema` | prompt-only | latency |
|---|---|---|---|
| `nemotron-3-nano-30b-a3b` | **3/3 strict** | 3/3 strict | 2.3–4.2s |
| `nemotron-3-super-120b-a12b` | **3/3 strict** | 3/3 strict | 1.7–4.3s |
| `openai/gpt-oss-20b` | 3/3 strict | 3/3 strict | ~4.0s |
| `llama-3.3-nemotron-super-49b-v1.5` | 3/3 strict | 3/3 strict | 23–46s (too slow) |

**Decision: `nemotron-3-nano-30b-a3b` for the Interviewer, `nemotron-3-super-120b-a12b` for
everything else, `openai/gpt-oss-20b` as fallback.** Structured output is no longer a risk —
strict `json_schema` was 3/3 on every fast candidate. Prompt-validate-retry stays as defence in
depth but is not load-bearing.

**Worth naming plainly: this is what the original tech research recommended, and I overrode it.**
The researcher proposed the Nemotron 3 family; I switched to GLM 5.2 on the strength of its
documented 1M context and explicit structured-output support. That reasoning was sound on
capability and wrong on the dimension neither of us had data for — how heavily contended a
popular third-party model is on NVIDIA's free tier. Capability was documented; provisioning had
to be measured.

**2026-07-29 · The `thinking` parameter is GLM-specific, not portable.** Nemotron 3 rejects it
with `HTTP 400 Validation: Unsupported parameter(s): 'thinking'`. The latency-vs-quality lever
designed into the architecture therefore no longer exists as a parameter. Replaced by **model
choice** — nano for latency-critical turns, super for quality-critical ones. Arguably cleaner,
since it is one dimension instead of two.

**2026-07-29 · `/v1/models` lists models the account cannot use.** 102 returned, but
`nvidia/llama-3.1-nemotron-70b-instruct` and `moonshotai/kimi-k2.6` return `404 Function not
found`, and `deepseek-ai/deepseek-v4-flash` / `nemotron-3-ultra-550b-a55b` return
`503 ResourceExhausted`. Never treat catalog presence as availability — issue a real completion.

**2026-07-29 · GLM 5.2 capabilities confirmed from the official model page.**
[build.nvidia.com/z-ai/glm-5.2](https://build.nvidia.com/z-ai/glm-5.2) Specifications and
Capabilities panels state: Provider Z.ai · Context Length **1M** · Parameters **753B** ·
Function Calling **Supported** · Structured Output **Supported** · Reasoning **Supported** ·
Text in, text out.

**Structured Output being explicitly listed is the significant one.** It was the single
unresolved risk in the tech research — my researcher could not confirm whether `guided_json`
worked on the free hosted endpoint or only on self-hosted NIM containers. It is now confirmed
from the vendor's own capability panel. The prompt-validate-retry fallback stays in the
architecture as defence in depth, but it is no longer a load-bearing assumption. Story 0.2
still measures the actual pass rate, since "supported" and "reliable ten times out of ten"
are different claims.

**2026-07-29 · NVIDIA key exposed; keeping it — deliberate decision, do not re-flag.**
The key was captured in a screenshot and remains in use. Karthik has decided not to rotate it.
Risk is bounded: the free tier is rate-limited at 40 RPM with no credit balance, so worst case
is contention, not cost. `backend/.env` is gitignored. **Future sessions: this is settled, do
not raise it again.**

Still worth doing in Phase 0 story 0.1: a pre-commit hook blocking the `nvapi-` and `sb_secret_`
prefixes. That guards the commit path regardless of this particular key's status.

**2026-07-29 · Supabase project recreated in Singapore; Render must deploy to Singapore.**
The first project (`naiwpcveuouubperqtet`) was created in **Sydney, `ap-southeast-2`** — determined
not from the dashboard but from the project's own IPv6 allocation: `db.<ref>.supabase.co`
resolves to `2406:da1c:10e4:...`, and AWS's published `ip-ranges.json` assigns `2406:da1c::/35`
to `ap-southeast-2`.

Render's free tier does not offer Sydney (Oregon, Ohio, Virginia, Frankfurt, Singapore only), so
backend and database would have sat on different continents. That interacts badly with this
architecture specifically: **LangGraph checkpoints after every node**, so one candidate turn is
roughly four checkpoint writes plus app-table writes — call it eight round trips. At ~100ms
Singapore↔Sydney that is close to a second of added latency per turn, permanently.

The decisive argument was asymmetry of cost, not raw milliseconds: the schema did not exist yet,
so recreating was free. After story 0.4 creates six tables plus LangGraph's checkpoint tables, a
region change becomes a real migration.

**Consequence for Phase 0 story 0.8: Render service region must be Singapore.** Not the default.

**New project: `tnqfqsocoqythakwybsw`, Singapore, verified.** Region confirmed the same way rather
than trusting the dropdown: `db.tnqfqsocoqythakwybsw.supabase.co` → `2406:da18:1691:a201:...`, and
AWS assigns `2406:da18::/35` to `ap-southeast-1`. Both `aws-0-` and `aws-1-` Singapore pooler hosts
resolve and accept TCP on 5432. Old Sydney project retained until the new one is proven, then
deleted (free tier allows two).

**2026-07-29 · Direct connection IPv6-only — now verified, not assumed.**
`db.naiwpcveuouubperqtet.supabase.co` returned an AAAA record and **no A record at all**. The
architecture's claim that Render's IPv4-only free tier cannot reach Supabase's direct connection
is measured fact. Session pooler remains mandatory. Both `aws-0-` and `aws-1-` pooler hosts
resolve and accept TCP on 5432; which one a project uses is not predictable from the ref, so if
auth fails on `aws-0-`, try `aws-1-` before assuming the password is wrong.

**2026-07-29 · Second credential exposure — database password.** The first database password was
posted in plaintext in chat. Reset as part of the project recreation. Separately it contained an
`@`, which breaks Postgres URL parsing and would have needed percent-encoding. Standing rule:
database passwords are letters and digits only.

**2026-07-29 · Supabase official agent skills installed.** `npx skills add supabase/agent-skills`
→ `supabase` and `supabase-postgres-best-practices`. Note the `supabase` skill scores **Medium**
on Snyk (the Postgres one is Low); skills run with full agent permissions, so worth knowing.

**2026-07-29 · Testing convention added, three tiers.** The phase spec originally carried only
acceptance criteria, with no test layer defined for non-agent work. Now: (1) automated tests in
`backend/tests/` and `frontend/src/**/*.test.ts`, named in the phase spec, with assertions in
code; (2) golden cases as fixtures, defined in agent specs, gating every prompt change; (3) a
**Handoff** section ending each phase spec, splitting "verified by me, with evidence" from
"needs your eyes." Rule recorded in `CLAUDE.md`: a phase is handed over with observed output
pasted into this file, or it is not handed over. "Compiles" and "tests should pass" are not
evidence.

---

## Blockers & open questions

~~`reasoning_effort` enum unknown~~ — **RESOLVED 2026-07-30. See Decisions.** Full set is
`none · minimal · low · medium · high · xhigh · max`. `high` exists, so the architecture's
assumption for the Evaluator holds. **No LLM-side unknowns remain.**

~~NVIDIA account model~~ — resolved 2026-07-29 from the account dashboard. See Decisions.

~~Structured-output latency 11–14s vs 2–4s~~ — **RESOLVED 2026-07-30.** Explained by two things:
the 2–4s figure came from a simpler schema over raw HTTP, and free-tier contention swings widely
(the same model and method moved between 9.2s and 20.4s median inside one hour). Four N=10 runs
are tabled under Decisions.

**Still open, and it is a product question rather than a bug: is 7–9s acceptable per
Interviewer turn?** `fast` is 10/10 at a ~7.2s median, which is what the Interviewer uses, so
the reliability side is fine. But a candidate waits on every one of those calls, and the p90 was
14.2s. Plain streaming is 0.5s to first token, so **streaming the Interviewer's question is the
obvious mitigation** and is worth deciding in Phase 3 rather than at the end.

**Production checkpoint latency is unmeasured.** The 298ms observed on 2026-07-30 is from a
Windows dev machine in India to Supabase in Singapore, dominated by home-internet round trip.
Render-in-Singapore to Supabase-in-Singapore is the path that matters and cannot be measured
until 0.8 deploys. **Do not quote 298ms, and do not quote the earlier "~1% of turn latency"
estimate either** — neither is established.

**`make test-web` has nothing to run.** The frontend has no `test` script and vitest is not
installed — correct for Phase 0, which has no frontend tests, but `make test` will fail on the
`test-web` leg until Phase 1 adds vitest. Do not read that failure as a broken scaffold.

**Interviewer persona name needs replacing.** "Maya Chen" appears throughout the architecture
wireframes as a placeholder and sits in the exact register v1 §7 bans ("John Doe", "Sarah
Chan"). Needs a real choice before Phase 3 ships.

~~Icon library conflict~~ — resolved 2026-07-29, Phosphor. See Decisions.
~~Progress-bar tension~~ — resolved 2026-07-29, no change needed. See Decisions.

---

## Environment notes

Populated during Phase 0 as things are actually verified.

**Toolchain, observed 2026-07-30:** Python 3.12.10 · Node 26.1.0 · npm 11.13.0 · git 2.54.0 ·
GNU Make 4.4.1 (installed this session, see Decisions).

**Backend venv at `backend/.venv`** — Python 3.12.10. The global interpreter has different
versions of fastapi/pydantic/openai and **no langgraph at all**; always use the venv or a `make`
target. Installed and `pip check` clean:

```
fastapi 0.135.1 · pydantic 2.10.4 · langgraph 1.2.9
langgraph-checkpoint-postgres 3.1.0 · langchain-nvidia-ai-endpoints 1.4.3
psycopg 3.2.3 · psycopg-pool 3.3.1 · openai 1.59.2
pytest 8.3.4 · pytest-asyncio 0.25.0
```

**Frontend:** Vite 8.1.5 · React 19.2.7 · **Tailwind v4.3.3 via the `@tailwindcss/vite` plugin**
— v4 style, so there is no `tailwind.config.js` and no `@tailwind` directives; `src/index.css`
opens with `@import "tailwindcss";`. Do not add v3-style config, the two do not mix. Tailwind was
proven to actually compile, not merely install, by grepping the built CSS for emitted rules. No
`lucide-react` anywhere, per the Phosphor decision.

**Supabase connection: session pooler, port 5432 — verified working 2026-07-30.**
`aws-0-ap-southeast-1.pooler.supabase.com:5432`, PostgreSQL 17.6. `check_db.py` connects clean.
**Six app tables now live** (story 0.4). `check_db.py` reports "public tables: 0" only before
that migration — after it, expect 6.

**Schema is managed by `backend/migrations/*.sql` + `scripts/migrate.py`. Never the dashboard.**
Story 0.8 deploys to Render, and a schema that exists only as dashboard clicks cannot be
recreated. Migrations are written idempotent so re-running is safe. Two separate concerns:
`migrate.py` owns the six app tables, `init_db.py` owns LangGraph's checkpoint tables.

- `checkpointer.setup()` runs via `scripts/init_db.py`, once, never on app startup. It also
  enables RLS on the checkpoint tables, which LangGraph does not do.
- **Transaction-pooler error text, observed 2026-07-30:**
  `psycopg.errors.DuplicatePreparedStatement: prepared statement "_pg3_0" already exists`.
  Reproduces only under concurrency — see Decisions.
- **Windows dev only:** `asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())`
  is required before any async psycopg use. Not needed on Render.
- **10 public tables:** six app tables + `checkpoints`, `checkpoint_writes`, `checkpoint_blobs`,
  `checkpoint_migrations`. All ten have RLS enabled, none have policies.
- **Checkpoint volume:** ~0.58 MB per 20-turn interview, roughly 869 interviews to the 500MB
  free cap. `messages` dominates; `case_world` is stored once.
- All 13 skills installed at `.agents/skills/` (symlinked for Claude Code).
  **Governing skill for this product: `design-taste-frontend-v1`.** See Decisions.
- `stitch-design-taste` independently corroborates the v1 dashboard rules — "Serif is always
  BANNED in dashboards or software UIs" and "Dashboard Constraint: use Sans-Serif pairings
  exclusively (`Geist` + `Geist Mono` or `Satoshi` + `JetBrains Mono`)". It also generates a
  semantic `DESIGN.md` for agents to follow. **Worth considering in Phase 1** as the artifact
  that encodes our tokens, rather than hand-writing one.
