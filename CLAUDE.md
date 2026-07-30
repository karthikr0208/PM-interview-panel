# PM Interview Panel

Multi-agent PM interview simulator. A candidate uploads a resume, gets levelled, sits a
45-minute Product Strategy interview conducted by a panel of six cooperating agents, and
receives an evidence-linked scorecard plus a coaching report.

LangGraph orchestration · `z-ai/glm-5.2` via NVIDIA NIM · FastAPI on Render ·
React + Vite on Netlify · Supabase for all durable state. Entire stack is free tier.

---

## 🔴 Start of every session — before anything else

1. Read **`docs/DEV-STATE.md`**. It is the source of truth for what is done and what is
   next. Trust it over your own inference from the codebase.
2. Read the spec for the current phase: `docs/specs/PHASE-<N>-SPEC.md`
3. If working on an agent, read `docs/specs/agents/AGENT-<NAME>-SPEC.md`
4. Read the **Decisions & deviations** section of DEV-STATE carefully. Reality has diverged
   from the original plan in specific places, and **those entries supersede ARCHITECTURE.md
   wherever they conflict.**
5. State back: the current phase, the next story, and anything blocking it. Then begin.

**Do not re-derive project state by reading source files.** DEV-STATE.md is maintained
deliberately and is faster and more accurate than inference.

## 🔴 Updating DEV-STATE — non-negotiable

**Update it as you go, not only at session end.** The moment a story is done, tick it and
move the `← NEXT` marker, in the same commit as the code. Sessions end abruptly — context
runs out, the window closes, you get interrupted. Incremental updates lose at most one
story; end-of-session-only updates lose everything since the last commit.

At a natural stopping point, also write:
- A "Last session" summary and a "Next session — start here" pointer, with file paths
- Any deviation from spec under **Decisions & deviations**, dated, with the reason
- The agent spec / golden-case table, if either changed

A stale DEV-STATE is worse than none. It produces confident wrong assumptions.

---

## Which file answers which question

| Question | File |
|---|---|
| Where are we? What's next? | `docs/DEV-STATE.md` |
| Why does this product exist? What is the rubric? | `docs/PRD.md` |
| How does the system fit together? | `docs/ARCHITECTURE.md` |
| What is in scope this phase? | `docs/specs/PHASE-<N>-SPEC.md` |
| What is this agent's contract? | `docs/specs/agents/AGENT-<NAME>-SPEC.md` |
| Why was it built this way? | `docs/research/` |

---

## Rules that must never be broken

**Supabase: session pooler, port 5432** — `aws-<region>.pooler.supabase.com:5432`.
Not the direct connection (IPv6-only; Render free tier is IPv4-only, it will not resolve).
Not the transaction pooler on 6543 (breaks psycopg prepared statements).

**`await_candidate` contains only `interrupt()` and its return.** On resume LangGraph
re-runs the entire node from the top, not from the interrupt line. No LLM calls, counters,
or writes before an `interrupt()` in the same node — ever. This is the single most
important structural constraint in the codebase.

**`case_world` is immutable after Phase 2.** Written once by the Case Architect, read-only
for every agent downstream. It is what stops the Interviewer contradicting itself when a
candidate asks a clarifying question forty minutes in.

**Never develop against `MemorySaver`.** It hides the entire class of stateless-HTTP bugs
until deploy. Use the Postgres checkpointer from Phase 0 onward.

**Every LLM call is logged with a timestamp.** The free tier ceiling is 40 requests/minute
and it is the first thing that will break under a demo.

**Golden cases must pass before any agent prompt change is committed.** Prompt edits are
otherwise unfalsifiable — the output "seems fine" and a dimension silently regresses.

**No em-dashes in user-facing UI copy.** Per the design skill's AI-tells list. Docs are
exempt; anything a candidate reads is not.

---

## Testing & verification — three tiers

Every phase has all three. They answer different questions and live in different places.

**1. Automated tests — live in code, listed in the phase spec.**
`backend/tests/` (pytest) and `frontend/src/**/*.test.ts` (vitest). The phase spec names the
test files and what each must assert; the assertions themselves live in the code. A phase spec
never contains test code.

**2. Golden cases — fixtures, defined in agent specs.**
5–10 fixed inputs per agent with expected-output assertions, at
`backend/tests/golden/<agent>/`. Run with `make golden`. These are the regression suite for
prompts. **They must pass before any prompt change is committed** — without them, prompt edits
are unfalsifiable.

**3. Handoff checklist — in the phase spec, for the human.**
The things only you can judge: does the interview feel real, does the design look right, is
the feedback actually useful. Each phase spec ends with a **Handoff** section splitting
*Verified by me, with evidence* from *Needs your eyes*.

**The rule:** never hand a phase over claiming it works without having run tiers 1 and 2 and
pasted the actual output into `DEV-STATE.md`. "The tests should pass" is not evidence.
"Compiles" and "typechecks" are not evidence. A phase is handed over with observed output or
it is not handed over.

## Commands

**Use the venv, not the global interpreter.** `backend/.venv/Scripts/python.exe` on Windows,
`backend/.venv/bin/python` elsewhere. The global one has no langgraph and different versions of
fastapi, pydantic, and openai. The `make` targets already point at the venv; the bare `python`
lines below are the ones to watch.

```
python backend/scripts/check_env.py        # all credentials present AND working
python backend/scripts/check_db.py         # DB connects; diagnoses the 3 failure modes
python backend/scripts/probe_candidates.py # model latency + structured output, re-measure

make dev-api                  # FastAPI with reload
make dev-web                  # Vite dev server
make test                     # pytest + vitest
make test-api                 # pytest only
make test-web                 # vitest only
make golden                   # all agent golden cases
make golden AGENT=evaluator   # one agent
backend/.venv/Scripts/python.exe backend/scripts/init_db.py   # checkpointer .setup()
                              # run ONCE, never on app startup. Needs the venv: it imports
                              # langgraph, which the global interpreter does not have.
```

---

## Design

All 13 skills from `Leonxlnx/taste-skill` are installed at `.agents/skills/`.

**Use `design-taste-frontend-v1`, not v2.** Counter-intuitive but correct: v2
(`design-taste-frontend`) explicitly scopes itself out of this product in its own §13 —
"Dashboards / dense product UI / admin panels… Multi-step forms / wizards." The v1 skill it
replaced still carries the software-UI rules v2 dropped when it was rewritten toward landing
pages.

Dials for this project: `DESIGN_VARIANCE 3` · `MOTION_INTENSITY 4` · `VISUAL_DENSITY 6`.
Motion sits below 5 deliberately, to avoid v1's perpetual-micro-interaction mandate fighting
the anti-jitter requirement. Density sits at 6 so card containers stay legitimate — above 7
v1 bans them.

Non-negotiables that follow: **Geist + Geist Mono**, no serif anywhere, mono for every
number. **`@phosphor-icons/react`** at `strokeWidth 1.5` — not `lucide-react`. One accent
under 80% saturation. No pure black. Full loading / empty / error state cycles on every
interactive surface. Labels above inputs.

Also apply from v2: the AI-tells list (§9) and **the em-dash ban in all user-facing copy**,
plus the button and form contrast checks.

Ignore from both: heroes, bento grids, eyebrows, marquees, logo walls, scroll hijacking,
macro-whitespace. Those govern marketing pages. If a landing page is built later, v2 and
`high-end-visual-design` govern it in full.

Two of these rules constrain **agent prompts, not just CSS**: no fake-round numbers
(`50%`, `$1M`) and no generic names ("John Doe" register) in generated case worlds.

Tokens, dial reasoning, and the three-column layout are in `docs/ARCHITECTURE.md` §8.

---

## Style

Comments state constraints and non-obvious invariants, not narration. Match surrounding
code. No new abstractions without a second caller. Prefer deterministic Python over an LLM
call wherever the decision can be made from state — it is cheaper, testable, and does not
consume the rate budget.
