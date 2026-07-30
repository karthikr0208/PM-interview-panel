# Phase 0 — Walking Skeleton

**Goal:** prove the riskiest infrastructure works, end to end, on deployed services, before a
single agent exists.

**Why this phase exists.** Four things in this stack could invalidate architectural decisions,
and all four are cheap to test and expensive to discover late: whether structured output is
reliable on NVIDIA's free hosted endpoint, whether the Supabase connection works from Render at
all, whether `interrupt()` genuinely resumes across separate HTTP requests, and what the account's
actual rate model is. Nothing here is product functionality. All of it is de-risking.

**Done when:** a deployed Render endpoint runs a two-node graph that pauses on `interrupt()`, and
a second HTTP call to that deployed URL resumes it from a Supabase checkpoint. Demonstrated with
two `curl` invocations and their output.

---

## Stories

### 0.1 Repo scaffold — ✅ DONE 2026-07-30

Backend and frontend skeletons, environment handling, no application logic.

Observed output for every box is in `DEV-STATE.md` § Last session. Delivered beyond the boxes:
`config.py` also rejects the 6543 transaction pooler and the IPv6-only direct-connection host,
and the pre-commit hook lives in tracked `.githooks/` via `core.hooksPath` so it survives a clone.

```
backend/
  app/main.py            FastAPI app, /health, CORS
  app/config.py          env loading, fail loudly on missing keys
  app/llm.py             ChatNVIDIA client factory
  app/graph/state.py     InterviewState TypedDict
  app/graph/build.py     graph construction + compile
  scripts/init_db.py     checkpointer.setup(), run once
  requirements.txt
frontend/
  (Vite + React + TS scaffold, Tailwind configured)
Makefile
.env.example
```

**Acceptance**
- [x] `make dev-api` serves `GET /health` returning `{"status":"ok"}`
- [x] `make dev-web` serves the Vite dev server
- [x] `.env.example` lists every required variable; `config.py` raises a clear error naming any that is missing
- [x] Secrets are gitignored; `.env` is never committed

---

### 0.2 NVIDIA smoke test — ✅ MOSTLY DONE 2026-07-29

Done ahead of the phase, and it changed the model choice. Scripts live in `backend/scripts/`:
`probe_latency.py`, `probe_models.py`, `probe_candidates.py`, `probe_structured.py`.

Settled: GLM 5.2 queues ~230s on the free tier and is out. `nemotron-3-nano-30b-a3b` (fast) and
`nemotron-3-super-120b-a12b` (deep) both do 3/3 strict `json_schema`, 2–4s. `thinking` is
GLM-only and does not exist on Nemotron. Catalog listing does not imply availability. Full data
in `DEV-STATE.md` § Decisions.

**Remaining**
- [ ] Same structured-output check through **`ChatNVIDIA`**, not the raw OpenAI client — the probes used raw HTTP. `with_structured_output()` must return a valid Pydantic instance 10/10.
- [ ] Streaming through `ChatNVIDIA` yields incremental chunks
- [ ] Re-measure latency **at a different time of day**. All measurements so far are from one ~23:00 IST window; contention is time-varying and the whole model decision rests on it.
- [ ] **Rate-limit logging starts here** — every LLM call timestamped from the first call written, not retrofitted.

**Decision gate.** If `ChatNVIDIA` cannot pass `response_format: json_schema` through, either use
`with_structured_output()` (which routes via tool calling) or drop to the raw OpenAI client for
structured calls. Record whichever, because it changes every agent's implementation.

---

### 0.3 Confirm the account model — ✅ DONE 2026-07-29

Resolved before the phase started. The account dashboard shows **up to 40 RPM and no credit
balance** — pure rate limiting, no exhaustible budget. The official model page confirms 1M
context, 753B parameters, and Function Calling / Structured Output / Reasoning all
**Supported**.

Remaining work folded into 0.1: **a pre-commit hook that blocks any commit containing the
`nvapi-` key prefix.** The first key was leaked via screenshot and rotated; the hook makes
that failure mode structural rather than a matter of care.

---

### 0.4 Supabase project and schema

**Acceptance**
- [ ] Project created; **session pooler** connection string (port 5432) recorded in `.env`
- [ ] All six tables from `ARCHITECTURE.md` §5 created via a checked-in migration
- [ ] RLS enabled on every table with permissive `session_id`-scoped policies
- [ ] `agent_events`, `answer_evaluations`, `transcript_turns` added to the `supabase_realtime` publication
- [ ] Storage bucket `resumes` created
- [ ] The `check (length(evidence_quote) > 0)` constraint is present and verified by attempting an empty insert

---

### 0.5 Checkpointer

**Acceptance**
- [ ] `AsyncPostgresSaver` connects over the session pooler from local development
- [ ] `scripts/init_db.py` runs `.setup()` and is idempotent on a second run
- [ ] LangGraph's `checkpoints` / `checkpoint_writes` / `checkpoint_blobs` tables exist alongside the app tables with no collision

**Explicitly verify the failure mode.** Attempt one connection over the **transaction** pooler
(port 6543) and confirm it produces `DuplicatePreparedStatement`. Record the observed error in
`DEV-STATE.md` § Environment notes. Knowing the symptom by sight is worth two minutes now and
saves an hour when it appears in Phase 3 for an unrelated reason.

---

### 0.6 Two-node graph with interrupt

Minimal and deliberately not the real graph.

```python
class SkeletonState(TypedDict):
    messages: Annotated[list, add_messages]
    turn_count: int

# ask_something   → one LLM call, appends a message, increments turn_count
# await_reply     → contains interrupt() and its return. NOTHING ELSE.
```

**Acceptance**
- [ ] Graph compiles with the Postgres checkpointer attached
- [ ] `ainvoke` runs to the interrupt and returns a result containing `__interrupt__`
- [ ] `ainvoke(Command(resume="..."), config)` resumes; `interrupt()` returns the passed value
- [ ] A checkpoint row exists in Postgres after **each** node — verified by querying the table directly, not inferred
- [ ] **Idempotency test:** the LLM call in `ask_something` fires exactly once across a full interrupt-and-resume cycle. Assert on the call log from 0.2.

That last checkbox is the one that matters. It is the structural constraint the whole conduct
loop depends on, and it is cheaper to prove here than to debug in Phase 3.

---

### 0.7 Interrupt/resume across separate HTTP requests

Local, before deployment.

**Acceptance**
- [ ] `POST /skeleton/start` returns the interrupt payload and a `session_id`
- [ ] `POST /skeleton/resume` with that `session_id` continues the graph
- [ ] **The API process is restarted between the two calls** and resume still works — this is the actual test. Nothing may live in process memory.
- [ ] `graph.get_state(config)` returns the correct `.next` for a paused session

---

### 0.8 Deploy

**Acceptance**
- [ ] Backend on Render free tier, **region: Singapore** — not the default. The Supabase project is in `ap-southeast-1`; a mismatched region adds ~100ms to every one of the ~8 database round trips per candidate turn. See DEV-STATE § Decisions.
- [ ] `/health` green
- [ ] Frontend on Netlify; `VITE_API_URL` set at build time
- [ ] CORS allows the Netlify origin and nothing wider
- [ ] Environment variables set in the Render dashboard, not committed
- [ ] **The 0.7 test passes against the deployed URL**, with the two `curl` invocations and their output pasted into `DEV-STATE.md`
- [ ] Cold-start latency measured after 15+ minutes idle and recorded as an actual number

---

---

## Automated tests

Written alongside the stories, not after. `make test-api` must pass before the phase is handed
over. No golden cases in this phase — there are no agents yet.

| File | Asserts |
|---|---|
| `tests/test_config.py` | Missing env var raises an error naming the variable |
| `tests/test_llm.py` | Completion returns text · streaming yields >1 chunk · `with_structured_output` returns a valid instance **10 consecutive times** (parametrized, records the pass rate) · every call is logged with a timestamp |
| `tests/test_checkpointer.py` | `.setup()` is idempotent on second run · a checkpoint row exists in Postgres **after each node**, queried directly · `thread_id` isolation: two sessions do not see each other's state |
| `tests/test_interrupt.py` | `ainvoke` returns `__interrupt__` when paused · `Command(resume=x)` makes `interrupt()` return `x` · **the LLM call in `ask_something` fires exactly once across a full interrupt-and-resume cycle** · `get_state().next` is correct while paused |
| `tests/test_api.py` | `/health` returns ok · start returns a `session_id` and interrupt payload · resume continues the graph · **resume succeeds after the app object is torn down and rebuilt** (nothing in process memory) · CORS rejects an unlisted origin |

**The load-bearing assertion is the single-LLM-call test in `test_interrupt.py`.** It is the
structural constraint the entire conduct loop depends on, and it is far cheaper to prove here
than to debug in Phase 3.

`test_llm.py` hits the real NVIDIA endpoint and is marked `@pytest.mark.live` so it can be
deselected. It is not mocked — mocking it would defeat the entire purpose of this phase, which
is finding out what the real endpoint actually does.

---

## Phase gate

Do not start Phase 1 until every box above is ticked and these hold:

1. `make test-api` passes, with output pasted into `DEV-STATE.md`.
2. Two `curl` calls against the **deployed** Render URL demonstrate interrupt and resume, with output recorded.
3. Structured-output reliability is a measured number, not an assumption.
4. The NVIDIA account model question is closed.
5. Cold-start latency is a measured number.
6. `DEV-STATE.md` § Environment notes contains real observed values, including the transaction-pooler error text.

## Handoff

### Verified by me, with evidence in DEV-STATE
- `make test-api` output
- Two `curl` invocations against the deployed URL and their responses
- Structured-output pass rate (n/10)
- Latency per model — `thinking` does not exist on Nemotron, so the lever is model choice
  (nano / super / backup), not a request parameter. Two samples recorded: 2026-07-29 ~23:00
  and 2026-07-30 ~07:30.
- Cold-start latency after 15+ minutes idle
- The observed `DuplicatePreparedStatement` error text

### Needs your eyes
- ~~**The NVIDIA account model.**~~ Resolved 2026-07-29 from the account dashboard: 40 RPM, no credits.
- ~~**Supabase project setup.**~~ Done — `tnqfqsocoqythakwybsw`, Singapore, connection verified 2026-07-30.
- **Render project setup** (story 0.8), if you would rather create it yourself than have me do it
  through the CLI. **Region must be Singapore**, not the default.
- **A judgement call, if structured output scores below 10/10.** That makes prompt-validate-retry mandatory in every agent rather than defensive, which adds work to every remaining phase. Worth your decision, not mine.

Nothing in this phase is visually assessable — there is no UI yet beyond a Vite scaffold. The
first genuine design review is the Phase 1 handoff.

## Out of scope

No agents. No resume parsing. No real UI beyond the Vite scaffold. No design tokens — those
belong to Phase 1 alongside the app shell. The temptation to start building the real graph here
should be resisted; this phase is disposable scaffolding whose only job is to prove the
infrastructure before anything is built on top of it.
