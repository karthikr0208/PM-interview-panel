# Phase 3.5 — Question quality: curated worlds, a shape bank, one question probed deeply

**Goal:** the candidate is asked **one open-ended product strategy question about a company they
have heard of**, and then probed on it for 45 minutes. No decorative statistics, nothing answerable
by reciting the brief back.

**Why this phase exists.** Phase 3 closed with the flow working and the questions wrong. The three
served on 2026-08-05 are recorded verbatim in DEV-STATE § Decisions; two of three stapled a market
size to the front and one could be answered by summarising the case. Karthik's own examples of the
target shape — *"what is Reddit's biggest threat"*, *"should Samsung enter gaming"*, *"how would you
price YouTube Premium"*, *"how would you 10x Duolingo"* — are shorter, broader, and about companies
the candidate already understands.

**Done when:** a candidate sits an interview against a real company, gets one question in the shape
of the examples above, is probed 6 or more times against their own answers, and the transcript holds
**every candidate turn**, not just the Interviewer's.

---

## 🔴 THREE DECISIONS THIS PHASE REVERSES. Read these before writing code.

All three are Karthik's calls of 2026-08-06, made against evidence, and they are deliberate.

### 1. Case worlds become CURATED and REAL. The Case Architect stops generating.

Eight hand-written fact sheets about real companies replace generation:
**Reddit · Duolingo · YouTube · Airbnb · Figma · Cursor · OpenAI · Anthropic**

**What this costs:** the Case Architect drops from a generative agent to a selector. Its 7 golden
cases and 47 offline assertion tests keep running, now **against hand-written fixtures** — which
AGENT-PLANNER-SPEC.md §5 already identifies as the more valuable direction, because a hand-built
world a human considers good passing the Case Architect's assertions is a **positive control on
those assertions themselves.**

**What it buys:** zero hallucinated facts, zero tokens per interview for world-building, and a
candidate with real intuition about the business. That last one is the actual complaint being fixed.

**🔴 The round-number assertion now runs against reality.** `is_round_dollar_amount` was written to
catch a model reaching for `$150M`. If a **real** public figure happens to be round, the assertion
is wrong and the data is right. Do not distort a real number to satisfy a test written for a
generative failure mode — widen the assertion and record why.

### 2. The Interviewer MAY now invent facts the world does not contain. The refusal branch goes.

Karthik: *"allow the candidate to ask clarifying questions even if they are not available in the
case world. The response need not be accurate or up to date from the model."*

**This deletes the strongest single result in the project.** [interviewer.py:75](../../backend/app/agents/interviewer.py#L75)
forbids invention absolutely, and the 2026-08-05 interview producing a correct refusal is the only
observation of ARCHITECTURE §9's undetectable failure mode not happening. It is being given up on
purpose, because a refusal reads as a broken interviewer to a candidate, and real interviewers say
*"assume DAU is 50 million"* all the time.

**🔴 It is replaced by INVENT-AND-RECORD, not by invent-freely.** The damage in improvisation is not
the invention, it is **self-contradiction**: 50M at minute 8 and 20M at minute 30, which a candidate
will catch and which ends the illusion. So:

| | |
|---|---|
| `case_world` | Unchanged. Still written once, still immutable, still the ground truth |
| `improvised_facts` | **New state field, append-only.** Every fact the Interviewer invents lands here |
| Every later clarification and probe | Receives `case_world` **plus** `improvised_facts` |
| `can_answer` | Stays on the schema. It now means "the world states this", and drives whether the answer is recorded as improvised |

The immutability rule survives intact: nothing writes `case_world`. The new list is a separate,
append-only channel, and it is what makes an invented fact durable rather than momentary.

**The assertion that replaces the refusal assertion:** an improvised fact, once recorded, must be
**repeated consistently** when asked again. That is mechanically checkable and it is the property
that actually matters now. `ungrounded_figures` is not deleted — it is retargeted at
`case_world ∪ improvised_facts`.

### 3. ONE question, probed live. `probe_angles` planned up front are dead.

`_QUESTIONS_THIS_PHASE` goes from 3 to **1**. AGENT-PLANNER-SPEC.md §8's open question — *"should
`probe_angles` be planned at all, or generated live?"* — is answered against the current design:
2-3 pre-written strings cannot fill 45 minutes, and a probe that ignores what the candidate actually
said is not a probe.

**Consequences that are easy to miss:**

- **Rubric coverage moves from questions to probes.** One question cannot be the `primary_dimension`
  of five dimensions. The **probe ladder** covers the rubric now, which rewrites
  AGENT-PLANNER-SPEC.md §3 and is what Phase 4's Evaluator will read.
- **`decide_next` currently asserts `followup_count == 0`** ([build.py:652](../../backend/app/graph/build.py#L652)),
  because PHASE-3-SPEC §2c excluded the probe edge deliberately. That assert comes out and
  `followup_count` becomes the loop's primary driver.
- **Ordering for graceful truncation is moot.** One question cannot be reordered.

---

## 🔴 The budget change, which is the largest in the project so far

Today a whole interview costs roughly **one** `fast` call (the transition is deterministic, the
question is copied byte for byte). After this phase it costs **one call per probe**, 6-10 of them,
each carrying `case_world` plus a transcript that **grows with every turn**.

Two ceilings, both real, and both must be computed **before** the loop is built, not after:

| Ceiling | The question to answer |
|---|---|
| **8,000 TPM** | Does the probe call still fit at **probe 10**, when the transcript is longest? `case_world` is ~1,200 tokens on its own. This is the same computation AGENT-INTERVIEWER-SPEC.md §6 ran, and there it found the naive design did not fit |
| **200,000/day** | At N tokens per interview, how many interviews exist in a day? If a full interview costs 30,000 `fast` tokens, that is **six**, and iterating on this phase competes with sitting it |

**If the full transcript does not fit at probe 10**, the fallback is the main question plus
`case_world` plus `improvised_facts` plus the **last N turns** — decided by measurement, not taste.

---

## 🔴 Traps carried forward. Every one is a recorded failure from this project.

| Trap | Where it bit |
|---|---|
| **Widen the assertion BEFORE changing the prompt** | The order that worked in 3.1 and 2.5. Already prescribed for the Case Architect's round figures and never done. A prompt change ahead of its assertion is unfalsifiable |
| **A prompted ban is not a ban** | The em-dash rule failed twice as prompt text and was only fixed deterministically by `stripDashes`. **The decorative-statistic ban must be structural** — a shape template with no stat slot — not a sentence in a prompt |
| **`await_candidate` contains ONLY `interrupt()` and its return** | The single most important structural constraint in the codebase. The candidate-answer write of story 3.5.1 **must not go in that node** — it re-runs on every resume |
| **Adding a node to `build.py` means re-running EVERY live test that builds a graph** | Story 3.2 broke `test_confirm_level.py` this exact way and shipped it in `08d8dba`, because only the edited file was re-run. The offline suite stayed green at 213 |
| **Deselected is not passed** | Twice on 2026-08-05, `N passed, M deselected` was read as verification when the deselected M were the only tests observing the property |
| **Every denial assertion needs a positive control and a vacuity floor** | Story 1.3a. An empty `grounded_in` satisfied the suite's most important check on all eight cases |
| **Classify every failure before believing it** | Three times a mostly-red run was rate limiting. Grep for `tokens per day` and `tokens per minute` first |
| **A green run is one sample** | `temperature=0` does not make these models deterministic |
| **The node owns side effects, the agent function stays pure** | Held for all four agents. Golden cases run with no database because of it |

---

## Stories

Five. Phase 3's spec warned "three stories, not seven" and it was right; this one is larger because
it reverses three decisions, but the first two stories cost **zero tokens** and should be done on a
dead budget.

### 3.5.1 The transcript holds candidate turns — ✅ DONE 2026-08-06

**Zero LLM cost. Blocking: nothing below is verifiable without it.**

DEV-STATE calls this "a schema-shaped problem, not a prompt one." **That is wrong and the correction
matters:** [0001_initial_schema.sql:46-54](../../backend/migrations/0001_initial_schema.sql#L46-L54)
already declares `role` as `interviewer | candidate | system` and `kind` as
`question | followup | answer | clarify | meta`. **The DDL has always supported this.** It is a
missing write, not a missing column, so it needs **no migration** — which also means no deploy
ordering risk.

Today only the Interviewer's own utterances get a row ([build.py:428](../../backend/app/graph/build.py#L428)),
so a finished interview stores 3 questions, 1 clarification, and **zero answers**.

**Acceptance**
- [x] A candidate answer writes a `transcript_turns` row with `role='candidate'`, `kind='answer'`
- [x] A candidate clarifying question writes one with `role='candidate'`, `kind='clarify'`
- [x] 🔴 **The write happens in the node AFTER the resume, reading `last_input` — never in
      `await_candidate`.** Confirmed: `await_candidate` contains **zero** `rest_insert` calls
- [x] `unique (session_id, idx)` is respected: two inserts at the same `(session_id, idx)` raise
      **409**, observed directly rather than read off the DDL
- [x] A live test reads back a finished interview and asserts the turns **alternate**
      interviewer / candidate, with no gaps in `idx`
- [x] **Falsified:** deleting both writes turns **4 of 6** live tests red, observed, then reverted

**🔴 THIS STORY'S BRIEF WAS WRONG AND THE AGENT CAUGHT IT.** The brief said to put the
candidate-answer write in `ask_question`. `route_input`'s `answer` branch routes to **`decide_next`**,
not `ask_question` ([build.py:792-798](../../backend/app/graph/build.py#L792-L798)), and on the final
question `decide_next` returns `exit` straight to `END` — so `ask_question` never runs again and
**the last answer of every interview would have had no row.** That is precisely the gap this story
exists to close, reintroduced by the fix for it. The write lives in `_decide_next_node` instead,
guarded on `last_input.type == "answer"`, which runs on every answer resume including the final one.

**Observed output**

```
await_candidate rest_insert calls        0        (load-bearing rule intact)
live transcript tests                    6 passed in 40.44s
falsification (both writes deleted)      4 of 6 red
  AssertionError: the final answer never got a row: last row was
  (4, 'interviewer', 'question', ...)  assert 'interviewer' == 'candidate'
replay at the same (session_id, idx)     httpx.HTTPStatusError 409, observed
shared-graph re-run  test_conduct_loop   3 passed, 20 deselected
                     test_confirm_level  9 passed in 430.52s
```

---

### 3.5.2 The eight curated worlds and the shape bank, both checked in — ✅ DONE 2026-08-06

**Zero LLM cost.** This is the story that actually fixes the reported defect.

**The eight worlds** live as checked-in fixtures conforming to the existing `CaseWorld` schema plus
one new field, `as_of: str`.

**Acceptance**
- [x] Eight worlds: **Reddit, Duolingo, YouTube, Airbnb, Figma, Cursor, OpenAI, Anthropic**
- [x] Every one **passes the Case Architect's own universal assertions** in
      `tests/golden/case_architect/assertions.py`. Two widenings, both recorded — see below
- [x] Each carries `as_of` (July to September 2025). 🔴 **Rendering it to the candidate is owed by
      story 3.5.5**; the data exists, the surface does not yet
- [x] Level coverage is data, not branching prose: APM `duolingo, cursor` · PM `reddit, figma` ·
      Senior PM `airbnb, youtube` · GPM `openai, anthropic`
- [x] `select_case_world(level, profile)` is **deterministic Python, no LLM** — a stable SHA-256 of
      the profile, so a retried request never switches the world mid-interview
- [ ] **The shape bank**, twelve shapes across four categories, checked in as data not prose:

| Category | Shape |
|---|---|
| **strategy** | What is `<company>`'s biggest threat over the next three years? |
| | Should `<company>` enter `<adjacent market>`? |
| | `<company>` can make one big bet next year. What should it be? |
| **gtm** | `<company>` just built `<capability>`. How would you take it to market? |
| | How would you launch `<product>` for `<new segment>`? |
| | `<competitor>` shipped `<capability>` first. How does that change `<company>`'s launch? |
| **pricing** | How would you price `<product>`? |
| | Should `<product>` move from `<current model>` to `<alternative model>`? |
| | `<company>` wants to raise prices on `<product>`. How would you do it? |
| **growth** | How would you grow `<metric>` at `<company>` by `<N>`x? |
| | `<metric>` has been flat for `<period>`. How would you diagnose and fix it? |
| | How would you increase `<conversion step>` for `<product>`? |

- [x] 🔴 **No shape has a slot for a market size or a growth rate.** Thirteen shapes, not twelve:
      `How would you {n}x {company}?` was added because it is Karthik's own example phrasing and the
      bank could not say it
- [x] **Assertions widened before any prompt is touched**, per the trap table:
      - [x] **Decorative-statistic check** — implemented as the spec's own deletion test, not a
            pattern catalogue. Fires on currency, percent, comma-grouped integers, and scale words
      - [x] **Shape conformance** — `fullmatch` against every bank template with slots filled
      - [x] **Recitation check** — implemented on the **property**, not the phrasing: an explanatory
            frame, with no second-person reference and no decision verb
      - [x] 2026-08-05's three real questions are the checked-in corpus, with the required table
            pinned: Q1 both fire, Q2 statistic only, Q3 neither
- [x] Suite is **deliberately RED before the Planner changes**, proven by running it
- [x] 🔴 **Every bank shape clears its own gates**, parametrized off `SHAPE_BANK` so a shape added
      later is covered without anyone remembering. **This control found a real defect on its first
      run** — see below

**🔴 TWO ROUNDS OF REWORK, BOTH FROM INDEPENDENT RE-VERIFICATION, NEITHER VISIBLE IN A GREEN SUITE.**

*The assertions did not generalize.* Both shipped green and both were near-useless. Measured against
variants I wrote myself:

```
is_recitation_shaped   1 of 6   fired only on the literal verb "support" next to "given"
decorative_statistic   2 of 6   missed customer counts, comma-grouped integers, bare ARR, churn %
```

Every one of those four misses is a field the curated worlds actually carry, so the check would have
reported green on the same defect wearing a different figure. Rewritten on the property rather than
the phrasing; now 6 of 6 and 6 of 6.

*A bank shape failed the bank's own gate.* Filling all thirteen shapes and running them through all
three checks — an ad-hoc probe that now lives in the suite permanently:

```
FAIL  Babbel shipped AI conversation practice first. How does that change Duolingo's launch?
      -> RECITATION
```

**The rule was right and the shape was wrong.** That phrasing asks what changed, not what the
candidate would do. Fixed to `...How does that change your launch plan for {company}?`, which is
better interview copy independent of the gate. 13 of 13 now clear.

*The round-number allowlist disarmed the generative path.* Three real round figures (`$100M` Cursor,
`$10B` OpenAI, `$3B` Anthropic) were exempted **inside the shared `is_round_dollar_amount`**, so a
**generated** world claiming `$100M` ARR passed the check that exists to catch exactly that. Moved to
a per-field exemption map at the curated-worlds call site, which asserts the violation was actually
raised before waiving it (*"an exemption that matches nothing proves nothing"*) and that the exempted
value still matches the fixture. A standing regression guard now fails if it leaks back.

**Also fixed:** `yoy_growth_pct` of `9900.0` (Cursor) and `200.0` (both AI labs) were fake-round
tells; now `412.6`, `194.1`, `216.3`, each with its waypoints in `supporting_facts`.

**Observed output**

```
offline suite            306 passed, 101 deselected, 0 failed   (baseline was 221/95)
planner golden           88 passed, 5 deselected
curated worlds + CA      91 passed, 7 deselected
bank control falsified   reverting the Babbel shape -> 1 failed, 12 passed
is_round_dollar_amount   $100M/$10B/$3B/$150M/$1M caught · $748M/$36.1B pass
eight worlds             0 em-dashes, 0 placeholders, 0 banned-register names
```

---

### 3.5.3 The Planner picks a shape and fills it — ✅ DONE 2026-08-06

**Acceptance**
- [x] Shape **selection** is deterministic Python from level and category; the LLM only **fills
      slots** from `case_world`. The question string is built by
      `shape.template.format(**slots)` **in Python** — the model never returns it, which is what
      makes a decorative statistic unsayable rather than discouraged
- [x] 🔴 **Re-measured, and the answer changed: the Planner now runs on `fast`.** Golden smoke
      passed with **no retry fired**. It needed `deep` only because `QuestionPlan` was the largest
      generation in the product; slots plus a ladder is a fraction of that
- [x] `question_plan` holds **one** main question plus a **probe ladder** of 5-8 angles, each tagged
      with the `primary_dimension` it surfaces
- [x] **All five rubric dimensions appear across the probe ladder** — observed, 6 entries covering
      all five on the smoke
- [x] `grounded_in` survives unchanged and still set-membership checks against `case_world`
- [x] Each of the eight worlds declares `suits_categories`, so category choice is **data, not an LLM
      guess** — nothing can ask a pricing question about Reddit's AI-licensing tension
- [x] `AGENT-PLANNER-SPEC.md` updated: §3 coverage, §5 assertions, §6 model, §8 probe question closed
- [x] **One golden case run as a smoke.** Not the full set, not an A/B

**Observed output**

```
offline            326 passed, 101 deselected, 0 failed   (baseline 306/101)
golden smoke       apm_consumer_world, role=fast, PASS, retry_fired=False
three gates        asserted in test_golden.py:142-151, not merely sampled

QUESTION  What is Ferngrove Media's biggest threat over the next three years?
LADDER    6 entries, all five rubric dimensions covered
```

That question is the target register, and it came out of the machine rather than out of a prompt
asking nicely for it.

**🔴 A collision in this story's own brief, resolved rather than papered over.** The brief said both
"keep `question_plan` a list of dicts, do not break the working graph" and "do not touch
`build.py`". Those conflict: `ask_question` reads `planned["primary_dimension"]`, and a one-question
plan has no single such value now that coverage lives on the ladder. Resolved by setting it
programmatically from `probe_ladder[0]`, documented at `_first_dimension`. **`build.py` untouched.**

---

### 3.5.4 Live probes, invent-and-record, and the probe edge — ⬜

**The largest story, and the one that reopens the graph.**

**🔴 TWO GAPS 3.5.3 SURFACED THAT NO STORY OWNED. THEY ARE THIS STORY'S NOW, AND THE FIRST ONE IS
THE WHOLE POINT OF THE PHASE.**

- [x] 🔴 **Wire the curated worlds into the graph — ✅ DONE 2026-08-06.** `generate_case_world` now
      calls `select_case_world`; the generative Case Architect is out of the runtime path entirely,
      so an interview costs **one fewer LLM call** than it did this morning. Three side effects
      unchanged, error path unchanged, `role` accepted and ignored. Observed output below
- [ ] 🔴 **`_QUESTIONS_THIS_PHASE = 3` against a one-question plan is an `IndexError` waiting to
      fire.** Nothing catches it today because every graph-level test injects a static
      `question_plan` fixture rather than running the real Planner through the compiled graph.
      **That gap in the tests is itself worth closing** — a live test that drives the real Planner
      through the graph would have caught this

**Observed output — the wiring box only**

```
offline        329 passed, 101 deselected, 0 failed   (baseline 326/101, +3 node tests)
falsified      the same 3 tests go RED against a generative-shaped world
               ('Bright Basket', suits_categories []) — on their own assertions,
               not on a ValidationError

Planner on `fast` against two REAL curated worlds, which had never happened
(3.5.3's smoke used the FIXTURE world "Ferngrove Media", not one of the eight):

  PM   world Figma      suits ['strategy','pricing','gtm']  shape gtm
       "How would you launch Figma Make for marketing teams?"       6 ladder entries
  GPM  world Anthropic  suits ['strategy','growth','gtm']   shape strategy
       "What is Anthropic's biggest threat over the next three years?"  5 ladder entries

no retry fired on either call · no decorative statistic · all five rubric
dimensions across each ladder · `grounded_in` cites real facts from the sheet
```

**🔴 Owed, not done: the live graph re-run.** `build.py` changed, and the named trap says re-run
every live test file that builds a graph — `test_confirm_level.py`, `test_conduct_loop.py`,
`test_transcript.py`, 18 live tests. **Deliberately deferred to the end of 3.5.4**, because the
probe edge reopens the same file within the same story and running ~40 `fast` calls twice would cost
a large fraction of a day's budget for one intermediate state. It is owed before the phase gate.

**Acceptance**
- [ ] `generate_probe(case_world, improvised_facts, main_question, transcript, ladder)` is a **pure**
      function, no session and no database, matching all four existing agents
- [ ] A probe **responds to what the candidate actually said**. A probe that reads identically
      against two materially different answers is the `write_bridge` failure again — that function
      was deleted on 2026-08-05 for being a constant function wearing an LLM call. **Check for it
      the same way: several different answers, compare the probes**
- [ ] `improvised_facts` added to `InterviewState` as an **append-only** list with a reducer, the
      same shape as `answer_evaluations`' `operator.add` — see ARCHITECTURE §4 "The trap"
- [ ] An answer with `can_answer=False` **invents a plausible fact, records it, and states it as
      given.** The refusal language in the clarification prompt comes out
- [ ] 🔴 **Consistency assertion:** ask for the same invented fact twice, get the same value.
      This replaces the refusal assertion as the suite's assertion with teeth
- [ ] `ungrounded_figures` retargeted at `case_world ∪ improvised_facts` rather than deleted
- [ ] `decide_next`: the `followup_count == 0` assert removed, `_QUESTIONS_THIS_PHASE = 1`, exit on
      probe count or `_TIME_BUDGET_MINUTES`. **Exit condition stays in exactly one place**
- [ ] The probe edge is a real edge in `build.py`, and `await_candidate` **still contains only
      `interrupt()` and its return** — assert the single-call guarantee across a probe loop, not just
      a question loop. `falsify_looping_interrupt.py` covers questions and **does not cover probes**
- [ ] 🔴 **Re-run EVERY live test file that builds a graph**, not just the edited one. Named trap
- [ ] The TPM computation of the budget section, **done and recorded, at probe 10**

---

### 3.5.5 The frontend: the brief, and a probe that reads as a probe — ⬜

**Zero LLM cost.**

**Acceptance**
- [ ] The **brief is shown**: company, what it sells, the `as_of` line. The candidate can re-read it
      without losing their place, the same failure `useInterview` already guards on clarifications
- [ ] A **probe is visually distinct from the main question** — the main question stays on screen
      for all 45 minutes; a probe is a follow-up beneath it, not a replacement. Losing the main
      question is the clarification bug in a new costume
- [ ] `stripDashes` applied to probe text, which is a **new model-output surface** and inherits
      nothing
- [ ] Full loading / empty / error cycle on the probe surface, matching 1.5's foundation
- [ ] **Falsified by mutation:** make the probe replace the main question, watch a test go red

---

## Automated tests

| File | Asserts |
|---|---|
| `tests/test_transcript.py` | Candidate answers and clarifications get rows · turns alternate · a replayed resume conflicts rather than duplicating |
| `tests/golden/case_architect/` | The eight curated worlds pass the universal assertions — a **positive control on those assertions** |
| `tests/golden/planner/` | Shape conformance · **no decorative statistic** · not recitation-shaped · rubric covered across the probe ladder · 2026-08-05's Q1/Q2 fail and Q3 passes |
| `tests/golden/interviewer/` | A probe responds to the answer given · an improvised fact **repeats consistently** · `ungrounded_figures` against `case_world ∪ improvised_facts` |
| `tests/test_conduct_loop.py` | The probe edge loops · `await_candidate` still single-call **across probes** · `decide_next` exits on probe count and on time |
| `frontend/src/**/*.test.ts` | The main question survives a probe · the brief renders with `as_of` · probe text is dash-stripped |

---

## Phase gate

1. **`pytest tests -m "not live"` green** — free, seconds. **Run it FIRST.**
2. **One Planner and one Interviewer golden case as a smoke.** Not the full set.
3. **The probe loop runs across real HTTP request boundaries**, and the single-call guarantee is
   **falsified across a probe**, not inherited from the question loop's falsification.
4. **An interview Karthik sits and believes — and this time the gate is the QUESTION, not the
   flow.** The flow already passed on 2026-08-05. What is being judged here is whether the question
   reads like his own examples and whether 45 minutes of probing holds up.

---

## Handoff

*To be filled with observed output. Nothing goes here that was not run.*

**Needs Karthik's eyes**
- The eight fact sheets. These are hand-written and he knows these companies; a wrong fact about
  Reddit or Cursor is one he will spot and I will not.
- Whether one question probed for 45 minutes actually sustains, or whether it runs dry at probe 5
  and needs a second question after all.
