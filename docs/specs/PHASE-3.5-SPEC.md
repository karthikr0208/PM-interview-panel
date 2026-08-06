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

### 3.5.1 The transcript holds candidate turns — ⬜

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
- [ ] A candidate answer writes a `transcript_turns` row with `role='candidate'`, `kind='answer'`
- [ ] A candidate clarifying question writes one with `role='candidate'`, `kind='clarify'`
- [ ] 🔴 **The write happens in the node AFTER the resume, reading `last_input` — never in
      `await_candidate`.** That node re-runs from the top on every resume and would double every row
- [ ] `unique (session_id, idx)` is respected: a replayed resume conflicts rather than duplicating.
      **Assert this by replaying**, not by reading the DDL
- [ ] A live test reads back a finished interview and asserts the turns **alternate**
      interviewer / candidate, with no gaps in `idx`
- [ ] **Falsified:** removing the candidate write turns that test red. Observed, then reverted

---

### 3.5.2 The eight curated worlds and the shape bank, both checked in — ⬜

**Zero LLM cost.** This is the story that actually fixes the reported defect.

**The eight worlds** live as checked-in fixtures conforming to the existing `CaseWorld` schema plus
one new field, `as_of: str`.

**Acceptance**
- [ ] Eight worlds: **Reddit, Duolingo, YouTube, Airbnb, Figma, Cursor, OpenAI, Anthropic**
- [ ] Every one **passes the Case Architect's own universal assertions** in
      `tests/golden/case_architect/assertions.py`, unmodified where possible. Where an assertion
      fires on a **real** figure, widen the assertion and record why — see the round-number note above
- [ ] Each carries `as_of` and it is **shown to the candidate**: *"This brief reflects public
      information as of `<date>`. Treat it as ground truth for this interview."* No em-dash
- [ ] Level coverage is deliberate and stated: which worlds suit APM, which suit GPM
- [ ] `select_case_world(level, profile)` is **deterministic Python, no LLM** — CLAUDE.md § Style
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

- [ ] 🔴 **No shape has a slot for a market size or a growth rate.** That is the structural fix for
      the decorative-statistic defect, and it is why this is a bank rather than a prompt instruction
- [ ] **Assertions widened before any prompt is touched**, per the trap table:
      - [ ] **Decorative-statistic check:** a question that still parses the same with its leading
            statistic clause deleted is a question whose statistic did no work. Mechanical and cheap
      - [ ] **Shape conformance:** the emitted question matches a bank shape with its slots filled
      - [ ] **Recitation check:** reject the `how does X support Y given Z` frame that produced Q1
      - [ ] Each has a **positive control that must go RED** — 2026-08-05's three real questions are
            the honest corpus: Q1 and Q2 must **fail** the new checks, Q3 must **pass**
- [ ] Suite is **deliberately RED before the Planner changes**, proven by running it

---

### 3.5.3 The Planner picks a shape and fills it — ⬜

**Acceptance**
- [ ] Shape **selection** is deterministic Python from level and category; the LLM only **fills
      slots** from `case_world`. Much smaller generation than `QuestionPlan`
- [ ] 🔴 **Re-measure the model.** The Planner needs `deep` today because `QuestionPlan` was the
      largest generation in the product (DEV-STATE § Decisions 2026-08-04). One question with filled
      slots is a fraction of that, so **`fast` is plausible now and must be tested, not assumed**
- [ ] `question_plan` holds **one** main question plus a **probe ladder**: an ordered list of
      angles, each tagged with the `primary_dimension` it is there to surface
- [ ] **All five rubric dimensions appear across the probe ladder** — coverage moved off the
      question, which rewrites AGENT-PLANNER-SPEC.md §3
- [ ] `grounded_in` survives unchanged and still set-membership checks against `case_world`
- [ ] `AGENT-PLANNER-SPEC.md` updated: §3 coverage, §5 the new assertions, §8's probe question closed
- [ ] **One golden case run as a smoke.** Not the full set, not an A/B — portfolio calibration

---

### 3.5.4 Live probes, invent-and-record, and the probe edge — ⬜

**The largest story, and the one that reopens the graph.**

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
