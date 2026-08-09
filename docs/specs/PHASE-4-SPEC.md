# Phase 4 — Evaluator and scorecard: a score that cannot be given without evidence

**Status:** ⬜ not started. Written 2026-08-07, before any code, from the live interview of the
same day. **Every number in § "What the live interview already decided" is measured, not projected.**

The Evaluator scores a candidate's answers against the PRD §7 rubric — five dimensions, 1 to 4,
each score carrying a verbatim quote from the transcript. The scorecard renders them. That is the
whole phase.

---

## 🔴 WHAT THE LIVE INTERVIEW ALREADY DECIDED. Read this before designing anything.

Karthik sat a full interview on 2026-08-07 (§ DEV-STATE Decisions, same date). Three of its
findings are load-bearing here, and all three would otherwise be discovered halfway through the
build.

### 1. TWO OF FIVE DIMENSIONS GOT ZERO EVIDENCE. This is the phase's hardest problem.

Final `dimension_coverage` after one question and eight probes:

```
business_model_fluency: 4    decision_quality: 4    structural_clarity: 1
market_accuracy:        0    point_of_view:     0
```

**The rubric has five equally-weighted dimensions and a real interview produced evidence for
three.** So the Evaluator will be handed a transcript and asked to score two dimensions nothing
was ever said about.

**Do NOT let it score them anyway.** A 1-to-4 on a dimension with no evidence is a fabricated
number wearing a rubric's authority, and PRD §8 already forbids the softer version of this
("every score carries a verbatim quote… enforced at the schema level, not by convention"). A score
with no quote available is the same defect as a score with an invented quote.

**The decision this phase must make, and it is Karthik's:** does an unevidenced dimension render as
`not assessed`, or does `dimension_coverage` steer the Interviewer so it never happens? They are not
alternatives — the first is required regardless, because coverage can never be guaranteed; the
second is a Phase 3.5 change that reduces how often it fires. **Ship the first. Propose the second.**

An aggregate over five dimensions where two are unassessed is misleading whatever the label says.
**If a dimension is unassessed, there is no overall score.** Say what was assessed.

### 2. A SINGLE END-OF-INTERVIEW EVALUATOR CALL DOES NOT FIT. This is measured, not feared.

Scoring the whole transcript in one call is the obvious design and **it is ruled out by a number
this project already took**. AGENT-INTERVIEWER-SPEC §6, measured 2026-08-06 with `tiktoken`:

```
full transcript at probe 10, verbose answers    10,274 tokens   <- OVER the 8,000 TPM ceiling
```

Add `case_world` (~1,200) and the rubric prompt and it is not close. **Per-answer scoring is
FORCED by the per-minute ceiling, not chosen for freshness.** PRD §3 already says "after each
answer"; this is the measurement that makes it non-negotiable.

**Compute the fit at the LAST turn before building the loop, not after.** That instruction is
verbatim from 3.5.4's traps, where it was the difference between a design that fit and one that
did not.

### 3. THE EVALUATOR MUST NOT REUSE THE INTERVIEWER'S TRANSCRIPT WINDOW.

`_windowed_transcript` is first answer plus last 4 turns. On 2026-08-07 that window is why the
Interviewer **missed a self-contradiction planted four turns apart** — the earlier turn had fallen
out of context. That is an acceptable trade for a probe, which only needs the last answer.

**It is not acceptable for a score.** "Sharpens a thesis under pushback" (point of view, anchor 4)
and "adapts structure to the prompt" (structural clarity) are properties of the ARC of an
interview, and a 4-turn window cannot see an arc. An Evaluator scoring per answer through a
keyhole will systematically under-score exactly the two dimensions that already get least evidence.

**So per-answer scoring needs a running summary, not a window** — carry forward the scores and
evidence already assigned, not the raw turns. That is cheap, it fits, and it is what makes an arc
visible without re-sending the transcript.

---

## 🔴 Decisions this phase inherits and must not relitigate

| Decision | Source |
|---|---|
| Five dimensions, 1 to 4, equally weighted, no offsetting | PRD §7 |
| **Every score carries a verbatim quote, enforced in the SCHEMA** | PRD §8 |
| Anchors shift with `assessed_level`; the dimensions do not | PRD §7 |
| Framework narration penalty, recorded **separately** from the five scores | PRD §7 |
| **No radar chart.** Horizontal bars, numeric value always visible | PRD §8 |
| **Blind mode**: defaults to scores-visible, toggles to coverage-only, full reveal at the end | PRD §8 |
| `case_world` is immutable; the Evaluator READS it and never writes | ARCHITECTURE §2 |
| Agents default to `fast` unless measured otherwise | CLAUDE.md calibration 2026-08-02 |

**PRD §3 assigns the Evaluator `deep`. Treat that as unmeasured.** The Planner carried the same
assignment and 3.5.3 measured it down to `fast` once its schema shrank. `AnswerEvaluation` is five
scores plus five quotes, which is smaller than `QuestionPlan` ever was. **Measure it; do not
inherit it.**

---

## 🔴 Traps carried forward. Every one is a recorded failure from this project.

- **`await_candidate` contains only `interrupt()` and its return.** It has zero `rest_insert` calls
  and zero LLM calls today. An Evaluator that scores "after each answer" is the most tempting reason
  yet to put work there. **Do not.** On resume LangGraph re-runs the node from the top, so an
  evaluator call there would fire twice per answer and the duplicate would be invisible in
  `answer_evaluations` — only `app.llm`'s call log would see it.
- **Re-run every live test file that builds a graph**, not just the one you edited. Story 3.2 broke
  `test_confirm_level.py` this exact way and it shipped, because only the edited file was re-run.
- **A green suite is not coverage.** On 2026-08-07 the level-to-category mapping was fully inverted
  with 374 tests green, because every assertion covered determinism and membership and none covered
  the mapping. **Ask what a test would say if the behaviour were backwards.**
- **Deselected is not passed.** Read the deselected count.
- **Classify every 429 before calling it a defect**, and grep for `tokens per day` before believing
  a failure. Three separate mostly-red runs have been rate limiting.
- **A dash reaching a candidate is a real defect.** `normalize_dashes` (2026-08-07) cleans the
  interview surface at the graph boundary. **The scorecard is a NEW surface** and must call it too,
  or use `stripDashes` on render. **Rows written before 2026-08-07 carry raw U+2011** — the
  scorecard renders historical transcripts, so it cannot assume clean input.

---

## Stories

### 4.1 The rubric, golden fixtures, and the assertion harness — ✅ DONE 2026-08-08

**Written blind, before the agent**, same as 1.3a and 3.1. The assertions are the deliverable; the
suite is deliberately RED at the end of this story.

- [x] `AnswerEvaluation` schema: five `DimensionScore` entries, each `{dimension, score 1-4,
      evidence_quote, reasoning}`, plus `framework_narration: bool` recorded separately, plus
      `not_assessed: list[str]` for dimensions with no evidence.
- [x] 6 to 8 golden fixtures at `tests/golden/evaluator/`, each a `(case_world, transcript,
      assessed_level)` triple with expected properties. **Reuse the planner's `case_world`
      fixtures by pointer, never by copy** — the rule spec §5 already sets for the interviewer suite.
- [x] **The corpus is free and it already exists.** Karthik's 2026-08-07 transcript is in
      `transcript_turns` for session `ac569e9b-db6a-4a17-9a73-b5c1ed43e59f`: one question, four
      clarifications, eight probes, nine candidate turns, with **known** properties — three
      dimensions evidenced, two not. Lift it as fixture 1.
- [x] Assertions: **every score has a non-empty `evidence_quote`** · **every quote appears VERBATIM
      in the transcript it was scored from** (the falsifiable version of PRD §8, and the one
      assertion this suite exists for) · a dimension in `not_assessed` carries **no** score · the
      same answer scores lower at a higher `assessed_level`.
- [x] **Falsify the verbatim-quote assertion** against a hand-written evaluation containing a quote
      that is *nearly* right (a word changed). If a paraphrase passes, the assertion is decorative.

**Acceptance:** the suite runs, is red, and the quote assertion has been **observed failing** on a
paraphrase. Zero tokens.

### 4.2 The Evaluator agent — ✅ DONE 2026-08-09

- [x] `app/agents/evaluator.py`, `evaluate_answer(case_world, question, answer, assessed_level,
      prior_scores, *, role="fast")`. Pure function: no DB, no session, no writes — same contract as
      `answer_clarification` and `generate_probe`.
- [x] `prior_scores` is the running summary from § "What the live interview already decided" #3:
      the dimensions already evidenced and their quotes, NOT the raw transcript.
- [x] **Measure `fast` against `deep` on two fixtures before assigning a role.** Record the number.
      **Measured: `deep` 2/2, `fast` 1/2**, same two fixtures, identical input. **Stayed on `fast`
      anyway** — one `deep` sample is not a measurement (`deep` flaps, `fast` is deterministic,
      DEV-STATE 2026-08-08), and the single disagreement is a rubric definition question, not a
      capability gap. See DEV-STATE § Decisions 2026-08-09.
- [x] **Compute the token fit at the LAST answer** (nine candidate turns, verbose) before wiring
      anything, and write the arithmetic into the docstring the way
      `_TRANSCRIPT_TAIL_TURNS` does. Comment block above `_EVALUATION_SYSTEM_PROMPT`, and made
      executable by `tests/test_evaluator_budget.py` — offline, zero tokens.
- [x] A dimension with no supporting evidence goes to `not_assessed`. **The prompt must make
      declining to score a first-class success, not a failure** — the false-premise regression of
      2026-08-07 is the standing proof that an agent told only to be helpful will oblige.

**Acceptance:** ✅ `apm_consumer_world_full_coverage` green on `fast`; both fixtures green on
`deep`. Role measured. **One open rubric question this story surfaced and did not decide** — see
DEV-STATE § Decisions 2026-08-09 #8.

### 4.3 The graph edge, and the write — ⬜

- [ ] `evaluate_answer_node` after the candidate's answer is recorded, **never inside
      `await_candidate`**.
- [ ] Writes `answer_evaluations`. **The DDL already decided the shape — read it before designing
      one.** From `migrations/0001_initial_schema.sql`:

```sql
turn_idx       int  not null,
dimension      text not null,
score          int  not null check (score between 1 and 4),
evidence_quote text not null check (length(evidence_quote) > 0)
```

  Three consequences, none of them optional:

  - **One row per (turn, dimension).** Not a JSON payload.
  - **PRD §8's "enforced at the schema level" is enforced in POSTGRES**, not just pydantic. A score
    without a quote cannot be written. That is stronger than the PRD claims and it is free.
  - 🔴 **`score` is `not null`, so an unassessed dimension CANNOT BE REPRESENTED as a row.** It is
    represented by the **absence** of one, which works and needs no migration. **Do not add a
    nullable score or a sentinel value** to make `not_assessed` storable — a nullable score would
    silently weaken the constraint that makes this table trustworthy. The reader joins against the
    five known dimensions and treats a missing row as not assessed.
  - **`framework_narration` and `reasoning` have NO column.** Either they get a migration, or they
    are not persisted. **Decide before 4.2 writes the schema**, not after.
- [ ] **Assert exactly one Evaluator LLM call per answer**, on `app.llm`'s log, not on state. Same
      rule as `test_confirm_level.py`'s and the probe's — a duplicate is invisible in the table.
- [ ] **Falsify it** by building the wrong graph, the way `falsify_single_call.py` does.
- [ ] **Re-run every live test file that builds a graph.**

**Acceptance:** the single-call assertion **observed failing** against a deliberately wrong graph.

### 4.4 The scorecard — ⬜

- [ ] Horizontal bars, numeric value always visible. **No radar chart** (PRD §8).
- [ ] Every bar expands to its `evidence_quote`. A score the candidate cannot trace to a sentence
      they said is the thing this design exists to prevent.
- [ ] **`not_assessed` dimensions render as "not assessed", never as a zero or an empty bar**, and
      **no overall score is shown when any dimension is unassessed.**
- [ ] Blind mode toggle (PRD §8): defaults to scores-visible, swaps to coverage-and-progress only,
      full reveal at the end.
- [ ] `stripDashes` on every rendered string. **Historical rows carry raw U+2011.**
- [ ] Full loading / empty / error states. Labels above inputs. Geist + Geist Mono, mono for every
      number. Phosphor at `weight="regular"`.
- [ ] **No em-dashes in any copy.**

**Acceptance:** `npm test -- --run` green, including a test that a `not_assessed` dimension shows no
number and suppresses the overall score.

---

## Automated tests

| File | Asserts |
|---|---|
| `tests/golden/evaluator/` | Every score has a verbatim quote **found in the transcript** · `not_assessed` carries no score · the same answer scores lower at a higher level · a paraphrased quote FAILS |
| `tests/test_evaluate_answer.py` (live) | Exactly one Evaluator call per answer · the node is not in `await_candidate` · rows land in `answer_evaluations` |
| `tests/test_conduct_loop.py` (live) | Still green after the new edge — **the graph is a shared object** |
| `frontend/src/**/*.test.ts` | Bars render with visible numbers · a quote expands · `not_assessed` shows no number and suppresses the overall · blind mode hides scores · dashes stripped |

**Pace any new live file**, per `_paced()` in `test_conduct_loop.py`. Unpaced live files have never
produced a readable red run in this project.

---

## Phase gate

1. **`pytest tests -m "not live"` green.** Free, seconds. **Run it FIRST**, not at handover.
2. **One Evaluator golden case as a smoke.** Not the full set.
3. **The verbatim-quote assertion observed FAILING on a paraphrase**, and the single-call assertion
   observed failing against a wrong graph. Neither is inherited.
4. **A scorecard Karthik reads and believes** — specifically, whether the evidence quotes justify
   the scores. His judgment, and it cannot be delegated.

---

## Handoff

*To be filled with observed output. Nothing goes here that was not run.*

**Needs Karthik's eyes**
- **Whether an unassessed dimension is acceptable at all**, or whether Phase 3.5 must steer coverage
  first. Today a real interview evidenced three of five.
- Whether the level anchors feel right: the same answer should be a Hire at PM and a No Hire at
  Senior PM, and only he can say whether it lands.
- Whether the coaching report (Phase 5) wants the Evaluator's `reasoning` field or its own pass.
