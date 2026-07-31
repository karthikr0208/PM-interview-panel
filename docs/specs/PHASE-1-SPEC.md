# Phase 1 — Resume Analyst and the design foundation

**Goal:** a candidate uploads a real resume and sees a real assessed level they can correct,
rendered in the real design system, with the database no longer wide open.

**Why this phase exists.** Phase 0 proved the infrastructure with a disposable graph. This is the
first phase where a human sees output and where a mistake has consequences beyond a failed test.
Four things make it the right next slice:

1. **The database is currently unreadable by browsers, deliberately.** Phase 0 ships RLS with zero
   policies. Nothing on the frontend can read anything until anonymous sign-in and scoped policies
   exist. Every later phase is blocked on this, so it goes first.
2. **`confirm_level` is the first real `interrupt()`** — the constraint Phase 0 proved in a
   throwaway graph now carries a candidate's actual correction.
3. **The Resume Analyst is the first agent**, so it is where golden cases, agent specs, and the
   `deep` model's 7-9/10 structured-output reliability stop being theory.
4. **It is the first visually assessable phase.** The design foundation laid here governs
   everything after it, and is expensive to change later.

**Done when:** a candidate visits the deployed Netlify URL, uploads a PDF or DOCX resume, watches
the Resume Analyst work in the orchestration column, and confirms or corrects an assessed level
that is then persisted — with session A provably unable to read session B's data.

---

## Stories

Ordered by dependency. 1.1 blocks everything on the frontend; 1.7 must not start before 1.6 is
verified.

### 1.1 Anonymous sign-in and scoped RLS policies — ✅ DONE 2026-07-31

**The security story. Do it first and do it carefully.** This is the only story in the phase where
a mistake is silent and serious.

The trap, recorded in DEV-STATE 2026-07-30 and worth restating because reasoning about it gives
the wrong answer: `anon` and `authenticated` **already hold table-level `SELECT`/`INSERT`/
`UPDATE`/`DELETE` grants** on all six tables, because Supabase adds them by default in `public`.
Grants control whether a table is *reachable*; RLS controls which *rows* come back. Today RLS
denies everything because there are no policies. **The first policy added is what opens the door,
and the grants are already open behind it.** A single over-broad policy exposes every candidate's
transcript and scores at once.

`sessions.user_id` is nullable and already exists, so no schema change is needed to support this.

**Acceptance**
- [x] Supabase anonymous sign-in enabled; the browser obtains a token with no signup screen and no visible step. **Anonymous users carry the `authenticated` role, not `anon`** — every policy targets `authenticated`
- [x] `sessions.user_id` populated with `auth.uid()` on creation — enforced at the database by the INSERT policy's `with check`; a session owned by another uid is rejected `42501`. **Route-level wiring lands in 1.2**
- [x] Policies on all six app tables scope rows to the owning session's `user_id`, via a join to `sessions` rather than repeating the claim on every table
- [x] **Cross-session denial proven empirically**, on all six tables, with real JWTs through PostgREST — and re-proven independently with a from-scratch probe. `A/own = 1` asserted alongside, so the denial cannot pass vacuously
- [x] The service role still bypasses everything, so the backend is unaffected
- [x] **LangGraph's four `checkpoint%` tables keep zero policies.** Confirmed by direct `pg_policies` query, independently of the test
- [x] `resumes` storage bucket stays private; the browser never gets a public URL

**The assertion that matters is cross-session denial, not "a policy exists."** `test_schema.py`
already asserts empirical denial rather than `rowsecurity = true`, and it will fail loudly if a
policy is too permissive. Extend it rather than writing a parallel test.

---

### 1.2 Resume upload and text extraction — ✅ DONE 2026-07-31

**Acceptance**
- [x] `POST /session` creates a session row and returns its id
- [x] **`POST /session` populates `user_id` from the caller's validated JWT** (via `GET /auth/v1/user`), never from a client-supplied value. Added beyond the original boxes; without it the backend's service-role write produces sessions the candidate's own browser cannot read
- [x] `POST /session/{id}/resume` accepts PDF and DOCX, stores the file in the private `resumes` bucket, and writes `storage_path`. **Also enforces session ownership** — 403 proven with two real identities
- [x] Extracted text written to `resumes.parsed_text` via `pypdf` / `python-docx`, both already in `requirements.txt`
- [x] **A scanned or image-only PDF with no text layer fails with a clear message**, not with an empty string. Proven end to end against a real server with a genuinely text-free PDF
- [x] File size and type rejected server-side. 5MB cap, counted from bytes received rather than a client-declared `Content-Length`
- [x] Anything other than PDF or DOCX is rejected by content inspection (`%PDF-`, `PK\x03\x04`), not by file extension alone

**Deviates from ARCHITECTURE §1 deliberately:** upload is proxied through Render rather than direct
to Storage via a signed URL, because rejecting a scanned PDF requires server-side extraction and
the bytes therefore cross Render either way. See DEV-STATE § Decisions 2026-07-31.

**Added `python-multipart==0.0.20`** (FastAPI cannot accept an upload without it) and moved
`httpx` from the dev block to core. No new environment variables.

**Out of scope:** OCR. A scanned resume is told to re-upload a text PDF.

---

### 1.3 Resume Analyst agent

First agent. Its contract lives in `docs/specs/agents/AGENT-RESUME-ANALYST-SPEC.md`, **written
before the prompt**, and that spec is the authority on schema and golden cases.

Model: **`deep`**. Note ARCHITECTURE §4 assigns `deep` to this agent while DEV-STATE 2026-07-30
records that on *reliability* grounds the assignment is backwards — `deep` is 7-9/10 on structured
output where `fast` is 10/10. That is deliberately left alone until Phase 2's golden cases give a
quality signal. **This phase's golden cases are the first real data on that question; record what
they show.**

Writes `candidate_profile`, `assessed_level`, `level_rationale`, `low_confidence_fields`.

**Acceptance**
- [x] `AGENT-RESUME-ANALYST-SPEC.md` exists and defines the output schema, the level rubric, and the golden cases — written 2026-07-31, before the prompt
- [ ] `assessed_level` is one of `APM | PM | Senior PM | GPM`, enforced by the schema, not by prompt text
- [ ] `level_rationale` cites specific resume content, not generic praise
- [ ] `low_confidence_fields` names fields the model was unsure about; these drive the confirmation UI in 1.6
- [ ] **5-10 golden cases at `backend/tests/golden/resume_analyst/`, passing, runnable with `make golden AGENT=resume_analyst`**
- [ ] Validate-retry is exercised, not assumed: at least one golden case records the observed retry behaviour on `deep`

**Golden cases must span the levels**, including at least one deliberately ambiguous resume where
the correct behaviour is a populated `low_confidence_fields`, not a confident guess. A levelling
agent that is never uncertain is broken in a way that only shows up in front of a real candidate.

**Two design rules constrain this agent's prompt, not just CSS** (v1 §7, via CLAUDE.md): no
fake-round numbers and no generic placeholder names. They bind harder on the Case Architect in
Phase 2, but the profile summary this agent writes is candidate-visible.

---

### 1.4 `level_candidate` → `confirm_level`, the first real interrupt

The Phase 0 skeleton becomes the real thing. `build.py` gets its first two nodes.

**Acceptance**
- [ ] `level_candidate` runs the Resume Analyst and writes its four fields to state
- [ ] `confirm_level` **contains only `interrupt()` and its return** — no LLM call, no counter, no write above that line, ever
- [ ] A candidate's correction to the level is carried into state by the resume value and persisted to `sessions.level`
- [ ] Accepting the assessed level unchanged also works, and is distinguishable from a correction
- [ ] **The Resume Analyst's LLM call fires exactly once across the confirm cycle**, asserted against `app/llm.py`'s call log

That last box is the Phase 0 constraint doing its job for real. **Assert on the call log, never on
state.** DEV-STATE 2026-07-30 records why: LangGraph discards the state writes of a node that
interrupted, so a doubled call leaves `turn_count`-style counters looking correct. The damage is
duplicated side effects, and only the log sees them.

---

### 1.5 Design foundation — ✅ DONE 2026-07-31

Governs every phase after this one. `design-taste-frontend-v1` is the authority; v2 contributes
its AI-tells list and the em-dash ban. Dials: **VARIANCE 3 · MOTION 4 · DENSITY 6**.

**Acceptance**
- [x] Tokens from ARCHITECTURE §8 implemented as CSS variables: background, surface, border, text primary/secondary, accent `#3A63D0` light / `#6E92E8` dark, semantic success/warning/error
- [x] **Geist and Geist Mono** self-hosted. No serif anywhere. **Mono for every numeral**, so timers and counters do not jitter in width as they update
- [x] ~~**`@phosphor-icons/react`** at `strokeWidth 1.5` globally~~ → **`weight: "regular"` globally via `IconContext`.** Phosphor has no `strokeWidth` prop; verified by grep across the whole package. See DEV-STATE § Decisions 2026-07-31. No `lucide-react` anywhere, confirmed against `package-lock.json`
- [x] 4px spacing scale · radius 8px cards / 6px controls · single-layer shadows tinted to the background hue, never pure black
- [x] Transitions `cubic-bezier(0.16, 1, 0.3, 1)` at 150-200ms; `prefers-reduced-motion` respected. **`ease-standard` is a working utility, `duration-standard` is not** — use `duration-(--duration-standard)`, guarded by test
- [x] Light mode is the default. Permanent dark mode is itself a documented AI tell, and this is used at a desk in daylight
- [x] **No em-dashes in any user-facing copy.** Docs are exempt; anything a candidate reads is not
- [x] `DESIGN.md` generated via `stitch-design-taste` at the repo root, reconciled against §8
- [x] vitest installed and configured. **`make test-web` runs for the first time: 25 passed**

**Consider generating `DESIGN.md` via the `stitch-design-taste` skill** rather than hand-writing
it, per DEV-STATE Environment notes. It produces a semantic design document agents can follow,
which matters because every later phase's UI is built against it.

---

### 1.6 Upload and confirmation UI

The first real screens. Three-column shell from ARCHITECTURE §8, but only the parts this phase
feeds: the orchestration column has one agent in it, and the right column is empty.

**Acceptance**
- [x] Upload surface with **the full state cycle: idle, uploading, parsing, error**. Skeletal loaders matching the final layout, never circular spinners (v1 §3 Rule 5) — done 2026-07-31 in 1.6a. Plus a fifth `done` state, since the flow has to acknowledge completion before 1.6b's confirmation screen exists. `uploading` → `parsing` is driven by XHR's upload-progress event; `fetch` cannot detect that boundary
- [ ] Orchestration column shows the Resume Analyst with the four states distinguished **by shape as well as colour**: `○` waiting, `◉` active and pulsing, `●` done, `⚠` error
- [ ] Agent activity reads as plain language ("read your resume and assessed a level"), **never raw JSON**
- [ ] Live updates arrive via Supabase Realtime on `agent_events`, not by polling
- [ ] Confirmation screen shows the profile, the level, and the rationale, and lets the candidate correct the level
- [ ] **Fields in `low_confidence_fields` are visually marked as uncertain**, so the candidate knows what to check rather than being asked to verify everything equally
- [x] Errors read as plain language with a details disclosure, not a stack trace — done 2026-07-31 in 1.6a. The backend's own `detail` string is surfaced verbatim, because those strings are already written for the candidate
- [x] Labels sit above inputs. No placeholder-as-label — done 2026-07-31 in 1.6a
- [x] Works at ≥1280px, the design target; below that it collapses to single-column without breaking — done 2026-07-31 in 1.6a. Three columns at `xl`, stacking to one below it with the conversation first

**A decision this story forces:** ARCHITECTURE's wireframes use **"Maya Chen"** as the interviewer
persona, which sits in exactly the register v1 §7 bans. If the persona header ships in this phase,
the name must be chosen properly first. See Blockers in DEV-STATE.

---

### 1.7 Delete the Phase 0 scaffolding

Only after 1.6 is verified. Deleting earlier removes the working reference before the replacement
is proven.

- [ ] `backend/app/graph/skeleton.py`
- [ ] `backend/tests/test_interrupt.py` — its assertions now live against the real graph in 1.4
- [ ] `/skeleton/start` and `/skeleton/resume` from `app/main.py`, and their tests in `test_api.py`
- [ ] `frontend/src/HealthCheck.tsx` and its mount in `App.tsx`
- [ ] The Vite starter content in `App.tsx`

**Do not delete** `app/config.py`'s validation, the lifespan checkpointer, the CORS setup, or
anything in `tests/conftest.py`. Those are permanent.

---

## Automated tests

Written alongside the stories, not after. `make test` must pass before handover.

| File | Asserts |
|---|---|
| `tests/test_rls_policies.py` | **Two anonymous identities cannot read each other's rows**, on every table · the service role still sees everything · `checkpoint%` tables still have zero policies |
| `tests/test_resume_upload.py` | PDF and DOCX extract text · a no-text-layer PDF fails with a clear error, not an empty string · oversized and wrong-type files rejected server-side |
| `tests/test_resume_analyst.py` | Output validates against the schema · `assessed_level` is one of the four values · `low_confidence_fields` populates on an ambiguous resume |
| `tests/test_confirm_level.py` | `ainvoke` pauses at `confirm_level` · a correction reaches state and `sessions.level` · **the Resume Analyst's LLM call fires exactly once across the cycle**, asserted on the call log |
| `frontend/src/**/*.test.ts` | First vitest tests. **`make test-web` currently has nothing to run and vitest is not installed** — this phase installs it |

**Golden cases:** `backend/tests/golden/resume_analyst/`, 5-10 fixtures, `make golden`. These gate
every future prompt change to this agent.

---

## Phase gate

Do not start Phase 2 until every box above is ticked and these hold:

1. `make test` passes, both legs, with output pasted into `DEV-STATE.md`.
2. `make golden AGENT=resume_analyst` passes, with the pass rate recorded.
3. **Cross-session RLS denial is proven empirically**, with the output pasted. Not "policies exist."
4. A real resume, uploaded through the deployed Netlify URL, produces a level you agree with.
5. The design foundation is implemented, not merely specified.

---

## Handoff

### Verified by me, with evidence in DEV-STATE
- `make test` and `make golden` output
- Cross-session RLS denial, queried directly
- The single-LLM-call assertion across the confirm cycle
- Structured-output behaviour of `deep` under real resumes, including any retries observed

### Needs your eyes
- **Does the assessed level look right?** This is the first output with no objective answer. Golden cases prove consistency, not correctness. Upload your own resume and several others.
- **The first genuine design review.** Phase 0 had nothing visually assessable. Judge the shell, the type, the motion, and whether the orchestration column reads as informative or as decoration.
- **The interviewer persona name**, if the header ships this phase.
- **Whether `deep` should stay on this agent.** Phase 2 was named as the decision point, but this phase produces the first real quality signal.

## Out of scope

No Case Architect, no interview, no scoring, no coach. The right-hand evaluation column stays
empty. No OCR. No mobile redesign below 1280px beyond graceful collapse. No login, no accounts,
no session history — anonymous sign-in is an identity for row scoping, not a user account.
