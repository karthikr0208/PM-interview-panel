# Agent spec — Evaluator

**Written 2026-08-09, AFTER the agent, not before it.** That is a deviation from this project's own
habit (the Resume Analyst, Planner and Interviewer specs were all written before their prompts) and
it is deliberate: PHASE-4-SPEC.md carried the full contract through stories 4.1 to 4.3, so writing a
second copy up front would have been a duplicate to keep in sync, not a design. This file exists
because DEV-STATE listed it as owed once the contract stopped moving.

**Everything here is measured or decided, not projected.** Where a number appears, the run that
produced it is named.

---

## 1. Contract

```python
async def evaluate_answer(
    case_world: dict,
    question: str,
    answer: str,
    assessed_level: str,       # APM | PM | Senior PM | GPM
    prior_scores: list[dict],
    *,
    role: Role = "fast",
) -> AnswerEvaluation
```

`app/agents/evaluator.py`. **Pure function**: no DB, no session, no writes, no `agent_events` row —
the same contract as `answer_clarification` and `generate_probe`. The golden cases call it directly
with no session and no database, so a DB call in here breaks every one of them. The graph node and
the `answer_evaluations` write live in `app/graph/build.py`'s `_make_evaluate_answer_node`.

`case_world` is **read only** (ARCHITECTURE §2, immutable after Phase 2).

The positional order is fixed by `tests/golden/evaluator/test_golden.py`'s call site, which was
written blind in story 4.1 before the function existed.

### `prior_scores` is a RUNNING SUMMARY, and that is the whole design

Not the transcript. Not a window over it. A list of
`{dimension, score, evidence_quote}`, one entry per dimension already evidenced, later evaluations
overwriting earlier ones for the same dimension.

**Bounded at five entries however long the interview runs.** This is why the call fits the ceiling
and why its cost does not grow with turn count, unlike the Interviewer's window.

🔴 **The Interviewer's `_windowed_transcript` must NOT be reused here.** It is the first answer plus
the last 4 turns, and on 2026-08-07 that window is exactly why the Interviewer missed a
self-contradiction planted four turns apart. That is an acceptable trade for a probe, which only
needs the last answer. It is not acceptable for a score: "sharpens a thesis under pushback" and
"adapts structure to the prompt" are properties of an ARC, and a 4-turn keyhole cannot see an arc.
The running summary is what makes the arc visible without re-sending the transcript.

---

## 2. Output schema

`AnswerEvaluation`, in `app/agents/evaluator.py`:

```
dimension_scores: list[DimensionScore]      # {dimension, score 1-4, evidence_quote, reasoning}
framework_narration: bool                   # PRD §7, recorded SEPARATELY from the five scores
not_assessed: list[str]
```

A `model_validator` enforces three invariants **in the schema**, going further than PRD §8's own
quote-per-score guarantee:

1. No dimension is scored twice.
2. No dimension is both scored and `not_assessed` — that is a score wearing a "no evidence" label
   at the same time, incoherent rather than merely inconsistent.
3. **Every one of the five dimensions is accounted for exactly once**, scored or `not_assessed`,
   never silently dropped. A dimension that quietly vanishes leaves an aggregate that misreports
   itself as complete.

`evidence_quote` and `reasoning` both carry `min_length=1`. Whitespace-only is the golden suite's
job (`blank_or_short_fields`), matching this project's `min_len` content-floor convention.

---

## 3. The rubric, and what `not_assessed` actually means

Five dimensions, 1 to 4, equally weighted, no offsetting (PRD §7). Anchors shift with
`assessed_level`; the dimensions do not.

### 🔴 The rule Karthik set on 2026-08-09, and it is not about the dimension

`not_assessed` means **the topic never came up**. It does not mean the candidate handled it badly.

| The candidate… | Result |
|---|---|
| was asked to choose, laid out the options, never picked one to defend | **2** |
| was asked to choose, did not even lay out the options | **1**, the floor |
| was never asked, and the topic never came up | **`not_assessed`** |

*"A candidate is expected to make a choice and defend it."* Dodging a question that demanded one is
**a failure the evaluator watched happen, not a coverage gap.**

**The scale stays 1-4.** The ruling was first phrased as "scored 0", which is not representable:
`answer_evaluations.score` is `not null check (score between 1 and 4)` and `DimensionScore` is
`Field(ge=1, le=4)`. Clarified to mean the floor. **No migration was taken, and none should be** — a
nullable score or a sentinel would weaken the one constraint that makes that table trustworthy.

### Why `not_assessed` has to exist at all

A real interview on 2026-08-07 produced `dimension_coverage` of
`business_model_fluency 4 · decision_quality 4 · structural_clarity 1 · market_accuracy 0 ·
point_of_view 0`. **Five dimensions, four probes, so at least one dimension has zero targeted
coverage every interview, by construction.** The Evaluator will routinely be handed a transcript and
asked about something nothing was said about.

🔴 **A 1-to-4 on a dimension with no evidence is a fabricated number wearing a rubric's authority.**
Declining is a first-class success, and the prompt says so in as many words.

🔴 **`dimension_coverage` is NOT ground truth for this agent.** It counts what the Interviewer
PROBED, not what the candidate EVIDENCED. Golden fixture 1's expectation was inherited from it and
is **known wrong** on the transcript's own text: turn 21/23 is a thesis sharpened under pushback and
turn 25 cites the world's 8.6% growth figure. See §7.

---

## 4. Constraints on the prompt

`_EVALUATION_SYSTEM_PROMPT`, four ordered steps. **The order is load-bearing**, the same lesson as
the Interviewer's clarification prompt, which only stopped accepting false premises once
"contradict first" was moved to step 1.

1. **Decide what the answer gives evidence for**, before scoring anything. Carries the
   topic-never-came-up distinction from §3.
2. **Quote before you score.** The quote is copied from the candidate's answer **character for
   character**, including typos and odd punctuation, and is checked byte for byte downstream. If no
   sentence supports the score, go back to step 1.
3. **Score against the anchors, at this candidate's level.** Includes the explicit instruction that
   the same answer scores LOWER at a higher level.
4. **Framework narration, recorded separately**, and it must never move any of the five scores.

Two rules were added on 2026-08-09 after a live run, and both are in the prompt because a live
output made them necessary, not because they were anticipated:

- **Narrating a framework is not structure.** `fast` scored an answer that recited RICE, build
  versus buy and a 2x2 as `structural_clarity=4` while setting `framework_narration=False`. It had
  treated borrowed shape as organisation, which is the exact thing the flag exists to catch.
- **`framework_narration` is TRUE on any of**: naming a framework and listing its steps, announcing
  a method never filled in with the company's own numbers, or naming two or more frameworks in one
  answer. The original wording required walking steps "out loud" and was too narrow.

---

## 5. Golden cases

`backend/tests/golden/evaluator/`. **7 fixtures, written blind in story 4.1**, before the agent, and
the suite was deliberately RED at the end of that story.

Fixtures reuse the planner's `case_world` fixtures **by pointer, never by copy** — with one
documented exception, `karthik_live_airbnb_senior_pm`, which carries its world inline because it is
the one place that world exists on disk.

### The assertion this suite exists for

`quotes_not_found_verbatim` — every `evidence_quote` must be an **exact substring** of the flattened
transcript. Deliberately not fuzzy and not semantic: PRD §8's "verbatim" is falsifiable only if it
means byte for byte.

🔴 **Falsified, not assumed.** A hand-written evaluation with ONE word changed ("runs" to
"operates") was observed FAILING this check in story 4.1. Without that, the assertion would be
decorative — the same class of bug `ungrounded_figures` shipped in its first, too-loose version.

### Smoked live 2026-08-09

```
GOLDEN_ROLE=fast   apm_consumer_world_full_coverage   PASS   retry_fired=True
                   sparse_world_framework_narration   PASS   (after the §4 prompt rules)
GOLDEN_ROLE=deep   both                               PASS
```

---

## 6. The model question — MEASURED, not inherited

**Runs on `fast`.**

PRD §3 assigns the Evaluator `deep`. **That assignment was never measured**, and the Planner carried
the identical one until 3.5.3 measured it down. Measured here 2026-08-09, two fixtures, identical
input: **`deep` 2/2, `fast` 1/2** — and `fast` was kept anyway, for three reasons that outweigh one
sample:

- **One `deep` run is not a measurement.** `deep` flaps against identical input; `fast` is
  deterministic (DEV-STATE 2026-08-08). A single green `deep` is exactly the evidence this project
  has learned not to trust.
- The one disagreement was a **rubric definition question, not a capability gap** — `fast` produced a
  defensible reading of an ambiguous rule, and the rule was then written down (§3).
- `deep` costs several times the budget on the model whose daily cap is what stops work.

### The token budget, computed at the LAST answer before the loop was built

tiktoken `o200k_base`, `Requested = system + human + max_tokens` against the **8,000 TPM** ceiling.
`max_tokens` is part of the request size on Groq, not a cap on the reply.

```
system prompt                                       1,378
largest case_world (openai.json)                    1,392
prior_scores, five dimensions, score + long quote     283   (438 with reasoning)

highest real fixture                                4,783   headroom 3,217
stress: largest world + 500-word answer + full prior 5,398   headroom 2,602
```

The **full transcript measured 10,274** on 2026-08-06 and is over the ceiling. **That is what forces
per-answer scoring** — it was never a freshness preference. `tests/test_evaluator_budget.py` makes
this executable offline at zero tokens, with a vacuity floor pinning that the measured message
actually contains the answer, the world and the summary.

`max_tokens=2048`. Do not argue it down from the output schema's size: on gpt-oss it is a
reasoning-plus-output budget and reasoning scales with the INPUT. That reasoning is what produced the
wrong 1024 for `generate_probe`.

---

## 7. Failure modes to design against

| Failure | Guard |
|---|---|
| A score with no quote | `min_length=1` in pydantic **and** `length(evidence_quote) > 0` in Postgres |
| A paraphrased quote | `quotes_not_found_verbatim`, observed failing on a one-word change |
| Scoring a dimension nothing was said about | `not_assessed`, and the prompt makes declining a success |
| **Declining a dimension the question demanded** | §3's rule, pinned by `_check_sparse_framework_narration` |
| A dimension silently dropped | The `model_validator`'s account-for-all-five invariant |
| **Two evaluations per answer** | One-call assertion on `app.llm`'s LOG, falsified by `scripts/falsify_evaluate_single_call.py` (wrong graph logs 2) |
| A dash reaching the candidate | `normalize_dashes` on `reasoning` at the write boundary; `stripDashes` on render |

🔴 **`normalize_dashes` is applied to `reasoning` but NEVER to `evidence_quote`.** The quote is
compared against the transcript byte for byte and `_decide_next_node` writes the candidate's answer
unnormalised — normalising one side of that comparison would turn a faithful quote into a mismatch.

🔴 **The node is never inside `await_candidate`.** LangGraph re-runs that node from the top on
resume, so a call there fires twice per answer and **the duplicate is invisible in
`answer_evaluations`** — the second call adds no row a reader could tell apart. Only the call log
sees it.

---

## 8. Open questions

- 🔴 **Golden fixture 1's ground truth is known wrong and is not yet fixed.** Two separate problems:
  its `not_assessed` was inherited from `dimension_coverage` (which measures probing, not evidence),
  and the check describes the WHOLE interview while `test_golden.py` scores a single 28-token
  answer. Karthik ruled on 2026-08-09 to correct it to what the transcript evidences. **The fix
  belongs with an accumulation test, and wants a live run to settle the per-answer expectation** —
  it was deferred when the daily budget ran out.
- **Whether Phase 5's Coach wants `reasoning` or its own pass.** `reasoning` is persisted
  (migration 0004, nullable) partly so this stays answerable later. `framework_narration` is
  deliberately **not** persisted: it is one bool per answer while the table's grain is
  `(turn_idx, dimension)`, and an answer where all five dimensions are `not_assessed` writes zero
  rows and would lose it entirely.
- **Whether an unassessed dimension is acceptable at all**, or whether Phase 3.5 should steer probe
  coverage so it fires less often. PHASE-4-SPEC's own framing: ship the first, propose the second.
  Coverage can never be guaranteed, so `not_assessed` is required regardless.
