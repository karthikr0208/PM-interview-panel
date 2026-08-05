# Phase 3 — Interviewer and the conduct loop

**Goal:** a candidate holding a question plan sits an interview. The Interviewer asks 2-3 of the
planned questions, the candidate answers or asks a clarifying question, and the graph pauses and
resumes across HTTP requests without re-asking anything.

**Why this phase exists.** Phase 2 ends with a plan nobody has walked. This is the phase where the
product becomes an interview rather than a pipeline, and it carries the last structural risk in the
architecture: **`interrupt()` #2, inside a loop.** Phase 0 proved a single interrupt resumes across
separate HTTP requests. It did not prove a *looping* one does, and a loop is where the
re-run-from-the-top semantics actually bite.

**Done when:** one candidate journey runs upload → level → confirm → case world → plan → **2-3
asked-and-answered questions**, across real HTTP request boundaries, with a transcript in state.

---

## 🔴 DELIBERATELY THIN. Read this before adding anything.

**Per CLAUDE.md's portfolio calibration (2026-08-02), this phase asks 2-3 questions, not the plan's
full 5-7, and it does NOT score answers.** Scoring is Phase 4. `evaluate_answer` in ARCHITECTURE's
`conduct_round` diagram is **out of scope here** — the loop runs without it.

That has one real consequence worth stating up front, because it is the kind of thing that gets
quietly reintroduced. **`decide_next` cannot read `dimension_coverage` from scores that do not exist
yet.** In this phase it fills coverage from the *asked* question's `primary_dimension`, which the
Planner already wrote. Phase 4 replaces that source with real scores and should not need to change
the routing shape.

**Three stories. Not seven.** Phase 1's spec had seven and took four sessions.

---

## 🔴 Traps carried forward. Every one is a recorded failure from this project.

| Trap | Where it bit |
|---|---|
| **`await_candidate` contains ONLY `interrupt()` and its return** | The single most important structural constraint in the codebase (ARCHITECTURE §3, CLAUDE.md). LangGraph re-runs the whole node from its top on resume. An LLM call, a counter, or a write above the interrupt runs **twice per turn**, silently. Story 1.4 proved this assertion can fail, against a deliberately wrong graph |
| **Falsify the single-call assertion, do not inspect it** | `backend/scripts/falsify_single_call.py` already exists and does exactly this for one interrupt. **A looping interrupt needs its own falsification** — the existing script does not cover it |
| **Write the golden fixtures BLIND, before the prompt** | Story 1.3 was split for this. Phase 2 did it deliberately and it caught four defects |
| **Every denial assertion needs a positive control and a vacuity floor** | Story 1.3a: the suite's most important check passed on all eight cases because an empty list satisfied it. Phase 2 hit the same shape again in `missing_grounding` |
| **`case_world` is immutable, and `answer_clarification` reads ONLY from it** | If the Interviewer improvises a fact, it contradicts itself later and only a human notices. ARCHITECTURE §9 lists this with no runtime detection |
| **Classify every failure before believing it** | Three times a mostly-red run was rate limiting. Grep for `tokens per day` and `tokens per minute` first |
| **A green run is one sample** | `temperature=0` does not make these models deterministic |
| **The node owns side effects, the agent function stays pure** | Held for all three agents so far. Golden cases run with no database because of it |

**🔴 The em-dash ban reaches a NEW surface in this phase, and no existing guard covers it.**
`tests/test_user_facing_copy.py` checks source strings, and as of 2026-08-04 also every `_*_SUMMARY`
constant. **The Interviewer generates candidate-facing prose at runtime**, which no static check can
see. The ban has to live in the prompt AND be asserted in the golden cases, the same way the
Planner's is.

**Model:** the Interviewer is **`fast`** per ARCHITECTURE §4, and this is the one place that table
and the portfolio calibration agree — it is the only agent that runs while a candidate watches a
cursor. Note the Planner needed `deep` (DEV-STATE § Decisions 2026-08-04); do not assume `fast`
works here without checking, and **do not assume it fails either.**

**Budget:** 200,000 tokens per model per day, rolling, invisible in every header. The conduct loop
is the first thing in the product that makes **several LLM calls per candidate turn**. Estimate the
per-turn cost before building the loop, not after.

---

## Stories

### 3.1 `AGENT-INTERVIEWER-SPEC.md` and its golden fixtures, both written before the prompt — ✅ DONE 2026-08-05

**Zero LLM cost. Do this on a day with no budget.** Held: the whole story cost **zero tokens**.

**Acceptance**
- [x] `docs/specs/agents/AGENT-INTERVIEWER-SPEC.md` defines both behaviours the agent has: **asking a planned question** and **answering a clarifying question from `case_world` alone**. §2a decides the first is **deterministic Python plus a small LLM bridge**, not a regeneration — see the decision in DEV-STATE
- [x] It states the prompt-size ceiling, **computed** from the largest real `case_world` plus the transcript, against the 8,000 TPM bucket. §6. **The naive design does not fit** and the finding is a constraint on story 3.2, not a footnote
- [x] Golden fixtures at `backend/tests/golden/interviewer/`, **written blind**, reusing Phase 2's hand-written case worlds so a `CaseWorld` change breaks every suite loudly. Fixtures hold a `world_fixture` pointer and never copy a world; a test pins that
- [x] **The assertion with teeth: an answer to a clarifying question invents nothing.** `grounded_in` set-membership **plus `ungrounded_figures`**, which is new and has no Planner equivalent
- [x] A **positive control** for it: a clarification answer citing an entity no world contains must FAIL. Plus the cross-world control, both halves
- [x] A **vacuity floor** beneath it, asserted first — and `can_answer=False` is **not** an exemption from it, which is the escape hatch this schema introduced
- [x] No em-dash or en-dash in generated question or clarification text. **The question is emitted verbatim by Python** so it inherits the Planner's already-passing check. 🔴 **`bridge` is a known gap owed to 3.2** — see spec §5
- [x] Suite is **deliberately RED**, proven by running it: `ModuleNotFoundError: No module named 'app.agents.interviewer'` in **0.17s**, before any network call

---

### 3.2 The Interviewer agent and the `conduct_round` loop — ✅ DONE 2026-08-05

**Acceptance**
- [x] `app/agents/interviewer.py` exposes **pure** functions, no database and no session, matching the other three agents
- [x] `ask_question` and `await_candidate` are **separate nodes**, and `await_candidate` contains **only** `interrupt()` and its return
- [x] `route_input` is a conditional edge on the resume payload's type: `clarify` or `answer`. 4 offline tests including both defaults
- [x] `decide_next` is **deterministic Python, no LLM call** — 10 offline tests, covered at its boundaries
- [x] The loop **exits after 2-3 questions**, exit condition in one place (`_QUESTIONS_THIS_PHASE`). Observed asking exactly 3 over HTTP
- [x] **🔴 The single-call guarantee is FALSIFIED for the looping interrupt.** `backend/scripts/falsify_looping_interrupt.py` — **and both sides are now observed**, which the script alone did not do: the wrong graph logs 4 where a correct 2-question loop logs 2, and the correct graph's own baseline (`q1=0, q2=1, q3=2`, staying at 3 across a clarification resume) is pinned by three live tests
- [x] **Two** golden cases smoked live on `fast`, not one: the plainly-answerable case and the refusal case, because the refusal branch is where the design risk lives. Both passed
- [x] The chain runs end to end from one resume through 3 answered questions, **across real HTTP request boundaries** — `backend/scripts/prove_interview_over_http.py`, a real uvicorn subprocess driven over a socket

**The trap specific to this story:** a loop that re-runs `ask_question` on resume looks *correct
from state* — the transcript still reads sensibly. Only the call log shows the duplicate. **Assert
on `app/llm.py`'s log, never on state.** That is the same instruction story 1.4 followed, for the
same reason.

---

### 3.3 The interview UI — ✅ DONE 2026-08-05

**Acceptance**
- [x] The question is revealed **whole, never streamed token by token** (design v1: no typewriter effect) — rendered in a single node, asserted on the complete string at first render
- [x] The candidate can answer, or ask a clarifying question, and the two are visibly distinct actions — two separate labelled controls, primary and secondary; each asserted to post its own `type`
- [x] Full loading / empty / error state cycle on the answer surface, matching 1.5's foundation — skeletal (never a spinner), disabled-with-a-visible-reason on empty, `role="alert"` plus a retry that resends the same action
- [x] The orchestration column shows the Interviewer, **by adding a row to `AGENTS` in `OrchestrationColumn.tsx`** — story 2.7 proved that is all a new agent needs. Confirmed again: one appended row, nothing else
- [x] **No em-dashes in any candidate-facing copy**, including anything rendered from model output — closed **deterministically, not by prompting**, via `stripDashes` at the render boundary. See DEV-STATE § Decisions 2026-08-05
- [x] **No persona header and no interviewer name.** Deferred since 2026-07-31 and still binding: "Maya Chen" sits in the register design v1 §7 bans

**Observed output**

```
frontend      13 files, 113 passed        (was 10 files / 84)
tsc --noEmit  clean
vite build    ok, dist/assets/index-DKTCjjeJ.js 435.10 kB
backend       221 passed, 95 deselected   (unchanged; no backend file touched)
```

**Falsified, not inspected.** Two deliberate mutations, both reverted:

```
clarification branch replaces the question   -> 2 failed  (TRAP 2 tests, interview.test.ts)
stripDashes removed from the question render -> 1 failed  (dash test, InterviewSurface.test.tsx)
                                                3 failed | 110 passed
```

---

## Automated tests

| File | Asserts |
|---|---|
| `tests/golden/interviewer/` | Clarification answers invent nothing · no dash variants · vacuity floor with a positive control |
| `tests/test_conduct_loop.py` | `await_candidate` re-runs without re-asking · `route_input` splits clarify from answer · `decide_next` is deterministic and covered at its boundaries · the loop exits |
| `frontend/src/**/*.test.ts` | Question renders whole · answer and clarify are distinct · Interviewer row shows four states |

---

## Phase gate

Matching Phase 2's, per the portfolio calibration:

1. **`pytest tests -m "not live"` green** — free, seconds.
2. **One Interviewer golden case as a smoke.** Not the full set.
3. **The loop runs across real HTTP request boundaries** for 2-3 questions, and the single-call
   guarantee has been **falsified**, not inspected.
4. **An interview Karthik sits and believes.** Still the one that matters, still his to judge, and
   the first time this product is a product.

---

## Handoff

**Verified by me, with evidence**

```
offline        221 passed, 95 deselected      backend
vitest         113 passed, 13 files           frontend  (was 84 / 10)
tsc --noEmit   clean
vite build     ok
live loop      3 passed, 20 deselected
golden smoke   apm_consumer_world        PASS on fast, retry_fired=False
               senior_pm_platform_world  PASS on fast, retry_fired=True  (refusal branch)
falsification  looping interrupt: wrong graph 1 -> 3 -> 4 where a correct loop logs 2
               TRAP 2:  clarification branch replaces the question  -> 2 failed
               dashes:  stripDashes removed from render             -> 1 failed
http proof     3 questions over 3 separate requests, clarification consumed no slot, done
deploy         Render route list + served Netlify bundle both verified by content,
               with a positive control
```

**Phase gate: 4 of 4.**

1. ✅ `pytest tests -m "not live"` green — 221 passed
2. ✅ One Interviewer golden case as a smoke — two ran, both PASS on `fast`
3. ✅ Loop runs across real HTTP boundaries, single-call guarantee **falsified** not inspected
4. ✅ **An interview Karthik sat and believed** — 2026-08-05, deployed stack, no bugs

**Verified by Karthik, in the browser, 2026-08-05**
- The whole flow runs smoothly with no bugs. Both the answer path and the clarify path.
- ✅ **The adversarial-fact check passed.** He asked a clarifying question whose answer was not in
  `case_world` and **the agent said so rather than inventing one.** ARCHITECTURE §9 lists this
  failure with **no runtime detection**, so this manual pass was the only thing that could catch it.
  One sample of a generative branch, which is proportionate for a portfolio artifact.

**Still open, and it is quality rather than correctness**
- **The generated questions are not good enough yet, and that is a PLANNER problem, not an
  Interviewer one.** `ask_question` copies `question_plan` byte for byte by design. Two defects
  observed across three served questions: a **decorative statistic** stapled to the front (2 of 3),
  and one question answerable by **reciting the case back** rather than exercising judgment.
  The three questions are recorded verbatim in DEV-STATE § Decisions 2026-08-05.
  **Karthik is bringing his own examples of good questions before the prompt is touched.**
