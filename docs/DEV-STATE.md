# Development State

**Last updated:** 2026-07-30 · Session 3

---

## Now

**Phase 0 — Walking skeleton. ✅ COMPLETE 2026-07-30. All eight stories, all six phase-gate
conditions, deployed and proven end to end.**

```
frontend  https://pmaiinterviewpanel.netlify.app
backend   https://pm-interview-panel.onrender.com     (Render, Singapore, free)
database  tnqfqsocoqythakwybsw                        (Supabase, Singapore, free)
```

**All four risks this phase existed to retire are retired**, each with a measured number rather
than an assumption:

| Risk | Answer |
|---|---|
| Is structured output reliable on the free endpoint? | No, not fully. `deep` 7-9/10 → validate-retry is mandatory, enforced in the wrapper |
| Does Supabase work from Render at all? | Yes. Session pooler, and a checkpoint step costs **~27ms** in production |
| Does `interrupt()` really resume across separate HTTP requests? | Yes. Proven across two separate OS processes, and against the deployed URL |
| What is the account's rate model? | 40 RPM, no credits, nothing exhaustible |

**Phase 1 is IN PROGRESS as of 2026-07-31. Stories 1.1, 1.2, 1.5, 1.3a and 1.6a are done and
committed. Next is story 1.3b, the Resume Analyst prompt itself — see § Next session, start here.**

The database is no longer wide open: cross-session denial is proven on all six tables with real
JWTs. Resumes upload, extract, and reject a scanned PDF loudly. The design foundation governs every
later phase, and `make test-web` runs for the first time in the project.

**Carried into Phase 1, do not lose:** Supabase **anonymous sign-in must be wired before the
frontend reads any data.** Phase 0 ships RLS with zero policies, so browsers currently get
nothing — correct now, but it means the three-column UI will show an empty middle column until
sign-in plus scoped policies exist. See Decisions 2026-07-30.

**Anonymous sign-in is DISABLED on the project as of 2026-07-31, measured, and it is a dashboard
toggle no script can flip.** See Blockers.

---

## Phase status

| Phase | Status | Spec | Verified |
|---|---|---|---|
| Planning docs | ✅ complete | — | 2026-07-29 — PRD, ARCHITECTURE, CLAUDE.md, research all written |
| 0 Walking skeleton | ✅ complete | PHASE-0-SPEC.md | 2026-07-30 — 52 tests live, deployed, phase gate 6/6 |
| 1 Resume Analyst + design foundation | 🟡 in progress — **1.1, 1.2, 1.5, 1.3a, 1.6a done**; 1.3b, 1.4, 1.6b, 1.7 remain | PHASE-1-SPEC.md | 2026-07-31 — 85 live tests, **53 offline, 33 vitest** |
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
| Resume Analyst | ✅ [AGENT-RESUME-ANALYST-SPEC.md](specs/agents/AGENT-RESUME-ANALYST-SPEC.md) — written 2026-07-31, before the prompt | **8 written and red on purpose** (story 1.3a). Green once 1.3b lands | — (no prompt yet) |
| Case Architect | ⬜ (Phase 2) | — | — |
| Planner | ⬜ (Phase 2) | — | — |
| Interviewer | ⬜ (Phase 3) | — | — |
| Evaluator | ⬜ (Phase 4) | — | — |
| Coach | ⬜ (Phase 5) | — | — |

---

## Current phase — story detail

**Phase 1 stories are defined in `docs/specs/PHASE-1-SPEC.md`.** Wave plan set 2026-07-31:
1.1 + 1.5 in parallel, then 1.2 + 1.3, then 1.4, then 1.6, then 1.7 inline.

- [x] 1.1 ~~Anonymous sign-in and scoped RLS policies~~ — done 2026-07-31. Cross-session denial proven on all six tables with real JWTs through PostgREST, re-proven independently. Output below
- [x] 1.2 ~~Resume upload and text extraction~~ — done 2026-07-31. 18 tests. **Deviates from ARCHITECTURE §1 deliberately** (backend-proxied upload, reasoning in Decisions) and **shipped three em-dashes into candidate-facing copy**, now fixed and guarded
- [ ] 1.3 Resume Analyst agent — **split in two, see Decisions 2026-07-31**
  - [x] 1.3a ~~golden fixtures + assertion harness~~ — done 2026-07-31. 8 fixtures, 23 offline tests, suite deliberately RED. **Independent probe found the spec's most important assertion passing vacuously on all eight cases; fixed and re-falsified.** Output below
  - [ ] 1.3b the agent itself — `app/agents/resume_analyst.py`, prompt, golden run on both models
- [ ] 1.4 `level_candidate` → `confirm_level`, the first real interrupt
- [x] 1.5 ~~Design foundation~~ — done 2026-07-31. All nine boxes. **`make test-web` runs for the first time in the project.** Two deviations found in verification, both below
- [ ] 1.6 Upload and confirmation UI — **split in two**
  - [x] 1.6a ~~shell, anonymous sign-in, upload surface~~ — done 2026-07-31. 33 vitest tests. Env vars proven inlined into the bundle. **One defect found in review, deferred to 1.6b with the reason recorded**. Output below
  - [ ] 1.6b confirmation screen, orchestration column states, Realtime on `agent_events`
- [ ] 1.7 Delete the Phase 0 scaffolding — **one item struck early, see Decisions 2026-07-31**

### Phase 0 stories — all complete, kept for the record

Defined in `docs/specs/PHASE-0-SPEC.md`.

- [x] 0.1 ~~Repo scaffold, `.env` handling, `requirements.txt`, Vite app, secret-prefix pre-commit hook~~ — done 2026-07-30, all four acceptance boxes verified with output below
- [x] 0.2 ~~NVIDIA smoke test~~ — done 2026-07-30. Gate resolved: **not 10/10** (`deep` 7-9/10), so validate-retry is mandatory. Streaming, rate-limit logging, and the off-peak re-measure all done
- [x] 0.3 ~~Confirm build.nvidia.com account model~~ — done 2026-07-29: 40 RPM, no credits
- [x] 0.4a ~~Supabase project + connection verified~~ — done: Singapore, session pooler, Postgres 17.6, `check_db.py` connects
- [x] 0.4 ~~Supabase project + schema migration~~ — done 2026-07-30. Six tables, RLS on all, realtime publication, private `resumes` bucket, constraints proven by failed inserts
- [x] 0.5 ~~Postgres checkpointer wired via session pooler, `.setup()` run once~~ — done 2026-07-30. Idempotent, no collision, 6543 failure reproduced, **RLS added to LangGraph's tables**
- [x] 0.6 ~~Two-node graph with `interrupt()` / `Command(resume=...)`~~ — done 2026-07-30. All five boxes, and **the idempotency assertion was falsified against a deliberately wrong graph before being trusted**
- [x] 0.7 ~~Interrupt/resume proven across two separate HTTP requests~~ — done 2026-07-30. Restart proven with **two separate uvicorn subprocesses**, not a rebuilt TestClient
- [x] 0.8 ~~Deploy backend to Render, frontend to Netlify, CORS wired, health check green~~ — done 2026-07-30. Phase gate 6/6, cold start 32.3s, production checkpoint step ~27ms. Output below

---

### 1.3a golden fixtures and assertion harness — observed output

`backend/tests/golden/resume_analyst/` (8 `.txt` fixtures, `cases.py`, `assertions.py`,
`test_golden.py`, `test_assertions.py`) plus `backend/tests/test_resume_analyst.py`.

**The suite is deliberately RED and must stay red until 1.3b lands.** It was written before and
blind to the prompt, so 1.3b cannot tune a fixture until its prompt passes.

```
offline suite     53 passed, 67 deselected in 2.44s      (30 -> 48 from the story, -> 53 with my fix)
golden suite      23 passed, 8 errors in 0.20s
  every error: ModuleNotFoundError: No module named 'app.agents'   <- the only reason, by design
fixtures          263-304 words each, all eight
em/en dash in fixtures: none
```

Collection stays clean because the import is lazy, inside a session-scoped fixture. A module-level
import would make `pytest tests -m "not live"` **error during collection** — deselection happens
after collection — breaking the project's fastest feedback loop for every file, not just this one.
Deliberately not `pytest.importorskip`, which would silently skip forever once the module exists
but is misnamed.

**INDEPENDENT PROBE — the spec's single most important assertion was passing vacuously on all
eight cases.** Found with a probe written from scratch, not by re-running the agent's tests:

```
PROBE 1 - the lazy agent: scope_evidence=[] notable_outcomes=[]
  universal assertions -> PASS          <- quoting NOTHING passed
PROBE 2 - the fabricating agent: invents a quote   (positive control)
  universal assertions -> FAIL fabricated scope    <- the check DOES discriminate
PROBE 3 - the lazy shape against all eight cases
  01..08  ->  PASS PASS PASS PASS PASS PASS PASS PASS
```

`missing_verbatim_quotes([])` returns `[]`, so **silence beat effort.** This is story 1.1's
`A/own = 1` column in different clothes: a denial assertion with no positive control passes when
the mechanism under test is dead. Probe 2 is what makes the finding meaningful — the check itself
was correct, it just had no floor.

Fixed with `empty_quote_lists()` and re-falsified in both directions, because a fix that makes
everything fail is not a fix:

```
AFTER — lazy shape       01..08  ->  FAIL empty ['scope_evidence', 'notable_outcomes']  (x8)
AFTER — honest shape     01..08  ->  PASS PASS PASS PASS PASS PASS PASS PASS
```

`scope_evidence` has no exception; `notable_outcomes` is relaxed only for fixture 07, which states
zero results and where empty is the honest answer. A `test_exactly_one_case_expects_no_outcomes`
guard stops a future edit relaxing it everywhere and silently ending the gate.

**Second defect, in the brief rather than the agent's work: retry detection missed half the
retries.** `_LoggedStructured` logs `outcome=empty` for `deep` returning `None` **and
`outcome=invalid` for a `ValidationError`** — both trigger a retry. My brief named only the first,
so the file would have recorded "retry never fired" while retries were firing, against the one
acceptance box that exists to stop that being assumed.

```
outcome=empty    retries=True  detected=True  OK
outcome=invalid  retries=True  detected=True  OK      <- was False before the fix
outcome=ok       retries=False detected=False OK
```

### 1.6a shell, anonymous sign-in, upload surface — observed output

`frontend/src/lib/supabase.ts`, `lib/api.ts`, `components/{AppShell,UploadSurface,
OrchestrationColumn,EvaluationColumn}.tsx`, two test files, `App.tsx`, `vite.config.ts`.

```
npm test      33 passed (33)        (25 -> 33; the 25 from story 1.5 still green)
npm run build ✓ built in 783ms      dist/assets/index-B97giJQ4.js  419.21 kB │ gzip: 119.43 kB
npx oxlint    exit=0
```

**Env vars proven inlined into the built bundle, not merely referenced** — the story 0.8 / 1.5
lesson, since Vite only inlines what code actually reads:

```
dist/assets/index-B97giJQ4.js   supabase project ref occurrences: 1
                                API URL occurrences:              2
```

**Design rules verified by grep rather than by claim**, across all of `frontend/src`: zero
em-dashes and en-dashes outside story 1.5's comments (which the rule exempts), zero bare
`duration-standard`, zero `lucide`, and **no `console.*` anywhere** — so the JWT is never logged.
It appears only in two `Authorization: Bearer` headers.

**The frontend/backend contract checked against `app/main.py` directly**, not assumed: form field
`file`, `POST /session` → `{session_id}`, `POST /session/{id}/resume` → `{resume_id, storage_path}`,
errors as `{"detail": ...}`. All four match.

**`XMLHttpRequest` instead of `fetch`, and the reasoning is correct.** Only XHR's `upload` progress
event distinguishes "bytes still on the wire" from "bytes arrived, server is extracting text" —
that is the uploading/parsing boundary the story requires, and `fetch` has no equivalent signal.

### 1.2 resume upload and text extraction — observed output

`backend/app/resume.py` (pure, no network), `backend/app/supabase_client.py` (httpx against
Auth/PostgREST/Storage), two new routes in `app/main.py`, `backend/tests/test_resume_upload.py`.

**Driven end to end against a real local server, with real anonymous tokens and real files —
not by re-running the agent's tests:**

```
=== auth on POST /session ===
  no Authorization header -> 422        garbage token -> 401
  valid A token           -> 200 {"session_id":"56691565-..."}
  session A user_id == A uid: True      <- populated from the JWT, not from the client

=== THE SECURITY ONE: can B upload into A's session? ===
  B uploads to A's session -> 403 {"detail":"This session does not belong to the calling identity."}
  no token                 -> 422       unknown session -> 404

=== content inspection, not extension ===
  .pdf that is plain text  -> 400 {"detail":"Unsupported file. Please upload a PDF or DOCX resume."}

=== no-text-layer PDF ===
  blank/scanned PDF        -> 400 "This PDF has no extractable text. It looks like a scanned or
                                   image-only document. Please upload a text-based PDF..."

=== residue after every rejected upload ===
  resumes rows: 0      storage objects in bucket: 0
```

**Rejected uploads leave nothing anywhere**, because extraction runs *before* the storage write.
There is also a compensating delete if the database insert fails after a successful upload, so a
half-finished request cannot orphan an object.

```
offline suite            30 passed, 58 deselected in 2.42s   (21 -> 27 from the story, -> 30 with the copy guard)
tests/test_resume_upload 18 passed in 40.31s                 (re-run independently)
tests/test_llm.py         7 passed in 481.98s
full live suite          85 passed in 3765.07s               (agent's run, see the contention note)
```

### 1.1 scoped RLS policies — observed output

`backend/migrations/0002_rls_policies.sql` and `backend/tests/test_rls_policies.py` (15 tests),
plus a deliberate rework of `test_schema.py`'s denial test.

**The policy inventory, queried straight from `pg_policies` rather than read off the migration:**

```
table                cmd     roles              policy
agent_events         SELECT  {authenticated}    own session agent_events
answer_evaluations   SELECT  {authenticated}    own session answer_evaluations
case_worlds          SELECT  {authenticated}    own session case_worlds
resumes              SELECT  {authenticated}    own session resumes
sessions             INSERT  {authenticated}    own session insert
sessions             SELECT  {authenticated}    own session select
transcript_turns     SELECT  {authenticated}    own session transcript_turns

policies on checkpoint% tables: 0    policies granting anon: 0
public tables without RLS:      0    resumes bucket public:  False
```

**CROSS-SESSION DENIAL — re-proven independently, with a probe written from scratch rather than
by running the agent's tests.** Two fresh anonymous identities, real JWTs, real PostgREST calls:

```
table                   A/own   A/Bs  B/own   B/As   verdict
sessions                    1      0      1      0   PASS
resumes                     1      0      1      0   PASS
case_worlds                 1      0      1      0   PASS
transcript_turns            1      0      1      0   PASS
answer_evaluations          1      0      1      0   PASS
agent_events                1      0      1      0   PASS
```

**The `A/own = 1` column is the one that makes the test mean anything.** Had the token been
malformed, every cell would read 0 and the denial columns would pass vacuously. Also probed the
unfiltered `select=*` a curious candidate would actually type — one row on every table, never two.
Raw `anon` key with no user token: 200 with 0 rows, on every table.

```
full live suite : 67 passed in 382.61s (0:06:22)     <- run independently, 52 -> 67
offline suite   : 21 passed, 46 deselected in 2.00s
migrate.py      : ok on both files, twice            <- idempotency
residue after   : auth.users 0 · sessions 0 · resumes 0 · transcript_turns 0 · agent_events 0
```

### 1.5 design foundation — observed output

`frontend/src/index.css` (full rewrite), `src/lib/icons.tsx`, `src/index.css.test.ts`,
`src/assets/fonts/` (Geist + Geist Mono variable woff2, OFL licence kept alongside), `DESIGN.md`
at the repo root, plus vitest wired into `vite.config.ts` and `package.json`.

```
npm run build
  dist/assets/Geist-Variable-Bj2R_7yk.woff2       69.65 kB
  dist/assets/GeistMono-Variable-Dispecij.woff2   71.36 kB
  dist/assets/index-KSU7xFWs.css                  14.05 kB │ gzip: 3.93 kB
  ✓ built in 356ms

make test-web        25 passed (25)      <- FIRST TIME THIS TARGET HAS RUN
npx oxlint           exit=0, clean
backend offline      21 passed, 31 deselected in 2.47s   (backend untouched, git status clean there)
```

**The agent proved the accent hex reaches `dist/`. That was not the assertion that mattered**, and
finding the gap is what independent re-verification bought this time. `#3A63D0` reaches the bundle
from the plain `:root` block whether or not Tailwind's `@theme` layer works at all. What story 1.6
actually depends on is `@theme` **generating utilities** through a `var()` indirection, which was
untested. Probed by building a throwaway component that uses them and grepping the emitted CSS:

```
EMITTED  .bg-background   .text-text-secondary   .border-border   .rounded-card
EMITTED  .shadow-elevated  .font-mono  .ease-standard  .rounded-control  .text-error
MISSING  .duration-standard          <- the one that does not exist
.bg-accent\/40 { background-color: color-mix(in oklab, var(--color-accent) 40%, transparent) }
```

So the `var()` indirection works, opacity modifiers work, and one utility silently does not exist.
See the Decisions entry below.

## Last session

**Session 5 — 2026-07-31. Stories 1.3a and 1.6a complete. Both halves of a deliberate split.**

Two stories were **split in two** this session, and one of those splits paid for itself immediately.

**Story 1.3 was split so the golden suite could not be tuned to the prompt.** 1.3a wrote eight
fixtures and the assertion harness blind, delivering a suite that is red on purpose; 1.3b must make
it pass without editing a fixture or an assertion. The hazard was specific: an agent writing both
can nudge a fixture whenever the prompt misses, and the suite stops gating at the exact moment it is
supposed to start.

**That split bought the session's real finding. The spec's single most important assertion was
passing vacuously on all eight cases.** `missing_verbatim_quotes([])` returns `[]`, so an agent that
quoted **nothing** passed the fabricated-quote check that the agent spec calls the most important
assertion in the file. Found with a from-scratch probe, not by re-running the agent's tests, and the
positive control is what makes it meaningful: a fabricated quote **was** correctly rejected. The
check was right; it simply had no floor. **This is story 1.1's `A/own = 1` column in different
clothes** — a denial assertion with no positive control passes when the mechanism under test is dead.
Closed and re-falsified in both directions, because a fix that makes everything fail is not a fix.

**A second defect was mine, not the agent's.** My brief told it to detect retries by matching
`outcome=empty`. `_LoggedStructured` also logs `outcome=invalid` for a `ValidationError`, and both
paths retry. The file would have recorded "retry never fired" while retries were firing, against the
one acceptance box that exists to stop exactly that assumption.

**Story 1.6 was split on dependency, not risk.** 1.6a's shell, anonymous sign-in and upload surface
need nothing from 1.3 or 1.4, so they ran in parallel with 1.3a on a disjoint file set with no LLM
contention. 1.6b keeps the confirmation screen, the live orchestration states and Realtime.

**1.6a came back clean and stayed clean under independent re-verification** — env vars proven inlined
into the bundle, no em-dashes, no bare `duration-standard`, no `lucide`, no `console.*` anywhere so
the JWT is never logged, and the frontend/backend contract checked against `app/main.py` rather than
assumed. Its one defect was found by reading the flow rather than by any test: **a new session row
is created on every upload attempt**, so a rejected scanned PDF plus a retry orphans a row.
Deliberately deferred to 1.6b, where the session lifecycle is actually decided.

```
7af1d72  Story 1.3a: golden fixtures and a deliberately red assertion harness
218e832  Story 1.6a: app shell, silent anonymous sign-in, and the upload surface
857032b  docs: record 1.3a and 1.6a, the vacuity finding, and the deferred session defect
```

**Test counts moved 30 → 53 offline and 25 → 33 vitest. Live count unchanged at 85** — the eight
golden cases are written but cannot run until 1.3b exists.

**Session 4 — 2026-07-31. Stories 1.1, 1.5 and 1.2 complete. Three of Phase 1's seven stories, plus
the Resume Analyst contract written before its prompt.**

Delegated all three to Sonnet agents and re-verified every one independently. **That re-verification
found something real in all three cases**, which is the strongest evidence yet that the orchestrate/
delegate/verify split earns its cost:

- **1.5** — the agent proved the accent hex reached `dist/`, which would be true even if Tailwind's
  `@theme` layer did nothing. Probing what story 1.6 actually depends on, utility generation through
  a `var()` indirection, found `duration-standard` silently generates no class at all.
- **1.1** — cross-session denial re-proven with a from-scratch probe. Turned up that an unauthorised
  UPDATE/DELETE returns **200, not 403**, which would have encoded a false pass in any future test.
- **1.2** — three em-dashes had shipped into candidate-facing error copy, in a function whose own
  docstring says the message is for the candidate. No test caught it. Now `test_user_facing_copy.py`.

**Two agents contradicted their briefs and were right both times.** `strokeWidth 1.5` does not exist
in Phosphor (verified: zero occurrences in the package, icons are filled geometry). And ARCHITECTURE
§1's direct-to-Storage upload does not survive this phase's own scanned-PDF requirement. Both are
logged under Decisions; **CLAUDE.md was corrected for the first**, ARCHITECTURE left alone per the
decisions-supersede-it rule.

**Karthik enabled Supabase anonymous sign-in**, which unblocked 1.1. The probe that confirmed it also
surfaced the fact that reshaped the whole story: **anonymous users carry the `authenticated` role,
not `anon`.**

```
dea296a  Story 1.5: design foundation, plus vitest and the first make test-web run
1804af6  Story 1.1: scoped RLS policies, cross-session denial proven
232e70a  Story 1.2: resume upload, extraction, and the em-dash ban as a test
```

**Test counts moved 52 → 85 live, 21 → 30 offline, and `make test-web` runs for the first time in
the project (25 passed).**

**Not done, and deliberately not started:** story 1.3. It is the heaviest LLM story in the phase and
was left for a fresh session rather than begun at 75% context.

**Session 3 — 2026-07-30. Stories 0.6, 0.7 and 0.8 complete. PHASE 0 IS DONE, deployed, and
proven end to end.**

The interrupt/resume machinery the whole product rests on now works and is proven: a graph that
pauses, a pause that survives the process dying, and the same cycle driven against the deployed
URL from the Netlify origin. 52 tests green live, phase gate 6/6.

**Three numbers that were assumptions this morning and are measurements tonight:** production
checkpoint step ~27ms (not the 298ms local figure), cold start 32.3s, and `VITE_API_URL` proven
inlined by grepping the deployed bundle rather than trusting that it was set.

**The repo was pushed to GitHub for the first time** —
`https://github.com/karthikr0208/PM-interview-panel`, `main` tracking `origin/main`. History was
scanned before pushing: `.env` was never tracked at any commit, and the only credential-shaped
strings in the entire history are fake test fixtures (`pw`, `abcdefgh`). Note `gh` is not
installed on this machine, so **repo visibility was not confirmed.**

**Working mode changed at Karthik's request: implementation is delegated to Sonnet subagents;
this session's role is planner, orchestrator, and verifier.** Now written into CLAUDE.md § How
work is done so it does not need restating each session. Story 0.7 was built that way.

**It paid for itself immediately.** The agent contradicted its own briefing on the Windows
event-loop fix and was right to — the fix I specified does not work, which I then reproduced
myself. Independent re-verification also caught test residue accumulating in the live database
that the agent's own green test run had not surfaced.

```
7b7f471  0.6 two-node graph with interrupt/resume
7bc437b  0.7 interrupt/resume across two HTTP requests
f17706f  docs: correct stale commit hashes
362c395  pin Python 3.12.10 for the Render build
ff398ea  0.8 part 1: backend live on Render, phase gate met
ed1d582  frontend: backend connectivity check
800f28c  0.8 cold-start latency measured at 32.3s
```

**Deployment settings worth not rediscovering.** Render: root dir `backend`, build
`pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`,
region Singapore, `PYTHON_VERSION=3.12.10` plus a committed `backend/.python-version`. Netlify:
base dir `frontend`, build `npm run build`, publish `frontend/dist`, `NODE_VERSION=22`. Both
redeploy automatically on push to `main`, and each only rebuilds when its own directory changes.

### Session 2 — 2026-07-30. Stories 0.1, 0.2, 0.4, 0.5 complete

Phase 0 went from nothing on
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

### 0.8 backend deployed to Render — observed output

**`https://pm-interview-panel.onrender.com`** · Singapore · free tier · root dir `backend` ·
start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (no `--reload`, correct on Linux)
· Python pinned to 3.12.10 via `backend/.python-version` plus `PYTHON_VERSION`.

The line that mattered in the deploy log is `Application startup complete` — that is the
`lifespan` opening `AsyncPostgresSaver` against Supabase from inside Render. The session pooler
works from Render, which was the second of the four risks this phase existed to retire.

```
==> Running 'uvicorn app.main:app --host 0.0.0.0 --port $PORT'
INFO:     Started server process [62]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:10000
==> Your service is live
```

**THE PHASE GATE — two curl calls against the deployed URL.**

```
=== CALL 1 — POST /skeleton/start ===
{"session_id":"23caf429-7674-4372-8b1d-a3393352b07e","interrupt":{"question":"..."}}
[status=200  total=1.819343s]

=== CALL 2 — POST /skeleton/resume (a separate HTTP request) ===
{"session_id":"23caf429-7674-4372-8b1d-a3393352b07e","turn_count":1}
[status=200  total=0.213757s]

=== same session again, already finished ===
status=404
```

`turn_count: 1` is the 0.6 idempotency property holding in production, not just in tests.

```
/health                                          200  {"status":"ok"}
OPTIONS /skeleton/start  Origin: evil.example.com 400   <- CORS rejects, per the preflight rule
```

**FRONTEND ON NETLIFY — `https://pmaiinterviewpanel.netlify.app`.** Base dir `frontend`, publish
`frontend/dist`, `NODE_VERSION=22`.

**`VITE_API_URL` proven baked in at build time, not merely set.** Vite only inlines variables that
code actually reads, so the box was vacuous until `HealthCheck.tsx` referenced it. Verified by
grepping the *deployed* bundle:

```
https://pmaiinterviewpanel.netlify.app        200
  bundle /assets/index-k5qsSOLI.js  contains  https://pm-interview-panel.onrender.com
```

The deployed bundle hash differs from the local build's (`index-DjE-cX_-.js`), which independently
confirms Netlify baked in a different value than the dev machine did.

**CORS, before and after the `ALLOWED_ORIGINS` change — and the before half is the useful half.**

```
BEFORE (ALLOWED_ORIGINS=http://localhost:5173)
  Origin: https://pmaiinterviewpanel.netlify.app -> 200, NO access-control-allow-origin
  Origin: http://localhost:5173                  -> 200, header echoed

AFTER  (ALLOWED_ORIGINS=https://pmaiinterviewpanel.netlify.app)
  Origin: https://pmaiinterviewpanel.netlify.app -> 200, header echoed
  Origin: http://localhost:5173                  -> 200, NO header      <- nothing wider
  OPTIONS Origin: http://evil.example.com        -> 400
```

**This is the 2026-07-30 CORS decision confirmed in production: the server returns 200 either
way.** Enforcement is the browser refusing a response whose `access-control-allow-origin` is
absent. A test asserting non-200 on a simple request would have passed against a wide-open server.

**FULL CHAIN, carrying the Netlify origin — browser to Netlify to Render to Supabase:**

```
POST /skeleton/start   Origin: https://pmaiinterviewpanel.netlify.app
  {"session_id":"83a73411-...","interrupt":{"question":"What's one product decision you made..."}}
POST /skeleton/resume  Origin: https://pmaiinterviewpanel.netlify.app   (separate request)
  {"session_id":"83a73411-...","turn_count":1}
```

**COLD START: 32.3 SECONDS.** Probe left the service genuinely untouched for ~18 minutes, then
hit `/health` once cold and once warm:

```
idle since:      13:57:51Z
cold_start    = 32.33s   status=200
warm_followup =  0.13s   status=200
```

Better than Render's own "50 seconds or more" banner, and still a product problem rather than a
curiosity. **The first request a candidate makes would hang for half a minute**, on a tool whose
first interaction is uploading a resume. The warm follow-up at 0.13s confirms it is entirely
spin-up, not the app.

**Mitigation, when it matters and not before:** an external uptime pinger on `/health` every ~10
minutes. Cheap, external to the codebase, and reversible. Do not solve this by paying for Render
or by adding a self-ping inside the app. Decide it in Phase 7, or the day before a demo.

**PRODUCTION CHECKPOINT LATENCY — measured at last, and it is nothing like the local number.**

Measured by difference against `/health`, which does no database work, so the client-side
India→Singapore round trip cancels out. All medians of 10 samples, seconds:

```
/health                        (no DB)                     0.1162
/skeleton/resume on a FINISHED session (1 read, then 404)  0.1167   -> read  ~0.5ms, unmeasurable
/skeleton/resume on a PAUSED  session (read + writes)      0.1434   -> write path ~27ms
```

**One checkpoint read is not distinguishable from noise. A full resume step — one read plus the
node's checkpoint writes — costs about 27ms.** Against ~298ms per checkpoint from the Windows dev
machine, which was dominated by home internet.

**This retires the open question and settles both earlier claims.** My original "~1% of turn
latency" guess was unverified and I was right to refuse it after measuring 298ms locally. In
production it is roughly 27ms against a 7-9s turn, so about 0.3%. The guess was directionally
right for the wrong reasons, and only the deployed measurement could tell the difference.
**It also vindicates the Singapore region decision**: co-location is what makes this ~27ms.

### 0.7 interrupt / resume across two HTTP requests — observed output

`backend/app/main.py` (lifespan-held checkpointer, `/skeleton/start`, `/skeleton/resume`) and
`backend/tests/test_api.py`.

```
tests/test_api.py  6 passed in 48.83s
  test_health_returns_ok
  test_start_returns_session_id_and_interrupt_payload
  test_resume_continues_after_the_process_is_torn_down_and_rebuilt
  test_get_state_next_reflects_pause_then_completion
  test_resume_404s_for_an_unknown_session_id
  test_cors_preflight_rejects_unlisted_origin_and_allows_the_configured_one

full live suite:  52 passed in 476.05s (0:07:56)
offline suite  :  21 passed, 31 deselected in 3.87s
```

`make dev-api` driven by hand against the real endpoint, which is what proved the Windows
event-loop finding below:

```
GET  /health          -> {"status":"ok"}
POST /skeleton/start  -> 200 OK
  {"session_id":"d8e7b0b9-b46d-441e-9c98-f43e0774c152","interrupt":{"question":"..."}}
```

**Test residue fixed.** `test_api.py` was the only test file not cleaning up after itself, and
13 orphan thread_ids / 47 checkpoint rows had accumulated in the live database. It now registers
each server-minted `session_id` and deletes it in teardown. Verified by counting either side of
a full-suite run:

```
select count(distinct thread_id), count(*) from checkpoints
  before full suite : (0, 0)
  after full suite  : (0, 0)      <- 52 tests, several creating sessions
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

**Stories 1.1, 1.2, 1.5, 1.3a and 1.6a are DONE and committed.** Remaining, in order:
**1.3b → 1.4 → 1.6b → 1.7.** 1.7 must not start until 1.6b is verified.

**Run these three first (~1 min), before anything else:**

```
cd backend && .venv/Scripts/python.exe -m pytest tests -q -m "not live"   # expect 53 passed, 67 deselected
cd frontend && npm test                                                   # expect 33 passed
curl -s https://pm-interview-panel.onrender.com/health                    # {"status":"ok"}, ~32s if cold
```

**Then check whether 1.3b landed**, because it is the thing most likely to have been interrupted:

```
ls backend/app/agents/resume_analyst.py                  # exists? 1.3b ran
cd backend && .venv/Scripts/python.exe -m pytest tests/golden -q
  # 23 passed, 8 errors (ModuleNotFoundError: app.agents)  -> 1.3b never started, brief it
  # 31 passed                                              -> 1.3b is done and green
  # 23 passed, 8 failed                                    -> 1.3b ran and the agent is wrong.
  #   Iterate the PROMPT. Never the fixtures or assertions. See below.
```

**The golden suite is red BY DESIGN until 1.3b lands.** It was written blind to the prompt in story
1.3a precisely so the prompt cannot be tuned against it. **Whoever implements 1.3b may not edit a
fixture or an assertion** — if one looks wrong, stop and report it. That constraint is the only
thing making this agent falsifiable, and these eight cases gate every future prompt change to it.

Do **not** run the full live suite to warm up. It is 6-63 minutes depending on NVIDIA contention
(see Decisions 2026-07-31) and it costs real rate budget. Run it before handover, not before work.

**Story 1.3 is the Resume Analyst, and its contract is already written:**
`docs/specs/agents/AGENT-RESUME-ANALYST-SPEC.md`. **That spec is the authority** — output schema,
the four-level rubric, all eight golden cases, and the assertions each must make. Do not redesign
it; implement it. Read it before writing a line of prompt.

**The three things in that spec that matter most, because they are what make it falsifiable:**

1. **Every entry in `scope_evidence` and `notable_outcomes` must appear verbatim in the input
   resume.** A fabricated quote fails the case. This is the single most important assertion.
2. **`level_rationale` must contain a verbatim substring of 8+ words from the input.** That is how
   "cites specific resume content, not generic praise" stops being a matter of opinion.
3. **Golden cases 5-8 are the ones with teeth** (title/scope mismatch, founder, duties-without-
   outcomes, engineer in transition). An agent that nails the four clear levels and is confidently
   wrong on every ambiguous one is the exact failure this product cannot afford. Ambiguous cases
   assert a *set* of acceptable levels plus a populated `low_confidence_fields`, never one level.

**Budget the time. 1.3b is the heaviest LLM story in the phase.** Eight cases across two models is
16+ structured calls per run, and the spec requires running enough times to observe a retry
actually fire. At the bad end of the contention range that is hours. **Run golden cases as their
own `make golden AGENT=resume_analyst` target, never inside the full suite.**

**1.3b's scope is a pure function, not a graph node.** `analyse_resume(resume_text, *, role)` takes
text and returns a parsed `ResumeAnalysis`. The spec's §1 side effects — the two `agent_events` rows
and the `resumes.profile` write — belong to the `level_candidate` **node in story 1.4**. The golden
cases call `analyse_resume` directly with no session and no database, so a DB call inside it breaks
all eight. It must also **assert `resume_text` is non-empty and fail loudly** (spec §7, row 1).

**The spec asks 1.3 to settle an open question, so do not skip it:** run the golden set against
BOTH `deep` and `fast` and record both. ARCHITECTURE §4 assigns `deep`, but `fast` is 10/10 on
structured output where `deep` is 7-9/10 and up to 3x slower. Nobody has ever measured *quality*.
If `fast` matches `deep` on cases 5-8, change the assignment and let Phase 2 inherit the finding.

**Story 1.4 next:** `level_candidate` → `confirm_level`, the first real `interrupt()`.
`confirm_level` contains **only `interrupt()` and its return** — no LLM call, no counter, no write
above that line. The single-call assertion goes against **`app/llm.py`'s call log**, never against
state; LangGraph discards the state writes of a node that interrupted, so a doubled call leaves
counters looking correct. See Decisions 2026-07-30.

**Story 1.6a is DONE** — shell, silent anonymous sign-in, upload surface, 33 vitest tests. The
browser Supabase client is installed and working. **Story 1.6b carries four things that are easy
to lose:**
- **No persona header.** The interviewer name is deferred to Phase 3; "Maya Chen" is in the register
  v1 §7 bans. Decided 2026-07-31.
- **Realtime is unproven under the new RLS policies.** `agent_events` has a scoped SELECT policy and
  Supabase Realtime applies RLS per subscriber. It *should* work. Nothing has tested it. **This is
  the single riskiest unknown left in the phase** — prove it with a real subscriber and a real
  second identity, not by reading the policy.
- **Fix the session-per-upload defect 1.6a left**, recorded under Decisions 2026-07-31. Every upload
  attempt currently calls `POST /session`, so a rejected scanned PDF plus a retry orphans a row.
  One candidate journey should be one session. Hoist it once 1.4 has settled the session lifecycle.
- **`.mono-num` exists and nothing uses it yet.** Story 1.5 defined it for "mono for every numeral";
  1.6b renders the first real numbers (the assessed level, confidence marks). Apply it to numerals
  that update, not to static prose like "up to 5MB".

**Story 1.7 deletes the Phase 0 scaffolding**, only after 1.6b is verified: `app/graph/skeleton.py`,
`tests/test_interrupt.py`, `test_api.py`'s skeleton tests, `frontend/src/HealthCheck.tsx`, and the
`/skeleton/*` routes. ~~The Vite starter content in `App.tsx`~~ — **already gone, removed by 1.6a**,
which had to replace it to mount the real shell. **`HealthCheck.tsx` is still mounted and must stay
until 1.6b is verified**; it is the working reference for backend connectivity. **Do not delete**
`config.py`'s validation, the lifespan checkpointer, the CORS setup, or anything in
`tests/conftest.py`.

**Keep every agent calling `get_llm(role)`.** Never let an agent import a client directly or
hardcode a model name. That one rule is what keeps a provider switch a six-line change — see
Decisions 2026-07-31 on LLM portability.

**Two live issues that will bite in Phase 3 if forgotten** — both under Blockers below:
`nemotron-3-nano` intermittently leaks reasoning preamble into `content` (it is the Interviewer's
model), and cold start is 32.3s (needs an external pinger before any demo).

**Redeploys are automatic** on push to `main`, for both Render and Netlify. Render only rebuilds
on changes under `backend/`, Netlify only under `frontend/`, so a docs-only commit deploys
nothing.

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

**2026-07-31 · STORY 1.3 SPLIT IN TWO so the golden suite cannot be tuned to the prompt. 1.3a
writes the fixtures and assertions blind; 1.3b must make them pass without editing either.**

The hazard is specific, not theoretical: an agent writing both the fixtures and the prompt in one
pass can adjust a fixture whenever the prompt misses, and the golden suite stops being falsifiable
at the exact moment it is supposed to start gating. Since these eight cases gate **every future
prompt change to this agent**, a suite tuned to the first prompt is worse than no suite.

So 1.3a delivered a suite that is **red on purpose** — it imports `app.agents.resume_analyst`,
which does not exist — and 1.3b's brief forbids editing a fixture or an assertion. If 1.3b believes
one is wrong it must stop and report, not weaken it. Same reasoning as holding story 1.1 until
anonymous sign-in was enabled: an agent facing a failing assertion tends to weaken it until green.

Cost of the split is one extra agent. It bought the vacuity finding above, which a single combined
agent would have had every incentive not to look for.

**2026-07-31 · STORY 1.6a: a new session row is created on EVERY upload attempt. Real defect,
deliberately deferred to 1.6b rather than patched here.**

`UploadSurface.handleFile` calls `createSession()` each time a file is chosen. A candidate who
uploads a resume the backend rejects (a scanned PDF, the most likely real rejection) and then
retries leaves an orphan `sessions` row behind, with no resume and no graph thread. Repeat retries,
repeat rows.

**Deferred, not ignored, because the fix belongs where the session lifecycle is actually decided.**
Story 1.4 gives a session a graph thread and 1.6b builds the confirmation screen on top of one
session id, so hoisting session creation now would be guessing at an interface that lands two
stories from now. Written into the 1.6b brief explicitly.

**Worth taking seriously despite being small**, because this project already has a recorded case of
orphan rows nobody collects: story 1.1 found 8 orphan checkpoint threads in production from story
0.8's manual curl probes, and the lesson there was that **test teardown cleans what tests create,
and nothing cleans what real usage leaves behind.** This is that same shape, reachable by a
candidate rather than by a developer.

**2026-07-31 · STORY 1.6a struck one of story 1.7's punch-list items early, and this is correct.**

1.7 lists "the Vite starter content in `App.tsx`" for deletion. Mounting the real shell is
incompatible with leaving the starter JSX in place, so 1.6a replaced it. The agent flagged this
rather than doing it silently. **`HealthCheck.tsx` is still mounted and still must not be deleted
until 1.6 is verified** — that is the item 1.7's ordering rule actually protects, since it is the
working reference for backend connectivity.

**2026-07-31 · LLM PORTABILITY, assessed against the code rather than assumed. A model swap is an
env var; a provider swap is about six lines in one file. Do NOT build a provider abstraction.**

Karthik asked how hard it would be to leave Nemotron later. Measured by grep, not estimated:

```
files importing ChatNVIDIA under backend/app :  1   (app/llm.py, line 20)
files referencing "nvidia" under backend/app  :  2   (app/llm.py, app/config.py)
agents importing a client directly            :  0
```

**The load-bearing design decision is that agents ask for a ROLE, not a model.** `get_llm("deep")`
resolves through `_MODEL_BY_ROLE`, which reads settings. Three tiers of switch follow:

| Switch | Cost |
|---|---|
| Different model, same NVIDIA endpoint | **Change an env var.** Zero code. Re-run golden cases |
| OpenAI-compatible provider (Groq, Together, Fireworks, OpenRouter, local vLLM) | Replace the `ChatNVIDIA(...)` constructor at `llm.py:239-243` with `ChatOpenAI(base_url=...)`. One file. Plus the env-var rename, which triggers the `backend/scripts/` grep rule |
| Anthropic / Gemini | Same single constructor swap — they are all LangChain `BaseChatModel`s with the same `invoke` / `with_structured_output` surface |

Roles resolve independently, so **mixed providers per role is already possible** with no change.

**What is not free, stated honestly.** Golden cases are the real switching cost and that is the
point — ~48 fixtures once all six agents exist, and re-running them is what makes a switch
falsifiable instead of "seems fine". The retry wrapper's justification is Nemotron-specific (it
exists because `deep` returns `None` rather than raising), so a provider with native strict schema
would make it near-dead code and every claim resting on the 7-9/10 figure would need re-measuring.
Prompts tuned around Nemotron's reasoning-preamble leak may not transfer. `reasoning_effort` is a
Nemotron-specific enum, currently used nowhere — keep it that way as long as possible. And two
constraints are provider-shaped rather than code-shaped: the 40 RPM ceiling, and free-tier-only.

**Decision: change nothing now.** There is no second caller for a provider abstraction, and the role
indirection already buys the flexibility. **The one rule to enforce in every future agent brief:
agents call `get_llm(role)` and never import a client or hardcode a model name.** That single rule
is the entire difference between a six-line switch and a six-file one. Cosmetic only:
`LoggingChatNVIDIA` and `llm.py`'s docstring are vendor-named, rename at swap time.

**2026-07-31 · STORY 1.2 DEVIATES FROM ARCHITECTURE §1: the resume is uploaded THROUGH Render, not
direct to Storage via a signed URL. Deliberate, and I think §1 is wrong here.**

ARCHITECTURE §1 says "Direct upload via signed URL. The file never touches Render — routing
multi-MB PDFs through a 512MB process is wasted compute." My story-1.2 brief specified a
backend-proxied `POST /session/{id}/resume` without noticing the conflict; the agent caught it and
flagged it, correctly.

**Kept, because §1's reasoning does not survive the no-text-layer requirement.** Acceptance for
this story is that a scanned PDF is *rejected*, and that decision needs `pypdf`, which runs on the
backend. With a direct browser upload the file lands in Storage first, Render must then download it
to extract text, and a rejected scan leaves an orphan object to clean up. **The bytes cross Render
either way — direct upload just adds a round trip and an orphan.** It would also require storage
write policies for the browser, which is new attack surface on a bucket that currently has none.

The compute argument is also small at real sizes: ARCHITECTURE's own estimate is ~200KB per resume
against Render's 512MB. The 5MB cap chosen here (no number was specified anywhere) is headroom, not
a real ceiling.

**Revisit only if resumes get large or uploads get frequent.** Neither is true at single-candidate
scale. ARCHITECTURE.md deliberately not edited, per the rule that decisions supersede it.

**2026-07-31 · STORY 1.2 SHIPPED THREE EM-DASHES INTO CANDIDATE-FACING COPY. Now fixed, and the
rule is a test instead of a hope.**

Found by grepping user-facing strings during re-verification, not by any test. All three were in
`resume.py`'s upload errors, including the scanned-PDF message a real candidate is most likely to
see:

```
"This PDF has no extractable text — it looks like a scanned or image-only document."
"Unable to read this PDF — the file may be corrupted."          (x2)
```

**The instructive part: the function's own docstring says "the message is written for the candidate
reading it, not a developer."** The author knew the strings were candidate-facing, and the em-dash
ban still did not survive contact. A rule that is stated in three documents and violated anyway is
a rule that needs a test.

`backend/tests/test_user_facing_copy.py` now AST-walks `backend/app/` and fails on an em-dash or
en-dash inside any `HTTPException(...)` or `*Error(...)` message. **Deliberately narrow** — it skips
docstrings and comments, which the rule exempts, and skips developer-facing exceptions
(`NotImplementedError`, `ConfigError`, `StructuredOutputError`) by name. It carries a
`test_the_check_finds_real_user_facing_strings` guard so an AST walk that silently matches nothing
cannot make the whole file vacuously green, and it was falsified by reintroducing an em-dash and
watching it fail.

**2026-07-31 · Full live suite duration swings between ~6 minutes and ~63 minutes. Same tests, same
code. Plan story 1.3 around this.**

Three measurements of the same suite today:

```
67 tests   382.61s  (0:06:22)     my run, story 1.1
85 tests  3765.07s  (1:02:45)     agent's run, story 1.2      <- 10x
tests/test_llm.py alone: 481.98s (0:08:01) vs a 335.27s baseline recorded 2026-07-30
```

The story-1.2 tests account for ~40s of that hour. **This is NVIDIA free-tier contention**, and it
is consistent with DEV-STATE's earlier finding that `deep`'s median moved between 9.2s and 20.4s
inside ninety minutes. Nothing is wrong with the code.

**Consequence for story 1.3, which is the next story and the heaviest LLM consumer in the phase:**
eight golden cases across two models is at minimum sixteen structured calls per full run, and
"run it enough times to observe a retry" multiplies that. At the bad end of this range that is
hours, not minutes. Budget for it, run golden cases as their own target rather than inside the
full suite, and **do not read a slow run as a broken agent.**

**2026-07-31 · STORY 1.1: an unauthorised UPDATE or DELETE through PostgREST returns HTTP 200, not
403. Assert on the DATABASE, never on the status code.** This is the CORS trap of 2026-07-30
wearing different clothes, and it will silently encode a false pass in Phase 3 if forgotten.

With no UPDATE/DELETE policy, RLS makes the `USING` clause match zero rows, so the statement
succeeds against nothing. PostgREST reports that as success. Observed, with ground truth read back
through the service role after each call:

```
A PATCH  Bs session   -> status 200, body=[]
  GROUND TRUTH -> session=ORIGINAL  turns=1
A DELETE Bs turns     -> status 200, body=[]
  GROUND TRUTH -> session=ORIGINAL  turns=1
A DELETE Bs session   -> status 200, body=[]
  GROUND TRUTH -> session=ORIGINAL  turns=1
```

**B survived completely unchanged.** The empty `body=[]` is the real signal, since `Prefer:
return=representation` returns the affected rows and there were none. A test asserting
`status != 200` on these would fail against correct code and invite someone to "fix" working
security. Two calls DO return 403 and are worth knowing as the contrast: inserting into a table
with no INSERT policy, and creating a session owned by another uid (`42501`, the `with check`
firing).

**2026-07-31 · STORY 1.1: 8 orphan checkpoint threads / 32 rows found in production. NOT a test
regression — they are story 0.8's manual curl probes, and nothing was ever going to clean them.**

Found while checking residue after the full suite. Story 0.7 recorded `(0, 0)` before and after a
full run, so this looked like a regression at first. It is not: **two of the eight thread_ids
appear verbatim in this file's own story 0.8 output** — `23caf429-...` was the phase-gate curl and
`83a73411-...` was the full-chain probe, both driven by hand against the deployed Render URL. The
0.7 measurement predates them.

**The gap is structural, not a bug: test teardown cleans what tests create, and manual production
probes are not tests.** Cleared (32 checkpoints, 32 blobs, 80 writes), `checkpoint_migrations` left
intact as always. Worth remembering before any demo — hand-driving the deployed service leaves
state that nothing collects.

**2026-07-31 · STORY 1.5: `strokeWidth 1.5` is NOT implementable in Phosphor. It has no such prop.
CLAUDE.md and ARCHITECTURE §8 both specify something the mandated library cannot do.**

The agent contradicted its brief here and was right. Verified independently rather than taken on
its word:

```
grep -rl 'strokeWidth' node_modules/@phosphor-icons/react/dist/   ->  no matches, anywhere
IconContext accepted props                                       ->  color?  size?  weight?  mirrored?
icon geometry                                                    ->  filled <path d="..."/>, viewBox "0 0 256 256"
```

Phosphor icons are **filled path geometry, not stroked paths** — the weight is drawn into the
outline, so there is nothing for a stroke width to apply to. `strokeWidth` is `lucide-react`'s API,
and lucide is the library three separate skills tell us not to use. The instruction was written by
analogy to the library we deliberately rejected.

**Resolved as `weight: "regular"` set globally through `IconContext`**, in
`frontend/src/lib/icons.tsx`. Phosphor documents `regular` as its 1.5px-stroke-at-24px-viewBox
weight, which is consistent with the 256 viewBox (16/256 × 24 = 1.5) and is the faithful reading of
the intent. **CLAUDE.md § Design updated**; ARCHITECTURE §8 deliberately left alone, per the rule
that decisions supersede it rather than rewriting its history.

**2026-07-31 · STORY 1.5: `ease-standard` is a working utility and `duration-standard` is not.
Tailwind v4 has no `--duration-*` theme namespace, and the failure is silent.**

Found by re-verification, not by the agent. `--ease-*` is a real v4 theme namespace so
`ease-standard` emits; the duration utility takes a bare number (`duration-150`), so a token named
`--duration-standard` generates **no class at all**. An element written `duration-standard` gets no
transition duration and no error — it just does not animate.

The tokens are emitted as custom properties and are usable, through a different syntax:

```
--duration-fast:.15s   --duration-standard:.18s              <- present in the built CSS
.duration-\(--duration-standard\){transition-duration:var(--duration-standard)}   <- works
.duration-standard                                            <- never generated
```

**Use `duration-(--duration-standard)`, never the bare form.** Documented in `index.css` at the
token, and guarded by a test that greps all of `frontend/src` — it will fail story 1.6 if anyone
writes the bare form.

**That guard was falsified in three directions before being trusted**, per the story 0.6 precedent:
it passes clean at 25, fails with `['__bad.tsx']` against a planted bare `duration-standard`, and
stays green against the correct `duration-(--duration-standard)` form. Its first two drafts were
both wrong in the same way the agent's own tests had been — `\bduration-fast\b` matches inside the
declaration `--duration-fast`, and a comment explaining the ban tripped the ban. **A regex needs a
`(?<!-)` lookbehind here, and comments must be stripped before matching.** Third time was correct.

**2026-07-31 · Phase 1 delegation shape, and three calls made before any code was written.**

Wave plan: **1.1 + 1.5 in parallel** (disjoint: backend SQL and tests vs frontend CSS and fonts),
then **1.2 + 1.3**, then **1.4**, then **1.6**, then **1.7 inline**. Two constraints shaped it.
`frontend/package.json` is a collision point — 1.1 would want `@supabase/supabase-js` while 1.5
wants Geist and Phosphor, so **the browser Supabase client was moved into story 1.6** and 1.1 is
backend-and-SQL only. And **no two agents run live LLM tests concurrently**: the 40 RPM ceiling is
shared, and 1.3's golden cases are the heaviest consumer in the phase.

**Karthik's call: `DESIGN.md` is generated via the `stitch-design-taste` skill**, not hand-written,
and lives at the repo root rather than in `docs/`. Every later phase's UI is built against it.
Where the skill's output conflicts with ARCHITECTURE §8, **§8 wins** and the conflict gets recorded.

**Karthik's call: the interviewer persona name is deferred to Phase 3, so story 1.6 ships NO
persona header.** "Maya Chen" sits in the register v1 §7 bans and the architecture wireframes are
riddled with it, so the constraint is written into the 1.6 brief explicitly rather than left to be
noticed. Deferring costs nothing here — Phase 1 has no interviewer.

**Orchestration call, not in the spec: vitest is installed in story 1.5, not 1.6.** The spec's test
table says only "this phase installs it" without assigning a story. Putting it in the foundation
means `make test` stops failing on its `test-web` leg a story earlier, and 1.6 gets a working
runner instead of having to build one. Its first test is a real guard rather than a smoke test: it
reads `index.css` and asserts every §8 token value, no serif family, and no `lucide-react`.

**2026-07-30 · STORY 0.7: the Windows event-loop guard in `app/main.py` does NOT do what the
2026-07-30 entry below implies. `--reload` is what makes `make dev-api` work.**

The earlier entry says the swap is "needed anywhere `AsyncPostgresSaver` is used locally" and that
stories 0.6 and 0.7 would hit it "when the graph is wired into FastAPI". Both true. What was
wrong was the implied fix: a guarded swap at the top of `app/main.py` does not rescue
`uvicorn app.main:app`. Reproduced directly:

```
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8011
  psycopg.InterfaceError: Psycopg cannot use the 'ProactorEventLoop' to run in async mode.
  ERROR:    Application startup failed. Exiting.

make dev-api  (uvicorn app.main:app --reload)
  POST /skeleton/start HTTP/1.1" 200 OK
```

**Why:** uvicorn's `Server.run()` calls `asyncio.run()`, which creates the loop under whatever
policy is active **before `app.main` is imported**. The guard therefore executes inside a
coroutine on a loop that already exists — too late. `--reload` works by a different mechanism
entirely: it spawns a child process and runs uvicorn's own `asyncio_setup()` there, before the
child's `asyncio.run()`. Nothing in `app/main.py` participates.

**The guard is kept** because `app.main` is also imported directly, outside uvicorn's CLI, where
it runs before any loop exists — and it is harmless otherwise. **It is not load-bearing, and the
comment above it now says so.** `tests/test_api.py` launches its subprocesses as
`python -c "<set policy>; import uvicorn; uvicorn.run(...)"` for the same reason.

**Production is unaffected:** Render is Linux, where the selector loop is already the default, so
a plain `uvicorn app.main:app` start command in story 0.8 is fine. The trap is local only, and it
is the *developer* who hits it.

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

~~**2026-07-31 · BLOCKS STORY 1.1: anonymous sign-in is disabled.**~~ — **RESOLVED 2026-07-31.**
Karthik enabled it (Authentication → Sign In / Providers → Allow anonymous sign-ins). Verified
against the live endpoint rather than trusting the toggle, and two distinct identities were minted
end to end:

```
identity A: status 200 | is_anonymous=True | role=authenticated | id=4cfedd11-...
identity B: status 200 | is_anonymous=True | role=authenticated | id=28b2d874-...
two DISTINCT identities: True
A token claims -> role: authenticated | sub: 4cfedd11-... | is_anonymous: True
```

**THE FINDING THAT CHANGES STORY 1.1: anonymous users carry the `authenticated` role, not `anon`.**
Supabase's own dashboard warns about this in an amber callout. So every policy must be written
`to authenticated` — and `authenticated` is exactly the role that already holds default table-level
grants on all six tables. A policy written `to anon` does nothing at all, and a test that probes
the `anon` role passes while the real browser path stays open. Both mistakes are silent.

Probe users deleted immediately afterwards with the admin API; `auth.users` confirmed back to
**0 rows**. Anonymous users are never garbage-collected by Supabase, so anything that mints them
must delete them.

**Deferred, deliberately, to Phase 7:** Supabase recommends CAPTCHA on anonymous sign-ins, since
the endpoint creates a database row without authentication and can be abused to bloat MAU. Correct
call for a project with no public traffic, but it is a real hole and it is recorded here rather
than left unnoticed.

The original blocking evidence, kept because it explains why the story was held:

```
status 422
{"code":422,"error_code":"anonymous_provider_disabled","msg":"Anonymous sign-ins are disabled"}
```

It is a dashboard toggle — Authentication → Sign In / Providers → **Anonymous Sign-Ins** — and no
migration or script can flip it. **This blocks more of 1.1 than it appears to.**
`sessions.user_id references auth.users`, so the cross-session denial test cannot insert its two
fixture sessions at all without two genuine `auth.users` rows, which is exactly what anonymous
sign-in mints. The story was held rather than started, deliberately: an agent facing failing auth
calls tends to weaken the assertion until it goes green, and this is the one story in the phase
where a weakened assertion is silent and serious.

Re-probe with the snippet above before starting 1.1. Expect `200` and
`is_anonymous = True`.

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

**`nemotron-3-nano` leaked reasoning preamble into `content` — observed once, in story 0.7's
live `/skeleton/start` response. Worth closing before Phase 3, because nano is the Interviewer.**

Prompt was "Ask a product manager one short opening interview question. Reply with the question
only, in one sentence." What came back, verbatim:

```
"We are to ask a short opening interview question for a product manager, and reply with only
 the question in one sentence.\n The question should be concise and serve as an opening...\n
 Example: \"Can you walk me through a product you've launched that you're most"
```

Deliberation in the content field, then truncated mid-sentence by the skeleton's
`max_tokens=120`. **A candidate would have seen all of it.**

**Update after two more samples from the deployed service: it is INTERMITTENT, which is worse
than consistent.** Same prompt, same model, three observations — two leaked preamble, one came
back clean (`"What's one product decision you made that surprised"`). A failure that happens
sometimes will survive casual testing and appear in front of a candidate. Caveat still stands
that the skeleton prompt is deliberately minimal, with no system message and no few-shot.

**But do not assume prompt engineering alone fixes it.** The Interviewer's question is the most
user-visible string in the product, and the streaming mitigation under discussion for the 7-9s
latency would stream this preamble token by token. Options if it persists: a system message
constraining the output shape, structured output for the question (already mandatory-retry, and
nano is 10/10 there), or `reasoning_effort` — the enum is known, and `none`/`minimal` exist. Test
in Phase 3 before choosing.

~~Production checkpoint latency is unmeasured.~~ — **RESOLVED 2026-07-30 by the deploy.**
A full resume step (one checkpoint read plus the node's writes) costs **~27ms** from
Render-Singapore to Supabase-Singapore; a single read is not distinguishable from noise. The
298ms figure was a dev-machine artefact. Output under § 0.8. **Quote 27ms, not 298ms.**

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

**PRODUCTION — live since 2026-07-30, all free tier, all Singapore.**

| | |
|---|---|
| Frontend | `https://pmaiinterviewpanel.netlify.app` — Netlify project `pmaiinterviewpanel` |
| Backend | `https://pm-interview-panel.onrender.com` — Render service `PM-interview-panel` |
| Database | Supabase `tnqfqsocoqythakwybsw` |
| Repo | `https://github.com/karthikr0208/PM-interview-panel` |

**Render:** root dir `backend` · build `pip install -r requirements.txt` · start
`uvicorn app.main:app --host 0.0.0.0 --port $PORT` · region **Singapore** · `PYTHON_VERSION`
3.12.10, matching the committed `backend/.python-version`. All 11 `REQUIRED_VARS` set in the
dashboard, never committed. `ALLOWED_ORIGINS` is the Netlify origin **only** — adding anything
wider fails story 0.8's acceptance.

**Netlify:** base dir `frontend` · build `npm run build` · publish `frontend/dist` ·
`NODE_VERSION=22` · `VITE_API_URL` set to the Render URL, plus `VITE_SUPABASE_URL` and
`VITE_SUPABASE_ANON_KEY` (**publishable key only — never `sb_secret_`, it bypasses RLS and every
`VITE_` variable ships readable in the browser bundle**).

**Both redeploy automatically on push to `main`**, and each only rebuilds when its own directory
changes, so a docs-only commit deploys nothing.

**Measured in production, 2026-07-30:** checkpoint step **~27ms** · cold start **32.33s** after
~18 min idle, warm 0.13s.

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

**Added in story 1.2 (2026-07-31):** `python-multipart==0.0.20` — **FastAPI cannot accept an
`UploadFile` without it**, so this was a hard blocker, not a nicety. `httpx==0.28.1` moved from the
`# Dev` block to `# Core`: it is now a runtime dependency, since `app/supabase_client.py` talks to
Supabase Auth, PostgREST and Storage over raw HTTP. **No Supabase Python client was added** — that
would have pulled five transitive packages in for one upload call. **No new environment variables**;
everything needed was already in `REQUIRED_VARS`.

**Added in story 1.6a (2026-07-31):** `@supabase/supabase-js` 2.111.0 (dependency) ·
`@testing-library/react` 16.3.2 and `jsdom` 30.0.1 (devDependencies). `vite.config.ts`'s test
`environment` moved **`node` → `jsdom`**, which component tests need; story 1.5's 25 tests were
re-run under the new environment and all still pass. **No new environment variables** —
`VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` already existed in both `.env` files and are now
read by code for the first time, which is what gets them inlined into the bundle.

There is no global vitest setup file, so `@testing-library/react` does not auto-clean the DOM
between tests; the test files call `afterEach(cleanup)` themselves. Worth knowing before adding a
third test file that assumes otherwise.

**Added in story 1.5 (2026-07-31):** `@phosphor-icons/react` 2.1.10 (dependency) · `vitest` 4.1.10
(devDependency) · Geist + Geist Mono variable `woff2` vendored into `frontend/src/assets/fonts/`
from the `geist` npm package, OFL licence kept beside them. `test: "vitest run"` added to
`package.json`, and a `test` block to `vite.config.ts` (`environment: 'node'`). Test files are
excluded from `tsconfig.app.json` and typed by a separate `tsconfig.vitest.json` — `src/` is typed
browser-only, so a test importing `node:fs` breaks `tsc -b` without that split.

**`make test-web` works from 2026-07-31 and `make test` no longer fails on its second leg.**
The design tokens live in `frontend/src/index.css` and are guarded by `src/index.css.test.ts`,
which asserts every ARCHITECTURE §8 hex value. **`DESIGN.md` at the repo root is the design
authority for every later phase**, generated via `stitch-design-taste` and reconciled against §8;
its § 8 lists every skill directive that was overridden and why.

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
  **But it does NOT rescue `uvicorn app.main:app`** — that path creates its loop before importing
  the module, so the guard runs too late and startup fails. `make dev-api` works only because
  `--reload` makes uvicorn fix the policy itself. Corrected 2026-07-30, see Decisions; do not read
  the guard in `app/main.py` as protecting you.
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
