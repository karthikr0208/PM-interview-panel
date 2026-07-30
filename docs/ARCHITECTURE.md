# PM Interview Panel — Architecture

**Last revised:** 2026-07-29 · **Status:** pre-implementation

> Where `docs/DEV-STATE.md` "Decisions & deviations" contradicts this document, **the deviation wins.** This document describes intent; that log describes reality.

---

## 1. System context

Three deployed surfaces. Only one holds durable state.

```
┌──────────────────────┐        ┌──────────────────────┐
│  Netlify (static)    │        │  Render (free web)   │
│  React + Vite bundle │        │  FastAPI + LangGraph │
│                      │        │                      │
│                      │──POST /turn ────────────────▶ │
│                      │◀─SSE  interviewer output───── │
│                      │        │   STATELESS          │
│                      │        │   spins down @15min  │
└──────────┬───────────┘        └──────────┬───────────┘
           │                               │
           │ Realtime (postgres_changes)   │ session pooler :5432
           │ direct upload (signed URL)    │
           ▼                               ▼
       ┌──────────────────────────────────────────┐
       │  Supabase                                │
       │  Postgres: app tables + LangGraph        │
       │            checkpoints                   │
       │  Storage:  resume PDFs                   │
       │  ← THE ONLY DURABLE STATE                │
       └──────────────────────────────────────────┘
                                    │
                                    │  HTTPS, OpenAI-compatible
                                    ▼
                        ┌──────────────────────────┐
                        │ NVIDIA NIM               │
                        │ z-ai/glm-5.2 · 40 RPM    │
                        └──────────────────────────┘
```

**Boundary crossings**

| From → To | Carries | Notes |
|---|---|---|
| Browser → Supabase Storage | Resume PDF | Direct upload via signed URL. The file never touches Render — routing multi-MB PDFs through a 512MB process is wasted compute. |
| Browser → Render | `{session_id, payload}` | Plain POST. `session_id` is the LangGraph `thread_id`. |
| Render → Browser | SSE event stream | Interviewer output and graph progress. |
| Supabase → Browser | Realtime `postgres_changes` | `agent_events` and `answer_evaluations`. Feeds the left and right columns **without touching Render**, so both keep working through a cold start. |
| Render → Supabase | Checkpoints + app rows | Session-mode pooler, port 5432. See §5. |

**Render holds no in-memory session state.** The only thing tying an HTTP request to an in-flight interview is the `session_id`. The process may die between any two nodes without losing an interview.

---

## 2. The agent panel

Six agents against `https://integrate.api.nvidia.com/v1`. Each agent spec lives at
`docs/specs/agents/AGENT-<NAME>-SPEC.md` and is the authority on prompts, schemas, and golden
cases; this section is the contract summary.

### Model selection, measured

| Role | Model | Structured output | Latency |
|---|---|---|---|
| **fast** | `nvidia/nemotron-3-nano-30b-a3b` | 3/3 strict | 2.3–4.2s |
| **deep** | `nvidia/nemotron-3-super-120b-a12b` | 3/3 strict | 1.7–4.3s |
| fallback | `openai/gpt-oss-20b` | 3/3 strict | ~4.0s |

**Not GLM 5.2, despite its capability panel.** Measured 2026-07-29: a 3-token prompt took
**~230 seconds**, of which ~228s was queueing and ~2s was generation. `meta/llama-3.3-70b` and
`openai/gpt-oss-120b` queue similarly. The congestion is per-model demand, not an account
throttle — NVIDIA's own Nemotron models answered the same prompt in 0.3–0.4s. On a free tier,
**how contended a model is matters more than how capable it is**, and only the first of those
is documented.

Structured output uses `response_format: {"type": "json_schema", ..., "strict": true}` and was
3/3 across three trials on every fast candidate, in both schema-enforced and prompt-only modes.
Prompt-validate-retry remains as defence in depth but is not load-bearing.

**There is no portable reasoning-effort parameter.** `thinking` is GLM-specific; Nemotron 3
rejects it with `400 Unsupported parameter(s): 'thinking'`. The latency-versus-quality lever is
therefore **model choice**, not a request parameter — one dimension instead of two.

**Catalog presence is not availability.** `/v1/models` returns 102 entries, but several
404 (`llama-3.1-nemotron-70b-instruct`, `kimi-k2.6`) or 503 with `ResourceExhausted`
(`deepseek-v4-flash`, `nemotron-3-ultra-550b`). Verify with a real completion before depending
on any model.

| Agent | Node | Runs | Reads from state | Writes to state | Model |
|---|---|---|---|---|---|
| Resume Analyst | `level_candidate` | once | `resume_text` | `candidate_profile`, `assessed_level`, `level_rationale`, `low_confidence_fields` | deep |
| Case Architect | `generate_case_world` | once | `assessed_level`, `candidate_profile` | `case_world` | deep |
| Interview Planner | `plan_interview` | once | `assessed_level`, `case_world` | `question_plan` | deep |
| Interviewer | `ask_question`, `answer_clarification` | per turn | `question_plan`, `case_world`, `messages`, `followup_count`, `dimension_coverage` | **fast** |
| Evaluator | `evaluate_answer` | per answer | `messages`, `case_world`, `assessed_level` | `answer_evaluations`, `dimension_coverage` | deep |
| Coach | `coach_report` | once | everything | `coach_report` | deep |

`fast` = `nvidia/nemotron-3-nano-30b-a3b` · `deep` = `nvidia/nemotron-3-super-120b-a12b` ·
fallback `openai/gpt-oss-20b`. Only the Interviewer runs while a candidate watches a cursor
blink, so it is the only one that trades depth for latency.

**Immutability rule:** `case_world` is written exactly once, by the Case Architect. Every downstream agent reads it; none writes it. This is what prevents the interviewer contradicting itself when a candidate asks a clarifying question forty minutes in.

**Failure behaviour** is uniform: schema validation failure re-prompts once with the validation error appended, then fails the node. A failed node retries from its last checkpoint, so no successful upstream LLM call is re-paid for. See §9.

---

## 3. The graph

```
START
 → parse_resume            deterministic, no LLM
 → level_candidate         Resume Analyst
 → confirm_level           ◀── interrupt #1 — candidate confirms or overrides
 → generate_case_world     Case Architect
 → plan_interview          Planner
 → [conduct_round]         subgraph, loops
 → aggregate_scorecard     deterministic roll-up
 → coach_report            Coach — whole transcript in one 1M-context call
END
```

### `conduct_round` subgraph

```
     ┌──────────────────┐
     │  ask_question    │   Interviewer LLM call
     └────────┬─────────┘
              ▼
     ┌──────────────────┐
     │ await_candidate  │   ◀── interrupt #2
     │ interrupt() ONLY │       nothing else in this node
     └────────┬─────────┘
              ▼
        ┌───────────┐
        │route_input│   conditional edge on payload["type"]
        └─────┬─────┘
      clarify │       │ answer
              ▼       ▼
   ┌────────────────┐ ┌──────────────────┐
   │answer_clarify  │ │ evaluate_answer  │  Evaluator
   │ reads          │ └────────┬─────────┘
   │ case_world     │          ▼
   └───────┬────────┘   ┌─────────────┐
           │            │ decide_next │  deterministic, no LLM
           │            └──┬───────┬──┘
           │        probe  │       │  advance
           └──────────▶ ask_question   exit subgraph
```

**Why `ask_question` and `await_candidate` are separate nodes.** On resume, LangGraph re-runs the entire node from its top — not from the `interrupt()` line. If the LLM call and the interrupt shared a node, every resume would re-issue the question and burn a request against the 40 RPM ceiling. `await_candidate` therefore contains the `interrupt()` call and its return, and nothing else. **This is the single most important structural constraint in the codebase.**

**Why `decide_next` is not an LLM call.** It reads `followup_count`, elapsed time, and `dimension_coverage` — all already in state. Making it deterministic saves roughly one LLM call per turn against the rate ceiling, and makes routing reproducible and unit-testable.

```python
def decide_next(state: InterviewState) -> str:
    covered = sum(1 for v in state["dimension_coverage"].values() if v > 0)
    elapsed = seconds_since(state["started_at"])
    if state["followup_count"] >= 3 or elapsed > 2400 or covered == 5:
        return "advance"
    return "probe"
```

---

## 4. State management

### There is no orchestrator agent

The orchestrator is the graph topology plus one shared state object. Agents read state, return partial updates, and LangGraph merges and persists them. Routing is done by plain Python reading that state.

This is not only idiomatic — it is load-bearing here. An LLM orchestrator would cost a call per turn against a 40-request ceiling and could hallucinate its own control flow. A function reading a counter cannot.

### The state schema

```python
class InterviewState(TypedDict):
    session_id: str

    # ── Resume Analyst ─────────────────────────────────────
    resume_text: str
    candidate_profile: dict
    assessed_level: str                      # APM | PM | Senior PM | GPM
    level_rationale: str
    low_confidence_fields: list[str]

    # ── Case Architect — written once, read-only after ─────
    case_world: dict

    # ── Planner ────────────────────────────────────────────
    question_plan: list[dict]

    # ── Conduct loop ───────────────────────────────────────
    messages: Annotated[list, add_messages]
    current_q_idx: int
    followup_count: int
    dimension_coverage: dict[str, int]
    started_at: str

    # ── Evaluator / Coach ──────────────────────────────────
    answer_evaluations: Annotated[list[dict], operator.add]
    scorecard: dict | None
    coach_report: dict | None
```

### Reducers

How a node's return value merges into state. Getting this wrong produces a silent bug, not an error.

| Field | Reducer | Behaviour |
|---|---|---|
| most fields | none | **Overwrite.** `current_q_idx` replaces the old value. |
| `messages` | `add_messages` | **Append**, de-duplicating by message ID. |
| `answer_evaluations` | `operator.add` | **Concatenate.** Each `evaluate_answer` returns a one-element list; they accumulate. |

> **The trap:** without `operator.add`, `answer_evaluations` would hold only the most recent evaluation. No exception is raised. You would simply get a scorecard built from one answer and have nothing to debug. A test asserts `len(answer_evaluations) == answer_count`.

### The checkpoint lifecycle

With `AsyncPostgresSaver` attached at `.compile()`, LangGraph writes a **complete state snapshot to Supabase after every node** — automatically, with no persistence code in any node. Not at the start. Not at the end. After each one.

```
parse_resume        ──▶ checkpoint
level_candidate     ──▶ checkpoint
confirm_level       ──▶ checkpoint   ← interrupt; HTTP request ends
generate_case_world ──▶ checkpoint
plan_interview      ──▶ checkpoint
ask_question        ──▶ checkpoint
await_candidate     ──▶ checkpoint   ← interrupt; HTTP request ends
evaluate_answer     ──▶ checkpoint
        …one per node, for the life of the session
```

Four consequences, each load-bearing:

1. **Resume is from the last completed node, never from the beginning.** A crash during `evaluate_answer` on question 4 resumes at question 4. Nothing before it re-runs.
2. **A Render cold start mid-interview is a latency event, not data loss.** The process can die between any two nodes.
3. **Every `interrupt()` is a checkpoint you deliberately stop at.** A candidate spending ten minutes typing costs zero server resources — there is no session held open.
4. **Failed LLM calls are cheap.** A 429 kills one node; it re-runs from the last checkpoint. Successful upstream calls are not re-paid for.

The trade-off is storage: full snapshots, not diffs. See §10.

### `thread_id`

```python
config = {"configurable": {"thread_id": session_id}}
```

The interview session UUID *is* the `thread_id`. It is generated client-side, stored in `localStorage` (V1 is anonymous), and sent with every request. Keep it under 255 characters.

### Inspection

`graph.get_state(config)` returns the current snapshot plus `.next`, the queued nodes — this is how a stuck session is debugged. `graph.get_state_history(config)` replays every checkpoint in order, which is effectively a free time-travel debugger.

---

## 5. Persistence

### Two stores, deliberately

| | LangGraph checkpoints | App tables |
|---|---|---|
| Written by | The checkpointer, automatically | Nodes, explicitly |
| Shape | Opaque serialized blobs | Normalized, queryable |
| Purpose | Machine resume state | Product data, analytics, the UI |
| Read by | LangGraph only | Frontend via Supabase Realtime |

Nodes write to both. The frontend never reads checkpoints — they are an internal format with no stability guarantee.

### Schema

```sql
create table sessions (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid null references auth.users,   -- nullable: V1 is anonymous
  status      text not null default 'created',
  level       text,
  created_at  timestamptz not null default now()
);

create table resumes (
  id           uuid primary key default gen_random_uuid(),
  session_id   uuid not null references sessions on delete cascade,
  storage_path text not null,
  parsed_text  text,
  profile      jsonb
);

create table case_worlds (
  id         uuid primary key default gen_random_uuid(),
  session_id uuid not null references sessions on delete cascade,
  world      jsonb not null                       -- immutable audit copy
);

create table transcript_turns (
  id         uuid primary key default gen_random_uuid(),
  session_id uuid not null references sessions on delete cascade,
  idx        int  not null,
  role       text not null,                       -- interviewer | candidate | system
  kind       text not null,                       -- question | followup | answer | clarify | meta
  content    text not null,
  created_at timestamptz not null default now(),
  unique (session_id, idx)
);

create table answer_evaluations (
  id             uuid primary key default gen_random_uuid(),
  session_id     uuid not null references sessions on delete cascade,
  turn_idx       int  not null,
  dimension      text not null,
  score          int  not null check (score between 1 and 4),
  evidence_quote text not null check (length(evidence_quote) > 0)
);

create table agent_events (
  id          uuid primary key default gen_random_uuid(),
  session_id  uuid not null references sessions on delete cascade,
  agent       text not null,
  status      text not null,                      -- started | done | error
  summary     text,                               -- human-readable, never raw JSON
  duration_ms int,
  tokens      int,
  created_at  timestamptz not null default now()
);
```

`agent_events` powers the orchestration column and doubles as a debugging audit log. The `check (length(evidence_quote) > 0)` constraint enforces at the database level the PRD guarantee that no score ships without evidence.

LangGraph's own `checkpoints`, `checkpoint_writes`, and `checkpoint_blobs` tables are created by `checkpointer.setup()` in the same database. No naming collision.

### Connection string — the trap

Supabase exposes three connection strings. Only one works here.

| Mode | Host / port | Verdict |
|---|---|---|
| Direct | `db.<ref>.supabase.co:5432` | ❌ **IPv6-only.** Render's free tier is IPv4-only. Will not resolve. |
| Transaction pooler | `...pooler.supabase.com:6543` | ❌ Resolves, but recycles connections between transactions, breaking psycopg prepared statements → `DuplicatePreparedStatement: prepared statement "_pg3_0" already exists` |
| **Session pooler** | **`aws-<region>.pooler.supabase.com:5432`** | ✅ **Use this.** IPv4-reachable, one dedicated backend connection per session, prepared statements behave normally. |

If the transaction pooler ever becomes necessary, pass `{"autocommit": True, "prepare_threshold": 0}`.

`checkpointer.setup()` runs exactly once, via `scripts/init_db.py`, never on application startup.

### RLS posture

V1 is anonymous, so RLS is enabled with permissive policies scoped by `session_id`. `user_id` exists and is nullable from day one so that adding Supabase Auth later is a policy migration rather than a schema rewrite. `agent_events`, `answer_evaluations`, and `transcript_turns` are added to the `supabase_realtime` publication.

---

## 6. Request lifecycle

### One candidate turn

```
1.  Candidate clicks Send. Browser POSTs {session_id, {"type":"answer","text":"..."}}

2.  FastAPI handler:
      config = {"configurable": {"thread_id": session_id}}
      graph.astream(Command(resume=payload), config, stream_mode=["updates","custom"])

3.  LangGraph loads the checkpoint for session_id from Supabase.
    Re-enters await_candidate from the top. interrupt() now RETURNS the payload.

4.  route_input reads payload["type"] == "answer" → evaluate_answer
       ├─ writes agent_events(agent="evaluator", status="started")   ─┐
       ├─ LLM call, thinking enabled, reasoning_effort high           │  Realtime
       ├─ writes answer_evaluations rows                              ├─▶ pushes to
       └─ writes agent_events(status="done", duration_ms, tokens)    ─┘  right column
                                                                          + left rail
5.  decide_next → "probe" (deterministic, no LLM)

6.  ask_question
       ├─ agent_events(agent="interviewer", status="started")
       ├─ LLM call, thinking DISABLED (latency)
       ├─ writes transcript_turns row
       └─ agent_events(status="done")

7.  await_candidate → interrupt() → checkpoint written, graph pauses

8.  FastAPI's astream generator completes; SSE stream closes.
    Browser has the follow-up question and renders it whole after a 600–1200ms beat.
```

Note that steps 4 and 6 push to the UI over **two independent channels**. The SSE stream carries the interviewer's output. Supabase Realtime carries agent status to the left rail and scores to the right panel. They are deliberately decoupled.

### A resumed session after a cold start

```
1.  Candidate returns after 25 minutes. Render has spun down.

2.  Browser GETs /session/{id}/state. Request triggers a cold start:
    30–60s. The UI shows "Waking up the interviewer…" — silence reads as broken.

3.  FastAPI boots. It has NO memory of this session, and does not need any.
    graph.get_state(config) reads the last checkpoint from Supabase.

4.  Returns .next == ("await_candidate",) plus the transcript so far.

5.  Browser shows the "Welcome back — you were on Question 3" interstitial.

6.  Candidate resumes. The next POST is an ordinary turn, exactly as above.
```

Nothing about step 3 is special-cased. Resume-after-crash and resume-after-idle are the same code path, because the backend was never stateful to begin with.

---

## 7. Real-time

Two channels, split by what they carry.

| | Chat | Left rail + right panel |
|---|---|---|
| Transport | SSE from FastAPI | Supabase Realtime `postgres_changes` |
| Source | `graph.astream(stream_mode=["updates","custom"])` | `agent_events`, `answer_evaluations` |
| Survives Render cold start | No — it is the in-flight call | **Yes** — reads Postgres directly |

SSE over WebSocket: `EventSource` auto-reconnects natively, which matters given a backend that spins down. WebSockets require hand-rolled reconnect logic and offer bidirectionality this app has no use for — candidate answers are discrete POSTs, not a stream.

`stream_mode="updates"` (diffs), never `"values"` (full snapshots). `values` would re-send the entire case world and transcript on every node.

---

## 8. Frontend

### Shell

Desktop-first; ≥1280px is the design target.

```
┌────────────────┬──────────────────────────────────┬─────────────────────┐
│ ORCHESTRATION  │  Maya Chen · Sr. PM Panelist     │  LIVE EVALUATION    │
│  280px fixed   │  Q 2 of 5          22:14 elapsed │  320px fixed        │
│                │                                  │                     │
│ ● Resume Agent │  ┌───┐ Your competitor just cut  │  Business model     │
│   done · 1.2s  │  │ M │ enterprise pricing 40%.   │  ████████░░  3/4    │
│                │  └───┘ What do you do?           │                     │
│ ● Case Architect│                                 │  Market accuracy    │
│   done · 3.4s  │        ┌──────────────────────┐  │  ██████░░░░  2/4    │
│                │        │ You                  │  │                     │
│ ● Planner      │        │ First I'd separate…  │  │  Decision quality   │
│   done · 2.1s  │        └──────────────────────┘  │  ░░░░░░░░░░  —      │
│                │                                  │                     │
│ ◉ Interviewer  │  ┌───┐│ FOLLOW-UP                │  Structural clarity │
│   ▓▓▓▓░░ active│  │ M ││ Say the board wants an   │  ████████░░  3/4    │
│                │  └───┘│ answer this week.        │                     │
│ ◉ Evaluator    │                                  │  Point of view      │
│   scoring Q2   │  ● ● ● Maya is reviewing…        │  ██████░░░░  2/4    │
│                │                                  │  ───────────────    │
│ ○ Coach        │ ┌──────────────────────────────┐ │  INSIGHTS           │
│   waiting      │ │ Type your answer…            │ │  → Named criteria   │
│ ───────────────│ │                              │ │    before choosing  │
│ 9 calls · 6.1s │ └──────────────────────────────┘ │                     │
│ 4.2k tokens    │ autosaved · ? clarify   [Send →]│  Coverage 3/5 dims  │
└────────────────┴──────────────────────────────────┴─────────────────────┘
```

**Left — orchestration.** Per-agent card: name, status, one-line human-readable activity ("scored your prioritization answer", never raw JSON), duration, tokens. Four states distinguished by **shape as well as colour**: `○` waiting, `◉` active (pulsing), `●` done, `⚠` error. Errors read as plain language with a details disclosure. Updates batched ~300ms; fade-and-slide entrances at 150–200ms.

**Centre — chat.** Persona header pinned. Questions revealed whole after a 600–1200ms beat, never token-streamed. Follow-ups indented 24px behind a thin left rule. System events centred, muted, no bubble. Composer is a large autosaving textarea with a separate low-emphasis "ask a clarifying question" affordance. Answers immutable once sent.

**Right — live evaluation.** Bar per rubric dimension with the numeric value always beside it; unscored dimensions show `—`, not zero. Blind-mode toggle in the header swaps scores for coverage signals.

Below 1280px the layout collapses to chat-primary with the side panels as tabs. Graceful degradation, not a mobile redesign.

### Stack and state boundary

React + Vite (not Next.js — the backend is a separate FastAPI service, so SSR and API routes solve nothing here, and Vite deploys to Netlify's static tier without fighting the platform). Tailwind + shadcn/ui. Recharts for the final scorecard.

| Concern | Tool |
|---|---|
| Server state — session, transcript, scorecard | TanStack Query |
| Live push — agent events, evaluations | Supabase Realtime → Query cache |
| UI-only state — composer draft, blind mode, panel collapse | Zustand |

### Design tokens

Neutral base, one accent, no gradients. Light mode default — permanent dark mode is itself a documented AI-generated tell, and this is a tool used at a desk in daylight.

| Token | Light | Dark |
|---|---|---|
| Background | `#FBFBFA` | `#0E0F11` |
| Surface | `#FFFFFF` | `#17181B` |
| Border | `#E6E6E3` | `#26282D` |
| Text primary | `#16171A` | `#ECEDEF` |
| Text secondary | `#6B6D73` | `#8B8E96` |
| **Accent** | `#3A63D0` | `#6E92E8` |
| Success / warning / error | `#2E7D5B` · `#B7791F` · `#B3452C` |

Type: **Geist** for UI and body, **Geist Mono** for all numerals — one of the two pairings v1 §3 names for software UI, and mono for numbers is mandatory so timers and token counts do not jitter in width as they update. No serif anywhere; v1 §7 bans serif on dashboards outright.

Icons: **`@phosphor-icons/react`**, `strokeWidth` standardized at `1.5` globally. Not `lucide-react` — three of the installed skills independently discourage it, and shadcn's default is swappable at scaffold time but expensive to change later.

4px spacing scale. Radius 8px on cards, 6px on controls, applied consistently. Single-layer shadows tinted to the background hue, never pure black. Transitions `cubic-bezier(0.16, 1, 0.3, 1)` at 150–200ms rather than `ease-in-out`; `scale-[0.98]` on `:active` for tactile feedback. The one longer beat is the scorecard reveal at 400–600ms. `prefers-reduced-motion` respected throughout.

Every interactive surface ships its full state cycle — loading (skeletal loaders matching final layout, never circular spinners), empty, and error — per v1 §3 Rule 5. Form labels sit above inputs with `gap-2`; no placeholder-as-label.

### Design skill authority

All 13 skills from `github.com/Leonxlnx/taste-skill` are installed at `.agents/skills/`.

**`design-taste-frontend-v1` is the governing skill for this product, not v2.**

This is deliberate and counter-intuitive. The current default, `design-taste-frontend` (v2), **explicitly scopes itself out** in its own §13 — "Dashboards / dense product UI / admin panels… Multi-step forms / wizards" are listed as out of scope, and it instructs the agent to say so rather than apply it wholesale. The v1 skill it replaced still carries dedicated software-UI rules that v2 dropped in its rewrite toward landing pages:

- **§3 Rule 1** — "Serif fonts are strictly BANNED for Dashboard/Software UIs. Use exclusively `Geist` + `Geist Mono` or `Satoshi` + `JetBrains Mono`."
- **§3 Rule 4** — "DASHBOARD HARDENING: for `VISUAL_DENSITY > 7`, generic card containers are strictly BANNED. Use logic-grouping via `border-t`, `divide-y`, or negative space."
- **§2** — "You MUST use exactly `@phosphor-icons/react` or `@radix-ui/react-icons`", with a globally standardized `strokeWidth`.
- **§6 VISUAL_DENSITY 8-10** — "Mandatory: use Monospace (`font-mono`) for all numbers."
- **§7** — the AI-tells list, including no pure black, no oversaturated accents, no Inter, no generic names, **no fake-round numbers**.

### Dial settings

v1 gates its rules on three dials. Ours, with reasoning:

| Dial | Value | Reasoning |
|---|---|---|
| `DESIGN_VARIANCE` | **3** | A fixed three-column assessment shell. Asymmetry and masonry are wrong for a tool someone works inside for 45 minutes. This is the one place we deliberately sit at the low end of the skill's range. |
| `MOTION_INTENSITY` | **4** | "Fluid CSS" band. Deliberately *below* 5 to avoid the skill's perpetual-micro-interaction mandate, which would fight the anti-jitter requirement from UI research. The single exception is the active-agent pulse, which carries real semantic state. |
| `VISUAL_DENSITY` | **6** | "Daily App Mode". Keeps card containers legitimate per Rule 4 — above 7 they would be banned, which would contradict the brief. |

**How density resolves the card question.** At 6, cards are permitted where elevation communicates hierarchy: the three columns as surfaces, and chat messages. Inside the rails, individual agent rows and score rows are grouped with hairlines and spacing rather than nested cards. "Rounded cards" describes the shell, not a box around every row.

### Applied from v2 as well

v2 is a substantial rewrite with rules that still transfer: the expanded AI-tells list (§9), **the em-dash ban in all user-facing copy**, button and form contrast checks (§4.5/4.6), the shape consistency lock (§4.4), and theme lock (§4.11).

**Not applied from either:** heroes, bento grids, eyebrow limits, marquees, logo walls, scroll hijacking, and the landing-page pre-flight items. If a marketing page is built later, v2 governs it in full — and `high-end-visual-design` becomes relevant there too, since its `py-24`-to-`py-40` macro-whitespace and floating-glass-pill navigation are built for exactly that surface and would be absurd here.

**Resolved by this reading:** v2's pre-flight bans "scoring/progress bars with filled background tracks" — but its own §9.F frames that as a landing-page rule and calls the pattern "dashboard-UI clutter *on a landing page*." We are the dashboard. The right panel's bars are correct as specified.

### Constraints this places on agent prompts, not just CSS

Two v1 AI-tells reach past the UI into the Case Architect's spec:

- **No fake-round numbers.** `99.99%`, `50%`, `$1M` are tells. Generated case-world financials must be organic — `31.4%` market share, `$4.7M` ARR, `18.2%` churn.
- **No generic names.** "John Doe", "Sarah Chan" and that register are banned. This applies to generated company names, competitor names, and the interviewer persona. The placeholder "Maya Chen" used in wireframes above sits squarely in the banned register and must be replaced before Phase 3 ships.

---

## 9. Failure modes

| Failure | Detection | Recovery |
|---|---|---|
| **Render cold start** | Request latency > 5s after idle | Expected, not an error. UI shows "Waking up the interviewer…" — silence reads as broken. Client pings `/health` every 10 min while a session is open to hold off the 15-minute spin-down. State is safe regardless. |
| **NVIDIA 429** | HTTP 429 | Exponential backoff with jitter, 20–30s per-call timeout. The node retries from its last checkpoint; successful upstream calls are not re-paid for. |
| **Structured output validation failure** | Pydantic `ValidationError` | Re-prompt once with the validation error appended. On second failure, fail the node and surface a plain-language error in the left rail. Never ship a partially-parsed evaluation. |
| **Supabase project paused** | Connection refused after 7 days idle | Manual unpause from the dashboard. Presents as a total outage; worth knowing before sharing a link. |
| **Interviewer contradicts the case world** | Manual: 5 adversarial clarifying questions in the Phase 3 gate | Structural, not runtime. `case_world` is immutable and `answer_clarification` reads only from it. If it recurs, the Interviewer prompt is leaking improvisation. |
| **Wrong reducer** | Test asserts `len(answer_evaluations) == answer_count` | Silent otherwise. This is why the assertion exists. |
| **Checkpoint bloat** | Periodic `pg_total_relation_size` check | Keep bulky artifacts (raw resume text after parsing, evaluation prose) in app tables; hold references in graph state. |
| **`interrupt()` re-run side effect** | Duplicate questions or double-counted turns | Structural: `await_candidate` contains only `interrupt()`. Any node containing an interrupt must have nothing before it. |

---

## 10. Constraints ledger

Every free-tier limit with its headroom, so the first thing to be outgrown is visible.

| Constraint | Limit | Expected V1 usage | Headroom |
|---|---|---|---|
| NVIDIA requests | 40/min | ~2 per candidate turn; a turn is ≥30s of human time | Comfortable for one candidate. **Tight for two concurrent sessions.** First thing to break under a demo. |
| Render RAM | 512MB | FastAPI + LangGraph + pypdf | Adequate. Rules out `unstructured` and `docling` for parsing. |
| Render spin-down | 15 min idle | Triggers mid-interview routinely | Mitigated by architecture, not avoided. |
| Render background workers | **Not free** | — | Forces inline evaluation. Cannot add a queue without paying. |
| Supabase database | 500MB | App tables + full-snapshot checkpoints | Monitor. Checkpoints grow faster than intuition suggests. |
| Supabase pause | 7 days idle | — | Manual unpause. Affects demos, not development. |
| Supabase storage | 1GB | Resume PDFs, ~200KB each | Thousands of sessions. Not a concern. |
| Netlify bandwidth | Generous | Static bundle only | Not a concern — no LLM traffic passes through it. |

---

**See also:** [PRD.md](PRD.md) · [DEV-STATE.md](DEV-STATE.md) · [specs/](specs/) · [research/](research/)
