# PM Interview Panel

Multi-agent PM interview simulator. A candidate uploads a resume, gets levelled, sits a
45-minute Product Strategy interview conducted by a panel of six cooperating agents, and
receives an evidence-linked scorecard plus a coaching report.

LangGraph orchestration · **`nvidia/nemotron-3-nano-30b-a3b` (fast) and
`nemotron-3-super-120b-a12b` (deep)** via NVIDIA NIM, `openai/gpt-oss-20b` as backup ·
FastAPI on Render (Singapore) · React + Vite on Netlify · Supabase for all durable state
(Singapore). Entire stack is free tier.

Not GLM 5.2 — it queues ~230s on the free tier, measured. See DEV-STATE § Decisions 2026-07-29.

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
6. Before writing code, skim **§ What to update, and when** below, so you know what this
   story will owe on the way out. Cheaper to know up front than to reconstruct at the end.

**Do not re-derive project state by reading source files.** DEV-STATE.md is maintained
deliberately and is faster and more accurate than inference.

**`.planning/HANDOFF.json` is not this project's handoff.** It is an auto-generated plugin
checkpoint, is empty, and is gitignored. **`docs/DEV-STATE.md` is the handoff.** Ignore any
file that merely sounds authoritative.

## 🔴 End of every session — before the context runs out

Sessions end abruptly. Do this at the last natural stopping point, not when you feel finished:

1. Everything in **§ What to update, and when** for whatever you actually completed.
2. `git status` clean, or the leftovers named in DEV-STATE § Next session.
3. **"Next session — start here"** rewritten so a cold session can act on it without asking a
   question. Name the file paths and the exact command to run first.
4. Anything you verified but did not record is lost. Record the output, not the claim.

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

## 🔴 What to update, and when

### End of every story — same commit as the code

| File | What changes |
|---|---|
| `docs/DEV-STATE.md` | Tick the story, move `← NEXT`, **paste observed output**, add any decision |
| `docs/specs/PHASE-<N>-SPEC.md` | Tick that story's acceptance boxes; add `— ✅ DONE <date>` to its heading |

Two boxes and a paste. If it takes longer than that, the story was too big.

### End of every phase — additionally

| File | What changes |
|---|---|
| `docs/DEV-STATE.md` | Phase status table row · "Last session" · "Next session — start here" · Environment notes with real observed values |
| `docs/specs/PHASE-<N>-SPEC.md` | Handoff section: move items from *needs your eyes* to *verified*, strike what is resolved |
| `docs/specs/PHASE-<N+1>-SPEC.md` | Write it before starting it |
| `docs/specs/agents/AGENT-<NAME>-SPEC.md` | If the phase built an agent |
| `docs/DEV-STATE.md` agent table | Spec link, golden-case count, last prompt change |

### Triggered updates — these are the ones that rot silently

Every entry below is a real failure from this project, not a hypothetical.

| When you… | Also update |
|---|---|
| Rename an env var, or drop an API parameter | **grep `backend/scripts/`** · `app/config.py` `REQUIRED_VARS` · both `.env.example` · `CLAUDE.md` |
| Add a dependency | `requirements.txt` or `package.json` · DEV-STATE Environment notes |
| Add an env var | `backend/.env` · both `.env.example` · `config.py` · Render dashboard (0.8+) |
| Add or rename a command | `Makefile` **and** the Commands table below — the Makefile's own header says do not rename one without the other |
| Change an agent prompt | Golden cases must pass **first** |
| Create database objects, or change anything shared | Run the **entire** live suite, not just the file you wrote. Story 0.5 broke two of 0.4's tests by adding tables to the same schema; the offline suite stayed green at 21 passed throughout and every per-file run passed |
| Diverge from `ARCHITECTURE.md` | Log it under DEV-STATE § Decisions. **Do not edit ARCHITECTURE.md** — decisions supersede it, and rewriting history there destroys the audit trail |

**The scripts row is the one that bites.** On 2026-07-30, `check_env.py` still required a
variable deleted on 2026-07-29 and still probed a parameter recorded as rejected on the same
day. The decision was written down correctly; the tooling was never updated. Docs get re-read,
scripts do not — so a decision that touches a name or a parameter is not done until you have
grepped for it.

---

## Which file answers which question

| Question | File |
|---|---|
| Where are we? What's next? | `docs/DEV-STATE.md` |
| **What do I update when I finish a story or phase?** | **CLAUDE.md § What to update, and when** |
| **Why did this diverge from the plan?** | **`docs/DEV-STATE.md` § Decisions & deviations** — supersedes ARCHITECTURE.md |
| Why does this product exist? What is the rubric? | `docs/PRD.md` |
| How was it *designed* to fit together? | `docs/ARCHITECTURE.md` — the plan, not always current reality |
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
backend/.venv/Scripts/python.exe backend/scripts/migrate.py   # apply backend/migrations/*.sql
                              # Idempotent, safe to re-run. The ONLY way to change the schema —
                              # never the Supabase dashboard, or Render cannot recreate it.
                              # --dry-run lists what would apply.

backend/.venv/Scripts/python.exe backend/scripts/init_db.py   # checkpointer .setup()
                              # run ONCE, never on app startup. Needs the venv: it imports
                              # langgraph, which the global interpreter does not have.
                              # Separate from migrate.py: LangGraph owns its own table shapes.
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
