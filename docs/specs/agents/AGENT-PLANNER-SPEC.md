# Agent spec — Interview Planner

> **🔴 REWRITTEN IN PART BY STORY 3.5.3, 2026-08-06. Read this box before anything below it.**
>
> Three sections below are **superseded** and left in place for the audit trail, per CLAUDE.md's
> rule against rewriting history:
>
> | Section | What actually holds now |
> |---|---|
> | **§2 output schema** | The agent no longer returns 5-7 free-form questions. It returns **slot fills** for a shape drawn from `app/questions/shapes.py`, plus `grounded_in`, plus a **probe ladder** of 5-8 angles, plus `intent`. **The question string is built in Python** by `shape.template.format(**slots)` — the model never writes it. That is what makes a decorative statistic structurally impossible rather than merely banned |
> | **§3 coverage** | **Rubric coverage moved from questions to the probe ladder.** One question cannot be the `primary_dimension` of five dimensions. All five must appear across the ladder. `minutes` / `total_minutes` no longer drive anything: `decide_next` owns time via `_TIME_BUDGET_MINUTES` |
> | **§6 the model question** | **Answered: `fast`, measured 2026-08-06.** The `deep` requirement of 2026-08-04 was a function of `QuestionPlan`'s size, not this agent's difficulty. Golden smoke passed on `fast` with no retry |
>
> **§5's assertions are extended, not replaced.** `missing_grounding`, the vacuity floor, and the
> cross-world genericness control all still hold and still matter. Three new ones join them, built
> in story 3.5.2 **before** this prompt changed: `decorative_statistic`, `is_recitation_shaped`,
> `matches_no_shape`. All three are asserted on the generated question in
> `tests/golden/planner/test_golden.py`.
>
> **§8's first open question is CLOSED.** *"Should `probe_angles` be planned at all, or generated
> live?"* — pre-written angles cannot fill 45 minutes and cannot respond to what the candidate
> actually said. The Planner now plans a **ladder of angles**; the Interviewer generates each probe
> live against the transcript (story 3.5.4).
>
> **Category selection is data, not a model decision.** Each curated world declares
> `suits_categories`, so nothing can ask a pricing question about Reddit's AI-licensing tension.
>
> Full detail and observed output: [PHASE-3.5-SPEC.md](../PHASE-3.5-SPEC.md) § 3.5.3.

**Written 2026-08-02, before the prompt exists**, per the story 1.3 split. The golden fixtures in
story 2.5 are written against this document and blind to the prompt.

**Status:** contract only. `app/agents/planner.py` does not exist yet (story 2.6).

**This is a thin agent with one hard requirement, and everything else is secondary: every question
must be answerable from the case world.** A question that assumes facts `case_world` does not
contain is the defect that surfaces in Phase 3 as the Interviewer improvising — which
ARCHITECTURE §9 lists as a failure mode whose only detection is *manual*, five adversarial
clarifying questions at the Phase 3 gate. **This spec exists to catch it here, mechanically, where
it is cheap.**

---

## 1. Contract

| | |
|---|---|
| **Reads from state** | `assessed_level: str` (confirmed) · `case_world: dict` |
| **Writes to state** | `question_plan: list[dict]` |
| **Side effects** | One `agent_events` row on start and on completion |
| **Immediately preceded by** | `generate_case_world` |
| **Immediately followed by** | the `conduct_round` subgraph (Phase 3) |
| **Model** | `deep`, per ARCHITECTURE §4. Names come from `app/config.py` |

**Pure function, node owns side effects.** `plan_interview(assessed_level, case_world, *, role)`
returns a validated `QuestionPlan`. No database, no session — the golden cases call it directly.

**🔴 `case_world` is READ ONLY. This agent is the immutability rule's first real test by a
downstream agent** (ARCHITECTURE §2). Story 2.6 asserts `case_world` is byte-identical across the
node, and that assertion is not decoration: it is the first chance to catch a downstream agent
mutating the artifact every later agent depends on.

---

## 2. Output schema

Sketch. Story 2.6 implements it; story 2.5 writes assertions against it.

```python
RUBRIC_DIMENSIONS = Literal[
    "business_model_fluency",
    "market_accuracy",
    "decision_quality",
    "structural_clarity",
    "point_of_view",
]

class PlannedQuestion(BaseModel):
    idx: int
    question: str                      # asked verbatim; revealed whole, never streamed
    intent: str                        # what this is trying to surface, for the Evaluator
    primary_dimension: RUBRIC_DIMENSIONS
    probe_angles: list[str]            # 2-3 followups if the answer comes back thin
    grounded_in: list[str]             # case_world facts/entities this depends on
    minutes: int

class QuestionPlan(BaseModel):
    questions: list[PlannedQuestion]   # 5-7
    total_minutes: int                 # <= 45, and see §3
```

**🔴 `grounded_in` is the field that makes this agent testable, and it is the whole design.** Each
question declares which pieces of the case world it depends on. That converts "is this question
answerable?" from a judgment call into a **set-membership check**: every entry must appear in
`case_world`, most usefully in its `supporting_facts`, `company.name`, or a competitor name.

Without it, the grounding assertion would have to parse natural language and would be
unfalsifiable. With it, story 2.5 gets a mechanical check and a positive control that rejects a
question naming an entity the world does not contain.

**The obvious objection, and the answer.** A model can populate `grounded_in` with plausible-looking
entries that do not appear in the world — which is precisely why the assertion checks them against
`case_world` rather than trusting them. A fabricated `grounded_in` entry FAILS the case. This is
the same shape as the Resume Analyst's verbatim-quote assertion, which is the most valuable
assertion in that suite.

---

## 3. Coverage and time

**Rubric coverage.** `docs/PRD.md` §7 defines five equally weighted dimensions. **Each must be the
`primary_dimension` of at least one question**, or the Evaluator has nothing to score on it and
`dimension_coverage` never fills. Cross-reference the PRD; do not restate the rubric here, or the
two will drift.

With 5-7 questions and 5 dimensions, coverage is achievable and one or two dimensions get a second
question. **Which dimension gets doubled should follow the level**, not be arbitrary.

**Time.** The interview is 45 minutes (PRD §1). `total_minutes` must not exceed it, and should
leave room — real interviews overrun on followups, and `probe_angles` exist precisely to be used.
**Plan for roughly 35-40 minutes of questions.**

**What happens when time runs short is NOT this agent's problem.** `decide_next` in Phase 3 is
deterministic and reads elapsed time from state (ARCHITECTURE §3). The Planner produces an ordered
plan; the conduct loop decides how much of it gets asked. **Order the questions so that truncation
degrades gracefully** — the most diagnostic question must not be last.

---

## 4. Constraints on the prompt

- **Questions are asked verbatim and revealed whole**, never token-streamed (PRD §8). So the
  `question` string is candidate-facing copy: **no em-dashes**, no raw JSON, no meta-commentary.
- **No framework narration in the question.** PRD §7 penalises candidates who recite frameworks;
  a question that invites it ("walk me through your CIRCLES analysis") manufactures the failure it
  then scores.
- **Questions must be specific to this world.** "What would you do?" fits any case. A question that
  would survive being pasted into a different case world is a defect, and §5 asserts it.
- **No fake-round numbers and no generic names**, same as the Case Architect — a question quoting
  "roughly 50% of users" reintroduces the tell the case world avoided.
- **Level calibration shifts the bar, not the dimensions** (PRD §7). The five dimensions are the
  same at APM and GPM; the questions' scope is not.

---

## 5. Golden cases

**Written blind in story 2.5.** Input is `(assessed_level, case_world)`.

**🔴 Corrected 2026-08-02: story 2.2's fixtures are candidate *profiles*, the Case Architect's
INPUT. They are not case worlds and cannot be reused directly here.** The Planner's fixtures must
be **hand-written case worlds** conforming to §2 of the Case Architect spec — which is correct for
blindness anyway, since a generated world would require the agent that does not exist yet.

**Two requirements that tie the suites together instead:**

1. **Name each fixture after the 2.2 scenario it corresponds to** (`apm_consumer_world` for
   `apm_consumer`, and so on), so the two suites describe the same seven situations.
2. **Every hand-written case world MUST pass the Case Architect's own universal assertions** in
   `tests/golden/case_architect/assertions.py`. This is free, needs no LLM, and buys two things: it
   proves the Planner is being tested against realistic input, and it is a **positive control on
   2.2's assertions themselves** — a hand-built world a human considers good should pass them, and
   if it does not, one of the two suites is wrong.

| # | Fixture | Asserts |
|---|---|---|
| 1 | `apm_consumer_world` | Questions are feature-scoped, not portfolio-scoped |
| 2 | `pm_b2b_world` | Product-area scope |
| 3 | `senior_pm_platform_world` | Questions carry ambiguity, not a single right answer |
| 4 | `gpm_portfolio_world` | At least one question attaches to a business outcome |
| 5 | `sparse_world` | A thin case world still yields grounded questions rather than generic ones |

**Universal assertions, every case, each with the positive control that must go RED:**

| Assertion | Positive control that must go RED |
|---|---|
| **Every `grounded_in` entry appears in `case_world`** | A question grounded in "Northwind Logistics" when no such entity exists |
| All five rubric dimensions are a `primary_dimension` at least once | A plan whose questions are all `decision_quality` |
| 5-7 questions | A plan of 1 question, and one of 20 |
| Each question has 2-3 `probe_angles` | A question with none |
| `total_minutes` <= 45 and matches the sum of `minutes` | A plan claiming 30 whose questions sum to 70 |
| No em-dashes in any `question` string | A question containing one |
| No fake-round numbers, no banned-register names | A question citing "50% of customers" |
| **Not generic** — see below | A plan of questions that would fit any case world |
| **Vacuity floor** — non-empty strings, non-empty lists | A plan of empty questions with empty `grounded_in` |

**🔴 THE VACUITY FLOOR IS THE LESSON OF STORY 1.3a AND IT APPLIES DOUBLY HERE.** A question with
an empty `grounded_in` list passes the grounding assertion vacuously, because there is nothing to
check against the world. **`grounded_in` must be non-empty on every question**, or the suite's most
important assertion is dead exactly as `missing_verbatim_quotes([])` was.

### The genericness assertion, which is the hard one

**A plan of questions that would suit any case world is the failure mode most likely to ship**,
because it looks fine in isolation. Approximate it mechanically rather than perfectly:

- Require each `question` string to contain **at least one proper noun or figure drawn from
  `case_world`** — the company name, a competitor, or a number from `metrics`.
- The positive control is the honest test: take a plan generated for fixture 1, run the assertion
  against fixture 4's case world, **and require it to FAIL.** A plan that passes against a world it
  was not written for is generic by definition.

**That cross-world control is the single most valuable test in this suite.** It is cheap, it needs
no LLM to run once the plans exist, and it directly measures the property that matters.

---

## 6. The model question

`deep`, per ARCHITECTURE §4. **This is the third agent to produce evidence** on an assignment open
since 2026-07-30. Kept informal by decision on 2026-08-02, so no acceptance box forces a dual-model
run — but **record flap counts honestly**, because the Planner is a *smaller* generation task than
the Case Architect and might be a legitimate `fast` candidate even if the Case Architect is not.

**Prompt budget: this agent's input is LARGE.** It receives the whole `case_world`, which is the
biggest input any agent in the product takes so far. Groq reports `Requested = prompt + input +
max_tokens` against an **8,000 TPM ceiling**, and `app/llm.py` sets `max_tokens=4096`. **Compute
the budget before writing the prompt**: a 1,200-token case world plus a 2,500-token prompt plus
4,096 is already 7,800. **This agent is the most likely in the product to be structurally unable to
run on the free tier.** Measure it in story 2.5, not after the prompt is written.

---

## 7. Failure modes to design against

| Failure | Why it matters | Guard |
|---|---|---|
| **A question the case world cannot answer** | Phase 3's Interviewer improvises, contradicts itself, and only a manual check catches it | `grounded_in` set-membership, §5 |
| **Empty `grounded_in`** | The grounding assertion passes vacuously — 1.3a's exact bug | Non-empty floor, asserted separately |
| **Generic questions** | The interview stops being about this case; looks fine in review | Cross-world control, §5 |
| **A dimension never covered** | The Evaluator cannot score it and the scorecard has a hole | Coverage assertion against the PRD's five |
| **Writes `case_world`** | Breaks the immutability rule every downstream agent depends on | Story 2.6 asserts it is unchanged across the node |
| **Reads level from the case world** | Discards the candidate's correction, same trap as the Case Architect | Read `assessed_level` from state |
| **Plan overruns 45 minutes** | The interview truncates and the last question is never asked | `total_minutes` assertion, plus ordering so truncation degrades gracefully |
| **Framework-inviting questions** | Manufactures the failure the rubric then penalises | Named in the prompt constraints |
| **Input too large for the TPM ceiling** | The agent cannot run at all on the free tier, regardless of pacing | §6, computed before the prompt is written |

---

## 8. Open questions

- **Should `probe_angles` be planned at all, or generated live by the Interviewer?** Planned here
  because Phase 3's Interviewer runs on `fast` and a probe is where improvisation is most likely to
  contradict the world. Revisit if they read as stilted at the Phase 3 gate.
- **Does `intent` earn its place**, or is it prose nobody reads? It is written for the Evaluator in
  Phase 4. If Phase 4 does not use it, delete it — no fields without a second caller.
- **Should the plan be regenerated if the candidate corrects their level?** Currently no: the
  correction lands before `generate_case_world`, so both downstream agents already see the
  corrected level. This only matters if a later phase allows re-levelling mid-interview.
- **Is 5-7 questions right for 45 minutes?** Taken from the PRD's interview length, not measured.
  The Phase 3 gate is the first real evidence, and this number should move if it is wrong.
