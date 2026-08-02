# Phase 2 — Case Architect and Interview Planner

**Goal:** a confirmed level produces a specific, self-consistent business world and a question plan
built against it, both persisted, both regression-gated, and neither invented twice.

**Why this phase exists.** Phase 1 ends with a candidate holding a level they agreed with. That
level buys nothing until there is something to be interviewed about. Four things make this the
right next slice:

1. **`case_world` is the load-bearing artifact of the whole product.** ARCHITECTURE §2 states the
   immutability rule: written exactly once, read by every agent downstream, written by none of
   them. It is what stops the Interviewer contradicting itself when a candidate asks a clarifying
   question forty minutes in. Getting it wrong here is not recoverable in Phase 3.
2. **The Planner is what makes the interview an interview** rather than six unrelated questions.
   It reads `case_world` and `assessed_level` and produces the spine the conduct loop walks.
3. **It is the second and third agents, so the golden-suite method gets its real test.** Phase 1
   built the method on one agent and discovered its failure modes the expensive way. This phase
   applies it deliberately from the start.
4. **It is the first independent signal on the `deep` model question**, which ARCHITECTURE §4 has
   left open since 2026-07-30 and which Phase 1 deferred with three flaps consciously accepted.

**Done when:** a candidate who confirms a level sees two more agents work in the orchestration
column, and the resulting `case_world` is specific enough that a PM reading it would believe the
company exists — persisted once, immutable, with a question plan built against it.

---

## 🔴 Before writing a line of prompt, read these

**Every one of these is a real, recorded failure from Phase 1, not a hypothetical.**

| Trap | Where it bit |
|---|---|
| **A denial assertion with no positive control passes when the mechanism is dead** | Story 1.3a: `missing_verbatim_quotes([])` returned `[]`, so an agent quoting **nothing** passed the suite's most important check on all eight cases. Every assertion in this phase needs a floor |
| **Write the fixtures blind, before the prompt** | Story 1.3 was split for exactly this. An agent writing both nudges a fixture whenever the prompt misses, and the suite stops gating at the moment it should start |
| **Classify every failure before believing it** | Twice, most of a red golden run was 429s. On 2026-08-02 all 8 full-suite failures were quota and one wore an `AssertionError` claiming `deep scored 0/10` |
| **A green run is one sample** | `temperature=0` does not make these MoE models deterministic. Three of the Resume Analyst's eight cases flap on identical input |
| **`_PACE_SECONDS` must grow with the prompt** | At ~2,900 prompt tokens against an 8,000 TPM bucket, 30s pacing recorded rate limits as prompt failures. **The Case Architect's prompt will be longer than the Resume Analyst's.** Compute the pacing, do not inherit it |
| **The node owns side effects, not the agent function** | `analyse_resume` stays pure so its golden cases run with no database. `generate_case_world` and `plan_interview` must follow the same split, or their golden cases need a session |

**Model names come from `app/config.py`, never from ARCHITECTURE §4**, which still names the
NVIDIA models the project left on 2026-07-31. Both agents here are `deep` per ARCHITECTURE's table;
`deep` is `openai/gpt-oss-120b` on Groq. **Keep every agent calling `get_llm(role)`.**

**Budget, measured 2026-08-02 and binding on this phase's plan:** 200,000 tokens per model per day,
a rolling window refilling ~138/min, invisible in every header. One eight-case golden run is
~32,000-60,000 depending on prompt length. **A full `make test` is ~120,000-130,000 on `deep` and
cannot share a day with anything else.** This phase adds two more golden suites to that total.
**Iterate on ONE case. Never run the full set to check a hunch.**

---

## Stories

Ordered by dependency. The spec-then-blind-fixtures-then-agent shape is deliberate and is the one
thing in this phase that must not be collapsed for speed.

### 2.1 `AGENT-CASE-ARCHITECT-SPEC.md`, written before the prompt — ✅ DONE 2026-08-02

**Acceptance**
- [x] `docs/specs/agents/AGENT-CASE-ARCHITECT-SPEC.md` exists and defines the output schema as a Pydantic model sketch, field by field, with which fields are required — §2, six models
- [x] It states the **side effects that belong to the node** (`agent_events` rows, the `case_worlds` write) and records that the agent function itself is pure — §1
- [x] It defines 5-10 golden cases spanning **all four levels**, since a GPM's case world should differ in scope from an APM's, and says what each asserts — §5, seven fixtures, plus §3's scope-by-level table
- [x] It names the **two design rules that bind this prompt**: no fake-round numbers, no generic placeholder names — §4, and §5 pairs each with the positive control that must go red
- [x] It states what makes a case world *bad* in a way a test can check, not only what makes it good — §5's universal-assertion table, §5's internal-consistency section, and §7's failure-mode table

**Written before the prompt exists, deliberately.** Story 2.2's fixtures are written against this
document and blind to the prompt, so the prompt cannot be tuned against them.

**The one field to read §2 for is `supporting_facts`.** It is 8-15 atomic statements and it is what
the Interviewer answers clarifying questions from in Phase 3. Without it, a clarifying question
forces improvisation, which is ARCHITECTURE §9's "Interviewer contradicts the case world" failure
and its only listed detection is manual.

**🔴 The two v1 AI-tells that reach past the UI into this agent's prompt** (ARCHITECTURE §8, via
CLAUDE.md). They bind harder here than anywhere else in the product:

- **No fake-round numbers.** `50%`, `$1M`, `99.99%` are tells. Generated financials must be organic:
  `31.4%` market share, `$4.7M` ARR, `18.2%` churn.
- **No generic names.** "John Doe", "Sarah Chan" and that register are banned, for company names,
  competitor names, and people.

**These are assertable and must be asserted**, not left to prompt prose. A regex for round numbers
and a banned-name list are both cheap. This is the first agent whose output a candidate reads as
fiction they must believe, so a tell here costs more than it does in a level rationale.

---

### 2.2 Case Architect golden fixtures and assertion harness — written BLIND — ✅ DONE 2026-08-02

**This story must not read the prompt, because the prompt does not exist yet.** Same split as story
1.3a, for the same reason, and that split is what caught 1.3a's vacuity bug.

**Acceptance**
- [x] 5-10 fixtures at `backend/tests/golden/case_architect/`, each a `(assessed_level, candidate_profile)` input, spanning all four levels — 7 fixtures as JSON, per spec §5
- [x] `cases.py`, `assertions.py`, `test_golden.py`, `test_assertions.py`, mirroring the Resume Analyst's layout
- [x] **The suite is deliberately RED**, failing only on `ModuleNotFoundError` for the agent module, with the import **lazy inside a fixture** so `pytest -m "not live"` still collects cleanly — **proven by RUNNING the live tests**, not inferred: 7 errors, all `ModuleNotFoundError`, in 0.07s at zero token cost, because the import fails before any call
- [x] **Every denial assertion has a positive control** proving it can fail — each row of spec §5's table has an accepting test and a rejecting test
- [x] **A vacuity floor**, the direct lesson of 1.3a — and **re-probed from scratch** rather than trusted: a lazy world is rejected on all six string fields, an honest one is accepted cleanly
- [x] `_PACE_SECONDS` computed, not copied — **90s**, with the arithmetic in a comment. **And it produced a hard ceiling story 2.3 must respect: max prompt ≈ 3,704 tokens ≈ 15,557 characters**
- [x] Asserts no fake-round numbers and no banned-register names, with positive controls on both

**The assertion that will be hardest, and is worth the effort: internal consistency.** A case world
that says the company has 40 employees in one field and describes a 200-person sales org in another
is the failure that will actually embarrass this product in front of a candidate. Consider asserting
cross-field relationships the schema cannot express.

---

### 2.3 The Case Architect agent and `generate_case_world`

**Acceptance**
- [ ] `app/agents/case_architect.py` exposes a **pure** `generate_case_world(assessed_level, candidate_profile, *, role)` returning a validated model, with **no database and no session** — the golden cases call it directly
- [ ] A `generate_case_world` **node** in `build.py` owns the side effects: an `agent_events` row on start, one on completion or error, and the `case_worlds` insert
- [ ] **`case_world` is written exactly once and is immutable thereafter** — ARCHITECTURE §2. Asserted, not asserted-by-comment
- [ ] The node runs after `confirm_level` and reads the **confirmed** level, including a candidate's correction, not the originally assessed one
- [ ] Golden cases pass, with the pass rate recorded and any flap recorded honestly against Phase 1's precedent
- [ ] Validate-retry behaviour recorded: `retry_fired` observed on every case, as in Phase 1

**🔴 The immutability assertion needs to be falsifiable, or it is decoration.** Prove it by
attempting a second write and confirming the failure, the same way story 0.6's idempotency
assertion was falsified against a deliberately wrong graph before being trusted. An immutability
rule nobody has watched reject a write is a comment.

**The confirmed-level trap is specific and easy to miss:** `confirm_level` writes the candidate's
chosen level back into `assessed_level`. A node that reads `candidate_profile` for level
information rather than `assessed_level` would silently ignore a correction, and every golden case
would still pass because they never exercise a correction. **Assert the correction path.**

---

### 2.4 `AGENT-PLANNER-SPEC.md`, written before the prompt — ✅ DONE 2026-08-02

**Acceptance**
- [x] `docs/specs/agents/AGENT-PLANNER-SPEC.md` exists, defining `question_plan`'s schema as a list of question objects — §2, `PlannedQuestion` and `QuestionPlan`
- [x] It defines how the plan **covers the rubric's dimensions**, so the conduct loop's `dimension_coverage` has something to count against. Cross-references `docs/PRD.md` §7 rather than restating it — §3, with the reason stated: a restatement would drift
- [x] It states plan length and its relationship to the 45-minute interview, and what happens when time runs short — §3. Truncation is `decide_next`'s job in Phase 3, so the Planner's obligation is **ordering the plan so truncation degrades gracefully**
- [x] 5-10 golden cases defined, keyed to case worlds from 2.2 so the two suites compose — §5, five fixtures reusing 2.2's worlds so a `CaseWorld` schema change breaks both loudly

**The design move worth reading §2 for is `grounded_in`.** Each question declares which case-world
entities it depends on, which turns "is this question answerable?" from a judgment call into a
**set-membership check** against `case_world`. A fabricated entry fails the case, exactly as a
fabricated quote fails the Resume Analyst.

**And §5's cross-world control is the cheapest high-value test in the phase:** run fixture 1's plan
against fixture 4's case world and **require it to FAIL.** A plan that passes against a world it
was not written for is generic by definition.

**The Planner is a thin agent with one hard requirement: the plan must be answerable from the case
world.** A question that assumes facts the case world does not contain is the defect that surfaces
as the Interviewer improvising in Phase 3, which ARCHITECTURE §9 lists as a failure mode with only
a manual detection. **Detect it here, where it is cheap.**

---

### 2.5 Planner golden fixtures and assertion harness — written BLIND — ✅ DONE 2026-08-02

**Acceptance**
- [x] Fixtures at `backend/tests/golden/planner/`, taking a `(assessed_level, case_world)` input — **five HAND-WRITTEN case worlds**, since 2.2's fixtures are candidate profiles, not worlds. Each named after its 2.2 counterpart
- [x] **Deliberately RED**, lazy import, same structure as 2.2 — proven by running: 5 errors, all `ModuleNotFoundError`, 0.05s, zero tokens
- [x] **The grounding assertion: every question must be answerable from the case world** — `grounded_in` set-membership against the world, with a positive control rejecting `Northwind Logistics`, an entity no world contains
- [x] Rubric dimensions are covered by the plan, asserted against the PRD's list rather than a copy
- [x] Vacuity floor — **and the trap it guards was demonstrated, not assumed.** `missing_grounding([], world)` returns `[]`, so an empty `grounded_in` passes the membership check vacuously; `empty_grounded_in` is the separate floor that catches it and runs first
- [x] Every denial assertion has a positive control — ten rows, each with an accepting and a rejecting test
- [x] **The cross-world control works**, and it is the cheapest high-value test in the phase: a plan grounded in `apm_consumer_world` passes against its own world and FAILS against `gpm_portfolio_world`
- [x] **The five hand-written worlds all pass story 2.2's universal assertions** — a free cross-suite positive control proving 2.2's checks accept a world a human considers good. **None needed relaxing**

**Budget measured, and it is NOT a blocker.** The spec's ~1,200-token estimate for a case world was
pessimistic; the largest real fixture is **937 tokens**. That leaves **max prompt ≈ 2,904 tokens
≈ 12,197 characters**, workable but **~22% tighter than the Case Architect's ~15,557**, as expected
since `case_world` is roughly 5x `candidate_profile`. **Story 2.6 must treat ~12,000 characters as
a hard ceiling, not a target.**

---

### 2.6 The Planner agent and `plan_interview`

**Acceptance**
- [ ] `app/agents/planner.py` exposes a pure `plan_interview(assessed_level, case_world, *, role)`
- [ ] A `plan_interview` node in `build.py`, after `generate_case_world`, owning its `agent_events` rows
- [ ] `question_plan` written to state; **`case_world` is read and NOT written** — assert this, since it is the immutability rule's first real test by a downstream agent
- [ ] Golden cases pass, pass rate recorded
- [ ] The graph runs `confirm_level → generate_case_world → plan_interview` end to end from a single resume, proven live

---

### 2.7 Orchestration column shows both new agents

**Acceptance**
- [ ] Both agents appear with the four states distinguished **by shape as well as colour**, matching 1.6b's existing pattern
- [ ] Activity reads as plain language, never raw JSON
- [ ] Updates arrive via Realtime on `agent_events`, reusing 1.6b's proven subscription
- [ ] **No em-dashes in any candidate-facing copy**, guarded by the existing grep
- [ ] **The Realtime startup race is re-checked**, not assumed. DEV-STATE 2026-08-01 resolved it as moot by reasoning, on the grounds that no agent writes an event immediately on session start. **These two agents write events sooner after confirm than the Resume Analyst does after upload**, which is exactly the condition that reopens it

**Do not ship a persona header.** The interviewer name is deferred to Phase 3, and "Maya Chen"
sits in the register v1 §7 bans. Decided 2026-07-31, still binding.

---

## Automated tests

| File | Asserts |
|---|---|
| `tests/golden/case_architect/` | Schema valid · no fake-round numbers · no banned-register names · internal consistency · vacuity floor |
| `tests/golden/planner/` | Every question answerable from the case world · rubric dimensions covered · vacuity floor |
| `tests/test_case_world.py` | `case_world` written exactly once · **a second write is rejected, proven by attempting one** · the node reads the CONFIRMED level, including a correction |
| `tests/test_plan_interview.py` | `question_plan` reaches state · `case_world` is unchanged across the node · the three-node chain runs end to end from one resume |
| `frontend/src/**/*.test.ts` | Both agents render their four states · Realtime updates arrive · no raw JSON in rendered copy |

---

## Phase gate

Do not start Phase 3 until every box above is ticked and these hold:

1. `make test` passes, with output pasted into `DEV-STATE.md`. **Run it FIRST on a fresh daily
   budget** — it is ~120,000-130,000 tokens on `deep` and cannot share a day.
2. `make golden AGENT=case_architect` and `make golden AGENT=planner` both recorded, with pass
   rates and any flaps stated honestly rather than re-run until green.
3. **The immutability rule is proven by a rejected second write**, not by inspection.
4. **A case world you read and believe.** Generate three at different levels and judge whether a PM
   would accept the company as real. This is the phase's equivalent of Phase 1's "does the level
   look right", and it has no objective answer.
5. The question plan for one of those worlds is one you would actually ask.

---

## Handoff

### Verified by me, with evidence in DEV-STATE
- `make test` and both `make golden` outputs
- The immutability rule, proven by a rejected write
- The confirmed-level path, proven with a correction rather than an acceptance
- Whichever golden cases flap, recorded with counts rather than smoothed over

### Needs your eyes
- **Do the case worlds read as real?** No test can answer this. Fake-round numbers and generic
  names are caught mechanically; a world that is merely *boring* is not.
- **Is the question plan an interview you would sit?** Coverage is assertable, quality is not.
- **The `deep` model question, now with three agents of evidence.** Phase 1 accepted three flaps
  and named this as the tiebreak. Kept informal by decision on 2026-08-02, so there is no
  acceptance box forcing it, but this is the phase where the answer becomes visible.

## Out of scope

No Interviewer, no conduct loop, no scoring, no coach. The right-hand evaluation column stays
empty. No persona header. No OCR. Nothing in the conduct-round subgraph, including
`await_candidate` — Phase 3 owns interrupt #2.
