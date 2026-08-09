# Development State

**Last updated:** 2026-08-08 · Session 15

---

## Now

**🟢 SESSION 15, 2026-08-08: EVERY OPEN ⬜ FROM SESSION 14 IS RESOLVED, AND THE PROBE-7 FAULT WAS
NEVER A DEFECT.** The paced live conduct loop went **4 passed, 346s — its first fully green run
ever**, with no `llm_schema_failure` logged. That closes the batching hypothesis: neither of
2026-08-07's live failures was a product defect, and `_append_retry_instruction` is off the list.

**🔴 But `gpm_portfolio_world` had never been executed, and the 2026-08-07 false-premise fix only
half worked.** Run live it failed **3/3 byte-identically** — `fast` is deterministic, unlike
`deep`. Step 1's first-sentence rule fired correctly; then the answer **handed over the answer to
the interview question**, a full 15/20/5 allocation, in the first person. Nothing in the prompt
forbade solving the case. Fixed **0/3 → 3/5 → 4/4**, the second edit needed only because the first
was routed around by reframing the allocation as a fact about the company.

**🔴 A second live interview (GPM, OpenAI world) found two more.** Probes 6-8 **recycled probes
1-3** — `generate_probe`'s 4-turn window cannot see the probe it is repeating. **Probes cut 8 → 4
on Karthik's call**, which removes the repetition structurally. And probe 8 quoted a **clarifying
question back as the candidate's position** — `route_input` knew the difference, `messages` threw
it away. `kind` now travels the whole path.

**🟢 Invent-and-record replicated:** `100×` invented (it is nowhere in `openai.json`) and
reproduced verbatim several probes later. **But it is the TRUE public figure** — with real
company worlds a leaked fact reads as correctly grounded and nothing can detect it. See § Decisions
2026-08-08 #4.

**🔴 One thing is NOT live-validated: the `kind` change**, which touches `await_candidate`. The
re-run died on the daily cap at **197,615/200,000**, classified as quota. Offline green at 394,
mutation-tested. **It is owed a live run on fresh budget.**

**🟢 Delegation is now a session-start decision** — CLAUDE.md step 6 plus a triage table (`01e44da`).

**Phase 0 — Walking skeleton. ✅ COMPLETE 2026-07-30. All eight stories, all six phase-gate
conditions, deployed and proven end to end.**

```
frontend  https://pmaiinterviewpanel.netlify.app
backend   https://pm-interview-panel.onrender.com     (Render, Singapore, free)
database  tnqfqsocoqythakwybsw                        (Supabase, Singapore, free)
```

**All four risks this phase existed to retire are retired**, each with a measured number rather
than an assumption:

| Risk | Answer |
|---|---|
| Is structured output reliable on the free endpoint? | No, not fully. `deep` 7-9/10 → validate-retry is mandatory, enforced in the wrapper |
| Does Supabase work from Render at all? | Yes. Session pooler, and a checkpoint step costs **~27ms** in production |
| Does `interrupt()` really resume across separate HTTP requests? | Yes. Proven across two separate OS processes, and against the deployed URL |
| What is the account's rate model? | 40 RPM, no credits, nothing exhaustible |

**🟢🔴 SESSION 14, 2026-08-07: KARTHIK SAT A FULL INTERVIEW ON THE DEPLOYED STACK.** One question,
four clarifications, **eight probes, clean exit at the boundary.** **Invent-and-record works end to
end** — it invented `3.2%`, recorded it, reproduced it exactly two probes later when asked cold, and
did **not** duplicate the entry. **The probe responded to the candidate's own claim 8 times out of
8.** The ladder engages. Probe 7 did not crash under human pacing.

**🔴 But the QUESTION was wrong, and the cause is one function.** A Senior PM was asked *"How would
you increase booking conversion for Airbnb Services and Experiences?"* in a **Product Strategy**
interview, while the same case world carried Local Law 18, Chesky's platform bet, and Services unit
economics in its ladder. `select_category` takes `_LEVEL_INDEX` modulo the length of a world's
category array, so **an APM gets the strategy question and a Senior PM gets funnel optimisation.**

**🔴 And a REGRESSION: the Interviewer accepted a false premise** — it agreed the short-term rental
market was "shrinking" against a world stating 8.6% growth. **This passed on 2026-08-05; story
3.5.4 deleted the refusal branch that made it pass.** Blast radius measured and limited: one turn,
never entered `improvised_facts`, never resurfaced. See § Decisions 2026-08-07 for all eleven
findings.

**🟢 SESSION 14, 2026-08-07: THE PROBE LOOP COMPLETED A LIVE RUN FOR THE FIRST TIME, AND EVERYTHING
IS DEPLOYED.** All eight probes plus the boundary exit passed in run 1 of `test_conduct_loop.py`,
which is phase-gate condition #3's central assertion and had never been observed. Twelve commits
pushed (`e2a2d7f..cbd5ce2`); Netlify proven current by bundle grep.

**🔴 One defect is open and it is NOT what it looks like: `generate_probe` fails intermittently at
probe 7, with a SHAPE fault, not a size one.** Session 13's `max_tokens` 1024 -> 2048 is now
verified as real (probes 1-6 are solid where probe 3 used to fail) but it moved the boundary rather
than closing it. **The next `max_tokens` bump would change nothing** — the body carries the generic
`"Failed to validate JSON"`, not the truncation message. `cbd5ce2` makes the next failure
self-diagnosing via a new `llm_schema_failure` log record. **The other run-2 failure was the 8,000
TPM per-minute ceiling, a test-harness artifact, not a defect.** See § Decisions 2026-08-07.

**🟢 SESSION 13, 2026-08-06: THE EIGHT REAL COMPANIES ARE LIVE IN THE GRAPH.** `generate_case_world`
calls `select_case_world`; the generative Case Architect is out of the runtime path, so an interview
costs **one fewer LLM call** and `suits_categories` is non-empty at runtime for the first time.
Smoked on `fast` against two real sheets — *"What is Anthropic's biggest threat over the next three
years?"* **329 offline passed. The live graph re-run is OWED**, deferred to the end of 3.5.4. See
§ Decisions 2026-08-06 (session 13).

**🟢 PHASE 3'S THREE STORIES ARE ALL DONE as of 2026-08-05. The candidate can now sit the whole
interview in a browser.** 3.1 (spec + blind fixtures, zero tokens), 3.2 (the agent and the looping
interrupt, falsified on both sides), 3.3 (the interview UI, zero tokens). **3 of 4 gate conditions
are met; the open one is #4, an interview Karthik sits and believes — his to judge.**

**Story 3.3 spent NO model budget at all**, which was the point of picking it: `fast` was measured
at 197,178/200,000 at session 10's close. It also closed the em-dash-on-model-output rule
**deterministically** after prompting had failed at it twice. See § Decisions 2026-08-05.

**🟢 AND IT IS ALL DEPLOYED.** Six commits pushed 2026-08-05 (`bc44041..db4eaf7`); Render and
Netlify both serve current `main`, verified by route list and by grepping the served bundle rather
than by trusting a dashboard.

**🟢🟢 PHASE 3 IS COMPLETE. GATE #4 IS CLOSED.** Karthik sat a real interview on the deployed stack
on 2026-08-05: the whole flow ran with **no bugs**, on **both the answer and the clarify path**, and
an adversarial clarifying question got a **correct refusal instead of an invented fact** — the one
failure mode ARCHITECTURE §9 says nothing can detect at runtime.

**🔴 The open work is question QUALITY, and it belongs to the PLANNER, not the Interviewer.** Two
defects across three served questions: a decorative statistic stapled to the front (2 of 3), and one
question answerable by reciting the case back. **Karthik is bringing his own examples before the
prompt is touched.** See § Decisions and § Next session.

**🟢 PHASE 2 IS COMPLETE AND THE DEPLOYED PRODUCT WORKS END TO END. Confirmed by Karthik in a
browser on 2026-08-04**, after four days of production being silently broken. `git status` is clean,
everything is pushed, and both Render and Netlify serve current `main`.

**Session 9 was mostly a bug-finding session, and none of the bugs were findable by the test
suites.** Session 8's two uncommitted agent files were sound, but neither passed its golden case;
the smokes found four defects. Then a real CV found three more, in places nine sessions of green
suites could not see:

| Defect | Where it hid |
|---|---|
| `app/llm.py` never retried Groq's schema rejections | A schema failure arriving as a transport exception |
| Deployed backend four days stale, serving Phase 0 | Between the repo and production |
| A real resume does not fit the 8,000 TPM ceiling | An input no golden fixture resembles |
| The upload never started the Resume Analyst | The **seam** between three individually-tested components |

**The last one is the most instructive: an existing test was CERTIFYING the bug**, asserting that a
missing session should silently do nothing. See § Decisions 2026-08-04.

**🔴 CALIBRATION CHANGED 2026-08-02: this is a PORTFOLIO artifact, not a production system.**
Sanity-level verification (~15k a phase, not ~150k), agents default to `fast`, build targets a thin
end-to-end slice. **This supersedes every phase gate and ARCHITECTURE §4.** See Decisions.

**🟡 PHASE 1: ALL SEVEN STORIES ARE DONE as of 2026-08-02 — 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7.
The PHASE GATE is what remains, and 4 of its 5 conditions are met. The open one is #4: a real
resume uploaded through the deployed Netlify URL producing a level Karthik agrees with. That is
his to judge and cannot be delegated. See § Next session.**

**Story 1.3 is ticked on a CONSCIOUS ACCEPTANCE of three flapping golden cases, not on a clean
run.** That is Karthik's decision of 2026-08-02, with the cost and the reopening conditions written
into Decisions below and PHASE-1-SPEC § 1.3. **Do not read a ticked 1.3 as a trustworthy golden
gate** — prompt changes to this agent need the 6-8 pair A/B, not a suite run.

**Session 8 update (2026-08-02). Two stories closed, and the golden suite finally measured.**

**Story 1.4 is CLOSED.** Both missing measurements are taken. **The single-call assertion — the
phase's most important — has been observed FAILING against a deliberately wrong graph**, so it is
no longer correct-by-inspection, and the 8 live tests were re-run rather than inherited. 1.6b's two
unmounted boxes are reachable as a result.

**Story 1.7 is CLOSED with its scope REDUCED, and the reduction is the interesting part.** The
spec's delete list was wrong: 1.4's tests do **not** replace story 0.7's two-OS-process proof, so
`skeleton.py` and both `/skeleton/*` routes are kept permanently as a test harness. Deleting to the
list would have destroyed the evidence retiring this architecture's central stateless-HTTP risk and
left a green suite behind.

**🔴 The golden suite ran all eight cases on `deep` with ZERO 429s for the first time — 37 passed,
1 failed.** Every prior full run lost most cases to quota, so this is the first genuine measurement
of the suite. **The feared regression from the case-01 fix did NOT happen** (`assessed_level` fires
on case 05 in 9 of 9 observations, and case 06 passed). But case 05 has a *third* distinct flap:
its level lands on `APM` sometimes. **Three of eight cases now flap, not two.**

**Session 7 update (2026-08-01, later the same day): the case-01 prompt fix is VALIDATED and
COMMITTED (`27bb749`), and the suite is measurably less trustworthy than session 6 thought.** The
fix went 6/6 on `deep` against a control that failed 2/4 under identical interleaved conditions.
But **the flap is not one bug in one case**: case 01 also over-flags `years_pm_experience` (a mode
the fix does not touch), and **case 02 now flaps too** — it failed on `deep` and went 3/3 clean on
`fast` the same hour. **Two of eight cases are known-unreliable, so 1.3 stays open.**

**Realtime under RLS is PROVEN as of 2026-08-01** — the risk carried since Phase 0 that browsers
could not read their own data is fully retired, with a positive control and a service-role control.

**🔴 The headline finding of 2026-08-01: `temperature=0` does NOT make Groq's gpt-oss models
deterministic, and this file previously recorded that it did.** Golden case 01 flaps roughly 50/50
on `deep` against identical input. A flapping case makes every future prompt change unfalsifiable,
which is the exact property the golden suite exists to provide. Details under Decisions.

The database is no longer wide open: cross-session denial is proven on all six tables with real
JWTs. Resumes upload, extract, and reject a scanned PDF loudly. The design foundation governs every
later phase, and `make test-web` runs for the first time in the project.

**Carried into Phase 1, do not lose:** Supabase **anonymous sign-in must be wired before the
frontend reads any data.** Phase 0 ships RLS with zero policies, so browsers currently get
nothing — correct now, but it means the three-column UI will show an empty middle column until
sign-in plus scoped policies exist. See Decisions 2026-07-30.

**Anonymous sign-in is DISABLED on the project as of 2026-07-31, measured, and it is a dashboard
toggle no script can flip.** See Blockers.

---

## Phase status

| Phase | Status | Spec | Verified |
|---|---|---|---|
| Planning docs | ✅ complete | — | 2026-07-29 — PRD, ARCHITECTURE, CLAUDE.md, research all written |
| 0 Walking skeleton | ✅ complete | PHASE-0-SPEC.md | 2026-07-30 — 52 tests live, deployed, phase gate 6/6 |
| 1 Resume Analyst + design foundation | 🟢 **COMPLETE 2026-08-05. All seven stories, all five gate conditions.** Gate #4 closed by rejecting its premise: seniority is company-relative, so the candidate picks the level and the agent's guess is a default. The selector existed since 1.6b; the missing piece was proving a **correction reaches the Case Architect and Planner**, now asserted and falsified. 1.3 ticked with three golden flaps consciously accepted | PHASE-1-SPEC.md | 2026-08-05 — see § Decisions |
| 2 Case Architect + Planner | 🟢 **ALL SEVEN STORIES DONE 2026-08-04, every box ticked. 3 of 4 gate conditions met.** Both agents smoked, **the full chain runs end to end live**, both agents in the orchestration column, **`case_world` write-once now enforced AND falsified**. Planner needs `deep` (measured) and flaps on genericness, accepted. Gate #4 (a case world Karthik reads and believes) is HIS and still open | [PHASE-2-SPEC.md](specs/PHASE-2-SPEC.md) | 2026-08-04 — **162 offline (+3 live), 84 vitest**, chain proven live |
| 3 Interviewer + conduct loop | 🟢 **COMPLETE 2026-08-05. All three stories, all four gate conditions.** Loop built, **the looping interrupt falsified on BOTH sides**, chain runs end to end over real HTTP, interview UI built with **TRAP 2 and the dash guard falsified by deliberate mutation**, and **deployed**. **Gate #4 CLOSED: Karthik sat a real interview in the browser and reported the whole flow working with no bugs.** **BOTH paths exercised** — and an adversarial clarifying question got a **correct refusal, not an invented fact**, which is ARCHITECTURE §9's undetectable failure mode observed *not* happening. The open work is **question QUALITY, not correctness** — see § Decisions 2026-08-05 | [PHASE-3-SPEC.md](specs/PHASE-3-SPEC.md) | 2026-08-05 — **221 offline (+3 live), 113 vitest**, deployed, interview sat, refusal branch confirmed live |
| 3.5 Question quality | 🟢 **ALL FIVE STORIES DONE AND VALIDATED LIVE 2026-08-08**, except one node change owed a re-run. Session 15: the paced conduct loop went **4 passed / 346s, its first fully green live run**, and **no `llm_schema_failure`** — so the probe-7 shape fault was **never a product defect** and `_append_retry_instruction` is CLOSED. `gpm_portfolio_world` ran for the first time, failed **3/3 byte-identically** (`fast` is deterministic; the flapping finding was `deep`), and is **4/4** after a scope rule stopping the interviewer answering its own case question. Interviewer golden suite **5 passed / 2 failed, both reds PRE-EXISTING and attributed by `git stash`**. A second live interview cut **probes 8 → 4** (probes 6-8 recycled 1-3 through `generate_probe`'s 4-turn window) and found a **clarifying question stored as a candidate position**, now fixed by carrying `kind` end to end. **🔴 The `kind` change is the one thing NOT live-validated** — the re-run hit the daily cap at 197,615/200,000, classified quota. See § Decisions 2026-08-08. Prior notes follow: **ALL FIVE STORIES CODE-COMPLETE 2026-08-06; VERIFIED IN PART AND DEPLOYED 2026-08-07.** The probe loop **completed a live run for the first time** (all 8 probes + boundary exit, gate condition #3's central assertion). Session 13's `generate_probe` `max_tokens` fix is **verified real but incomplete** — it moved the failure from probe 3 to probe 7. **The probe-7 fault is a SHAPE fault, not truncation; another `max_tokens` bump does nothing.** The other live failure was the 8,000 TPM per-minute ceiling, a test-harness artifact. Neither of two full live runs was green, but **every test passed in at least one**. Twelve commits deployed. See § Decisions 2026-08-07. Prior session-13 notes follow: **the `fast` daily budget ran out mid-live-run at 198,580/200,000.** 3.5.4's probe loop and 3.5.5's UI are built, offline-green and falsified by mutation, but **the probe loop has never completed a live run** and `generate_probe`'s `max_tokens` fix is applied and unverified. **THE EIGHT REAL COMPANIES ARE LIVE IN THE GRAPH.** `generate_case_world` calls `select_case_world`, the generative Case Architect is out of the runtime path, and an interview costs **one fewer LLM call**. Smoked: the Planner asks *"What is Anthropic's biggest threat over the next three years?"* against the real Anthropic sheet. **The live graph re-run is OWED** — deferred to the end of 3.5.4 because the probe edge reopens `build.py` in the same story. 3.5.1 transcript holds candidate turns · 3.5.2 eight curated real-company worlds, a 13-shape bank, three new assertions · 3.5.3 **the Planner stops writing questions** (Python formats a bank template) **and drops from `deep` to `fast`, measured.** Target register reached: *"What is Ferngrove Media's biggest threat over the next three years?"* **Four defects caught by independent re-verification, none visible in a green suite.** The rest of 3.5.4 (probe loop, `improvised_facts`, `_QUESTIONS_THIS_PHASE` 3 → 1) and 3.5.5 remain | [PHASE-3.5-SPEC.md](specs/PHASE-3.5-SPEC.md) | 2026-08-06 — **329 offline (was 326), 6 live transcript, 113 vitest**, Planner smoked on `fast` against real Figma and Anthropic worlds |
| 4 Evaluator + scorecard | 🟡 **4.1 AND 4.2 DONE. 4.2 closed 2026-08-09: the Evaluator scores live.** `439 offline passed, 111 deselected` (was 429/111, deselected unchanged). Smoke green on `fast` for `apm_consumer_world_full_coverage`; **role measured at `deep` 2/2 vs `fast` 1/2 and we stayed on `fast` deliberately** (one `deep` sample is not a measurement, and the single disagreement is a rubric definition question). **Token fit computed at the LAST answer BEFORE the loop was built**, per the spec's own instruction: stress case 5,398 against the 8,000 ceiling, asserted offline by `tests/test_evaluator_budget.py` at zero tokens. **One open rubric question surfaced and deliberately not decided** — whether demonstrating a LOW anchor counts as evidence, or whether `not_assessed` means "did not engage at all"; it is Karthik's, and the spec already named it his. **Both of 4.1's open questions are answered**: the "duplicate" clarify turn is not a replay (two different questions 332s apart, idx contiguous 0..27), and fixture 1's inherited ground truth is wrong on the transcript's own text — `dimension_coverage` counts what the Interviewer PROBED, not what the candidate EVIDENCED. Next is 4.3. Prior note: **STARTED 2026-08-08. Story 4.1 DONE (`2231a96`), delegated to a Sonnet subagent and independently re-verified — the first story built under CLAUDE.md's new delegation policy.** Schema, 7 golden fixtures, assertion harness. **429 offline passed (was 394), evaluator suite 35 passed / 8 errors — and the RED is the acceptance**, every error an `ImportError` for the not-yet-existing `evaluate_answer`, with no stub written to fake it. The verbatim-quote assertion was **falsified against a one-word paraphrase** ("runs" → "operates") and observed rejecting it. Fixture 1 is Karthik's **real** 2026-08-07 transcript read from Postgres, spot-checked as genuine. **Two open questions the subagent surfaced: the real transcript has FIVE clarify turns not four (turns 9 and 11 duplicate, possibly a resume replay), and fixture 1's `not_assessed` ground truth is inherited from the spec rather than measured.** Next is 4.2. Prior note: **SPECCED 2026-08-07**, from the live interview of the same day rather than from the plan. Three findings shape it: **2 of 5 rubric dimensions got ZERO evidence** in a real interview, so the Evaluator will be asked to score things nothing was said about; **a single end-of-interview call does not fit the 8,000 TPM ceiling** (the full transcript measured 10,274 tokens on 2026-08-06), so per-answer scoring is forced rather than chosen; and the Interviewer's 4-turn window **must not be reused**, because "sharpens a thesis under pushback" is a property of an arc a keyhole cannot see. The DDL also settles more than expected — `evidence_quote` is `not null` with a length check, so PRD §8's schema-level enforcement is **in Postgres**, and `score` being `not null` means an unassessed dimension is represented by the ABSENCE of a row | [PHASE-4-SPEC.md](specs/PHASE-4-SPEC.md) | — |
| 5 Coach | ⬜ not started | — | — |
| 6 Orchestration depth | ⬜ not started | — | — |
| 7 Polish & hardening | ⬜ not started | — | — |

## Agent specs & golden cases

Specs are written at the top of the phase that builds each agent, not up front.

| Agent | Spec | Golden cases | Last prompt change |
|---|---|---|---|
| Resume Analyst | ✅ [AGENT-RESUME-ANALYST-SPEC.md](specs/agents/AGENT-RESUME-ANALYST-SPEC.md) — written 2026-07-31, before the prompt | 8 written (1.3a). Best run **37 passed / 1 failed, zero 429s** (2026-08-02). **Not yet a reliable gate — 3 of 8 flap on `deep`: 01 `years_pm_experience`, 02 re-capitalization, 05 level → APM** | 2026-08-01 `27bb749`, validated against a control |
| Case Architect | ✅ [AGENT-CASE-ARCHITECT-SPEC.md](specs/agents/AGENT-CASE-ARCHITECT-SPEC.md) — **superseded at the top 2026-08-06: this agent no longer runs in production** | 7 written blind 2026-08-02, still running. **The 8 curated worlds now pass them too, which makes them a positive control on the assertions themselves.** 47 offline assertion tests | **N/A — the prompt is not used in an interview.** `select_case_world` is deterministic Python, zero tokens |
| Planner | ✅ [AGENT-PLANNER-SPEC.md](specs/agents/AGENT-PLANNER-SPEC.md) — **§2, §3, §6 superseded 2026-08-06 by story 3.5.3**; see the box at the top of that file | Rewritten for the one-question-plus-ladder contract. **Smoked live on `fast` 2026-08-06, PASS, no retry.** Three new gates asserted on the generated question: `decorative_statistic`, `is_recitation_shaped`, `matches_no_shape` | 2026-08-06 — **the prompt no longer writes the question.** Slots + ladder only; Python formats the bank template. **Runs on `fast` (measured) — the `deep` requirement was about `QuestionPlan`'s size, not this agent** |
| Interviewer | ✅ [AGENT-INTERVIEWER-SPEC.md](specs/agents/AGENT-INTERVIEWER-SPEC.md) — **a SECOND superseding box added at the top 2026-08-07**, above 3.5.4's. Clarification prompt restructured, `required_angle` added, `select_probe_angle` and `angles_match` new | 5 written blind 2026-08-05, **reusing the Planner's case worlds by pointer, never copied**. 40 offline assertion tests, **+4 for `echoes_false_premise` 2026-08-07**. **2 of 5 ever smoked live** (2026-08-05). 🔴 **`gpm_portfolio_world` — the adversarial leading-question case — is one of the 3 NEVER RUN, and it is the test for the regression found live on 2026-08-07. Run the unrun three before writing new ones** | **2026-08-07 — `_CLARIFICATION_SYSTEM_PROMPT` restructured into THREE ORDERED STEPS, contradiction FIRST**, after it accepted a false premise live. `_PROBE_SYSTEM_PROMPT`'s ANGLE_USED section now honours a `required_angle`. **NEITHER VALIDATED LIVE.** Prior: 2026-08-06 invent-and-record, and `max_tokens` 1024 -> 2048 which is now **verified real but incomplete** (probes 1-6 solid, probe 7 still fails intermittently on a SHAPE fault). Runs on `fast` |
| Evaluator | 🟡 spec is PHASE-4-SPEC.md §4.1-4.4; no separate agent spec yet (owed if 4.3 changes the contract) | 7 written blind 2026-08-08, **reusing the planner's case worlds by pointer** except the one documented exception (Karthik's real 2026-08-07 interview, which has nothing to point at). **2 of 7 smoked live 2026-08-09.** `apm_consumer` green on both roles; `sparse_world_framework_narration` green on `deep`, red on `fast` on a **rubric definition disagreement, not a malformed output** — see § Decisions 2026-08-09 #8. 🔴 **fixture 1's ground truth is KNOWN WRONG** and is 4.3's to fix: it describes the whole interview while the call scores one answer, and its `not_assessed` was inherited from the Interviewer's probe ledger | **2026-08-09 — first prompt.** Four ordered steps, decline-to-score made a first-class result, and `framework_narration` strengthened after `fast` returned `False` on an answer that walks RICE's letters out loud. **Runs on `fast`** (measured, not inherited) |
| Coach | ⬜ (Phase 5) | — | — |

---

## Current phase — story detail

**Phase 1 stories are defined in `docs/specs/PHASE-1-SPEC.md`.** Wave plan set 2026-07-31:
1.1 + 1.5 in parallel, then 1.2 + 1.3, then 1.4, then 1.6, then 1.7 inline.

- [x] 1.1 ~~Anonymous sign-in and scoped RLS policies~~ — done 2026-07-31. Cross-session denial proven on all six tables with real JWTs through PostgREST, re-proven independently. Output below
- [x] 1.2 ~~Resume upload and text extraction~~ — done 2026-07-31. 18 tests. **Deviates from ARCHITECTURE §1 deliberately** (backend-proxied upload, reasoning in Decisions) and **shipped three em-dashes into candidate-facing copy**, now fixed and guarded
- [x] 1.3 ~~Resume Analyst agent~~ — **DONE 2026-08-02. Split in two, see Decisions 2026-07-31.**
  Ticked on a **conscious acceptance of three flapping cases**, not on a clean run — Karthik's call,
  with the cost and the reopening conditions written into PHASE-1-SPEC § 1.3 and Decisions below
  - [x] 1.3a ~~golden fixtures + assertion harness~~ — done 2026-07-31. 8 fixtures, 23 offline tests, suite deliberately RED. **Independent probe found the spec's most important assertion passing vacuously on all eight cases; fixed and re-falsified.** Output below
  - [x] 1.3b ~~the agent itself~~ — done 2026-08-02. `app/agents/resume_analyst.py`, with the
    case-01 fix **validated against a live control and committed (`27bb749`)**. All eight cases ran
    on `deep` with zero 429s on 2026-08-02: **37 passed, 1 failed.** Ticked with **three flaps
    (01, 02, 05) consciously accepted** — see PHASE-1-SPEC § 1.3 for the cost and what reopens it
- [x] 1.4 ~~`level_candidate` → `confirm_level`, the first real interrupt~~ — **DONE 2026-08-02.**
  Built and committed `aa3a756` in session 7; closed in session 8 by the two measurements it was
  short of. **The single-call assertion is now FALSIFIED, not merely green** — the wrong graph logs
  2 `outcome=ok` records. 8 live tests re-run independently. Output below
- [x] 1.5 ~~Design foundation~~ — done 2026-07-31. All nine boxes. **`make test-web` runs for the first time in the project.** Two deviations found in verification, both below
- [ ] 1.6 Upload and confirmation UI — **split in two.** 1.6b brought forward ahead of 1.4 on
  2026-08-01: 1.4 needs model budget that is exhausted, 1.6b needs none. See Decisions
  - [x] 1.6a ~~shell, anonymous sign-in, upload surface~~ — done 2026-07-31. 33 vitest tests. Env vars proven inlined into the bundle. **One defect found in review, deferred to 1.6b with the reason recorded**. Output below
  - [x] 1.6b ~~confirmation screen, orchestration column states, Realtime on `agent_events`~~ —
    done 2026-08-01. 66 vitest tests (33 → 66). **Realtime under RLS PROVEN with two real
    identities plus a service-role control.** Session-per-upload defect fixed and falsified.
    ~~**Two boxes are built and tested but NOT mounted**~~ → **both mounted and reachable as of
    2026-08-02**, by 1.4's `aa3a756`. A residual Realtime startup race is recorded. Output below
- [x] 1.7 ~~Delete the Phase 0 scaffolding~~ — **DONE 2026-08-02, SCOPE REDUCED.** The delete list
  was wrong: 1.4's tests do NOT replace story 0.7's two-OS-process proof, so `skeleton.py` and both
  `/skeleton/*` routes are **kept as a permanent test harness** on Karthik's call. 5 of 12 Phase 0
  tests deleted, 7 kept and re-run green. `HealthCheck.tsx` deleted in full. See Decisions
  2026-08-02 and the output below

### Phase 0 stories — all complete, kept for the record

Defined in `docs/specs/PHASE-0-SPEC.md`.

- [x] 0.1 ~~Repo scaffold, `.env` handling, `requirements.txt`, Vite app, secret-prefix pre-commit hook~~ — done 2026-07-30, all four acceptance boxes verified with output below
- [x] 0.2 ~~NVIDIA smoke test~~ — done 2026-07-30. Gate resolved: **not 10/10** (`deep` 7-9/10), so validate-retry is mandatory. Streaming, rate-limit logging, and the off-peak re-measure all done
- [x] 0.3 ~~Confirm build.nvidia.com account model~~ — done 2026-07-29: 40 RPM, no credits
- [x] 0.4a ~~Supabase project + connection verified~~ — done: Singapore, session pooler, Postgres 17.6, `check_db.py` connects
- [x] 0.4 ~~Supabase project + schema migration~~ — done 2026-07-30. Six tables, RLS on all, realtime publication, private `resumes` bucket, constraints proven by failed inserts
- [x] 0.5 ~~Postgres checkpointer wired via session pooler, `.setup()` run once~~ — done 2026-07-30. Idempotent, no collision, 6543 failure reproduced, **RLS added to LangGraph's tables**
- [x] 0.6 ~~Two-node graph with `interrupt()` / `Command(resume=...)`~~ — done 2026-07-30. All five boxes, and **the idempotency assertion was falsified against a deliberately wrong graph before being trusted**
- [x] 0.7 ~~Interrupt/resume proven across two separate HTTP requests~~ — done 2026-07-30. Restart proven with **two separate uvicorn subprocesses**, not a rebuilt TestClient
- [x] 0.8 ~~Deploy backend to Render, frontend to Netlify, CORS wired, health check green~~ — done 2026-07-30. Phase gate 6/6, cold start 32.3s, production checkpoint step ~27ms. Output below

---

### Session 10 — 2026-08-05 — Phase 1 closed, Phase 3 half built, and "deselected is not passed"

**Four commits: `b485cb6`, `08d8dba`, `3056bf8`, `1ba75cd`.** Tree clean, nothing deployed.

| Delivered | Evidence |
|---|---|
| **Story 3.1** — agent spec + 5 blind golden fixtures | **Zero tokens.** Suite deliberately RED in 0.17s, before any network call |
| **Story 3.2** — the conduct loop, routes, falsification, HTTP proof | 221 offline · 3 live · 2 golden smokes on `fast` · 3 questions over 3 real HTTP requests |
| **The bridge deleted** | Measured a constant function across 6 varied inputs. Karthik's call |
| **Phase 1 gate #4 closed** | Premise rejected: seniority is company-relative. Propagation asserted and falsified |

**Four things were found by re-verifying rather than by reading a report**, which is the pattern
worth repeating:

1. `ungrounded_figures` was a substring search, so `"roughly 7 designers"` PASSED against a world
   containing no 7 — blind to exactly the figures a model invents, and sitting on top of fixture 3's
   headcount premise.
2. A `getattr(result, "bridge", None)` guard that could only ever no-op, reading as coverage while
   asserting nothing.
3. Three live tests that had never run and could never pass, leaving the phase's central proof half
   complete.
4. A load-bearing test I broke myself in `08d8dba` and shipped.

**The expensive half of this session was two full chain runs. The cheap half — the spec, the blind
fixtures, the figure-check fix, the guard falsification, the six-sample bridge probe, all the docs —
cost almost nothing and found everything.** Same finding as session 9. Front-load the zero-quota
work.

### Session 9 — 2026-08-04 — the two smokes, and what they actually found

**Session 8's prediction held: the uncommitted agents were sound, not abandoned drafts.** Both are
now committed. **But neither passed its golden case as written**, and the value of this session is
the four defects that surfaced — three of which were in the *test suites and shared code*, not in
the agents.

**Baseline before any change, free:**

```
offline suite    147 passed, 82 deselected     <- matches session 8 exactly, dirty tree included
```

**🔴 DEFECT 1, THE IMPORTANT ONE — `app/llm.py` was silently swallowing every schema failure Groq
rejects server-side.** The wrapper's own docstring promised "retries schema failures only: a `None`
return or a `ValidationError`", and Groq's 400 `json_validate_failed` is a schema failure — but it
arrives as `openai.BadRequestError`, hit the `except Exception` transport branch, and was re-raised
**without ever retrying**. The class of failure the wrapper exists to absorb was bypassing it.

Observed on the Planner's first smoke, `fast` folding `grounded_in` into the preceding array:

```
BEFORE   outcome=error error=BadRequestError          <- raised, no retry
AFTER    outcome=invalid error=BadRequestError        <- classified as schema
         outcome=ok                                   <- retry succeeded
         retry_fired=True
```

**That before/after IS the falsification** — the fix was proven by observing the behaviour change
live, not by reasoning about it. Three offline tests now pin it, including the boundary that a 429
must still NOT be retried (broadening the retry to swallow rate limits would be strictly worse than
the bug).

**This is shared code and it affects every agent, including the two shipped in Phase 1.** The full
live suite was NOT re-run, per the portfolio calibration; the offline suite (157) and both smokes
are the evidence.

**DEFECT 2 — the Case Architect's own prompt was the source of a placeholder leak.** A live world
put `"The feature X would increase onboarding completion by 3.1%"` into `supporting_facts`, which is
candidate-facing copy. Root cause was the prompt's own APM example, `"Should we build X into the
onboarding flow?"`. Fixed at the source, plus an explicit ban, plus a new `contains_placeholder_token`
assertion wired into the universal battery — the suite could not previously see this.

**DEFECT 3 — the blind ACV check was a B2B assumption and failed two worlds that were right.**
Spec §5 says implied ACV must be plausible "for the stated stage **and market**"; the blind
implementation dropped the market half and used a flat $50 floor. It rejected $30.75 ARPU over
400,000 users, then $3.91 over 3,200,000 — both ordinary consumer figures. **Conditioned on
`customer_count` rather than lowered**, deliberately: ratcheting the single floor down until the run
passes is the exact failure spec §5 warns about, and it would have destroyed the check for B2B.

**DEFECT 4 — the genericness check demanded the company's full legal name.** `deep` asked "what are
the key strengths and weaknesses of **Ferngrove's** business model?" against a world whose company
is "Ferngrove Media", and the check called it generic. It was under-measuring: the short form and
the possessive are how a real interviewer speaks. Now accepts a distinctive first word, with a
four-character floor so a company called "The Ledger" cannot make every question pass on "The".

**Final smoke results, both on one golden case each, as § Next session instructed:**

```
case_architect  apm_consumer        1 passed in 97.52s    role=fast   retry_fired=False
planner         apm_consumer_world  1 failed in 101.09s   role=deep   retry_fired=False
                  -> grounding PASSES, dimension coverage PASSES, timing PASSES,
                     case_world immutability PASSES, genericness fails on 1 of 7 questions
offline suite   157 passed, 82 deselected, 3.73s
```

**🔴 THE PLANNER NEEDS `deep`. This is the one agent the portfolio calibration's "agents default to
`fast`" does NOT apply to, and it is a correctness constraint, not a quality preference.** Measured:
`fast` (gpt-oss-20b) failed Groq's strict schema validation on `QuestionPlan` **twice in a row**,
raising `StructuredOutputError` — the retry worked and both attempts still failed. `deep` produced a
valid plan first try, every time, with no retry. `QuestionPlan` is the largest generation in the
product (5-7 objects of 7 fields, two of them string arrays). **This is the evidence
AGENT-PLANNER-SPEC §6 explicitly asked for.** `build.py`'s `planner_role` default is back to `deep`.

**The genericness flap is ACCEPTED, not fixed, matching story 1.3's precedent.** Across five `deep`
runs the count went 5 generic -> 3 -> 1 -> 0 -> 1 as the prompt tightened. It now lands at **6 of 7
questions compliant, with a different question slipping each run.** A question that omits the
company name still reads perfectly well to a candidate, so this does not visibly break a demo.
**Reopens if:** it ever exceeds 2 of 7, or if a Phase 3 interview visibly reads as generic.

**🟢 THEN THE WHOLE CHAIN RAN END TO END, which was the phase's real question.** Found after the
first commit: `tests/test_confirm_level.py`'s existing live tests now flow straight through the two
new nodes, because `build.py` chains them after `confirm_level`. No new harness was needed.

```
tests/test_confirm_level.py::test_command_resume_carries_the_candidates_level_into_state
  ResumeAnalysis   -> level_candidate
  CaseWorld        -> generate_case_world node
  QuestionPlan     -> plan_interview node, 7 questions, total_minutes=35
1 passed, 4 warnings in 64.66s
```

Real graph, Postgres checkpointer, across an interrupt and a resume. **And it resumes with a level
DIFFERENT from the assessed one**, so the confirmed-level trap named in the 2.3 brief is covered
too: both nodes ran on the corrected level, and the graph reached END without pausing again.

**The node side effects are proven, by inference and worth stating precisely:** `rest_insert` calls
`resp.raise_for_status()` and neither node catches it, so a chain that completes is proof that all
eight writes (four per node — `started`, the artifact insert, `done`) returned 2xx. **What no test
asserts is the CONTENT of those rows.** That is the honest limit of this evidence.

**⬜ STILL OWED on 2.3: the write-once half of immutability is not falsified.** Immutability *across*
`plan_interview` is asserted and passes. But nothing has watched a second write to `case_world` be
rejected, and the spec is explicit that an immutability rule nobody has seen reject a write is a
comment. Story 0.6's idempotency falsification is the pattern to copy.

**🟢 STORY 2.7 IS DONE, at zero token cost. PHASE 2 IS CODE-COMPLETE.**

Both new agents are in the orchestration column. **The interesting result is how little it took:**
one Realtime subscription already filters on `session_id` rather than on agent, so the two agents
needed a row in a new `AGENTS` table and **no new mechanism at all** — `lib/agentEvents.ts` was not
touched. 1.6b's "later phases add rows here rather than replacing this one" held exactly.

```
vitest    74 passed  ->  80 passed     6 new, all scoped per row
offline   157 passed ->  159 passed    2 new, the copy guard below
tsc -b    clean
```

**🔴 THE EM-DASH GUARD HAD A HOLE, and this story is what exposed it.** `test_user_facing_copy.py`
inspected only `HTTPException` and `*Error(...)` calls. The `_*_SUMMARY` constants in
`app/graph/build.py` are **rendered verbatim to the candidate** by the orchestration column, in
preference to the frontend's own fallback copy, and were never in scope. 2.7 tripled how many there
are. The new check matches on the `_SUMMARY` name suffix, so a future agent's summary is covered the
day it is written.

**It is falsified, not assumed.** Planting an em-dash in `_PLAN_DONE_SUMMARY`:

```
1 failed, 4 passed        FAILED test_no_dashes_in_agent_event_summaries
```

Exactly one test, and the right one. (A first attempt at this falsification wrote the file back with
PowerShell's `Set-Content -Encoding UTF8`, which **adds a BOM in PS 5.1** and broke `ast.parse` on
every file in `app/`, failing all five tests for the wrong reason. Restored with `git checkout` and
redone with an editor that does not add one. Worth knowing before scripting any file round-trip on
this machine.)

**The Realtime startup race does NOT reopen, and the 2.7 box's premise was the wrong clock.** The
box flags these agents as writing sooner after the candidate's action than the Resume Analyst does.
True, and irrelevant: **the settle window is measured from `subscribe()`, not from the triggering
action.** `OrchestrationColumn` sits in `AppShell`'s slot in `App.tsx` OUTSIDE the
`renderConversation()` switch, so it never unmounts, and `useAgentEvents` resubscribes only when
`sessionId` changes — once per candidate. The subscription has been open for the entire upload and
confirmation cycle before the Case Architect writes anything. **Verified by reading `App.tsx`, not
by a probe run** — `probe_realtime.mjs` was not re-run because neither the RLS policies nor the
publication changed. What would reopen it is recorded in the component itself.

**Observed but NOT chased, deliberately:**
- A live world produced `"'story' has 80% usage"` in `supporting_facts` — a fake-round number in
  free text. `banned_round_numbers` only checks the typed percentage fields, not fact strings.
  Cosmetic, does not break a demo.
- Every structured call logs a pydantic `UserWarning: Expected 'none' but got CaseWorld`. Appears on
  all three agents, is not new to this session, and nothing depends on that serialization. Recorded
  so the next session does not mistake it for a fresh defect.

---

### 2.1 / 2.2 / 2.4 — Phase 2's zero-quota half, session 8, 2026-08-02

**Three stories, no LLM calls at all.** Both agent contracts written before either prompt exists,
and the Case Architect's golden suite written blind against its spec. This is the 1.3a discipline
applied deliberately instead of discovered.

```
offline pytest   60 passed, 70 deselected  ->  104 passed, 77 deselected
                 +44 offline (39 from the agent, +5 from my fix below)
                 +7 deselected = the seven live golden cases
collection       46 tests collected in 0.03s, clean
```

**🔴 THE RED-NESS IS PROVEN, NOT INFERRED, AND IT COST NOTHING.** The lazy import fails *before*
any LLM call, so the live tests can be run for free to confirm the suite fails for exactly one
reason:

```
7 errors in 0.07s
ERROR test_golden_case[apm_consumer]  ... and six more
E   ModuleNotFoundError: No module named 'app.agents.case_architect'
```

**Every one is that error and nothing else.** The agent inferred this from reading; running it is
strictly better and free. Worth remembering for story 2.5.

**MY OWN PROBE, written from scratch rather than by re-running the agent's tests**, aimed at
1.3a's exact bug — does a lazy world pass vacuously?

```
LAZY world   -> rejected on all six string fields
HONEST world -> rejected fields: []
VERDICT: the floor rejects silence AND accepts effort
```

**Both halves matter.** A floor that rejected everything would also "pass" the first check and be
useless. This is the third time this project has probed a denial assertion for a floor, and the
first time the floor was already there.

**🔴 THE PROBE FOUND A REAL GAP ANYWAY, in a place the vacuity floor deliberately does not cover.**
`arr_usd` and `size_usd` are figures, not prose, so they are absent from `test_golden`'s
vacuity-floor field list and reach `is_round_dollar_amount` unguarded:

```
BEFORE                                    AFTER
arr_usd=''              ValueError        -> "metrics.arr_usd='' is not a parseable dollar amount"
arr_usd='N/A'           ValueError        -> reported as a violation
arr_usd='unknown'       ValueError        -> reported as a violation
arr_usd='TBD'           ValueError        -> reported as a violation
arr_usd='$18.6 million' ValueError        -> reported as a violation
```

**The gate held either way** — a ValueError still fails the case. What changed is the message.
An unparseable ARR is an *agent* defect and must say so; a raw `ValueError` reads as a broken
harness, **and on this project a confusing red has twice been the thing that got tuned away rather
than fixed.** Fixed in `banned_round_numbers` rather than in `is_round_dollar_amount`, which is
deliberately pinned to raise by its own test. Five parametrized tests added, 99 -> 104.

**🔴 A HARD CEILING STORY 2.3 MUST RESPECT, computed before the prompt is written.** Groq reports
`Requested = prompt + input + max_tokens`, `max_tokens=4096` in `app/llm.py`, against an **8,000
TPM** bucket. **A single request over 8,000 can never succeed, at any pacing.**

```
max prompt for the Case Architect   ~3,704 tokens  ~15,557 characters
Resume Analyst's prompt today       ~2,900 tokens  ~12,200 characters
headroom                            ~27%
_PACE_SECONDS                       90  (projection, not a measured header, so padded
                                         above the 59.3s the arithmetic gives)
```

**27% is not much**, and AGENT-CASE-ARCHITECT-SPEC §2 is a six-model schema with a long constraints
section. **Story 2.3 must measure the real prompt against this ceiling before tuning anything else.**

**The agent's own process caught one bug, which is worth recording as evidence the method works.**
Its first positive control for `implied_acv_implausible` used spec §5's example of 2 customers and
$40M ARR — and *passed*, because a $20M implied ACV is below a `max_acv=50M` default. The control
could not fail. It tightened the ceiling and re-ran. **That is Trap 2 working as designed**, and it
is the same shape as the three false passes this project has caught by hand.

**One deviation to carry into 2.3:** the schema has no structured person field, so the "John Doe"
half of the banned-name control can only be checked against free text (`supporting_facts`,
`situation.leadership_belief`). If `CaseWorld` later gains an exec or persona field, point
`contains_banned_register_name` at it directly.

### 2.5 Planner golden suite — observed output, session 8, 2026-08-02

Delegated, re-verified independently. **Fourth Phase 2 story with zero LLM calls.**

```
offline pytest   104 passed, 77 deselected  ->  147 passed, 82 deselected
                 +43 offline, +5 live, and no other file's count moved
collection       48 tests, clean
RED-ness         5 errors in 0.05s, every one:
                 ModuleNotFoundError: No module named 'app.agents.planner'
```

**MY OWN PROBE, from scratch, on the three properties the suite rests on:**

```
Q1  missing_grounding([], world) -> []                    <- the 1.3a trap is REAL
    empty_grounded_in([empty, populated]) -> [0]          <- and the floor catches it
Q2  'Ferngrove Media' vs its OWN world -> missing []
    'Ferngrove Media' vs the GPM world -> missing ['Ferngrove Media']
Q3  'What would you do?'                        -> generic=True
    'Ferngrove Media is losing activation...'   -> generic=False
```

**🔴 Q1 IS THE ONE THAT MATTERS AND IT IS THE BEST-HANDLED VACUITY CASE THIS PROJECT HAS PRODUCED.**
The suite does not merely have a floor — **it has a test that DEMONSTRATES the trap exists**
(`test_missing_grounding_is_vacuously_empty_on_an_empty_grounded_in_list`) alongside the test that
catches it. That is strictly better than story 1.3a's fix, which added a floor without pinning the
vacuity it was guarding against. If someone later "simplifies" the floor away, a test fails that
explains exactly why it existed.

**A free cross-suite positive control, and it is a genuinely new idea in this project.** The five
hand-written case worlds are asserted to pass **story 2.2's** universal assertions. That proves two
things at once: the Planner is tested against realistic input, and 2.2's checks accept a world a
human considers good. **All five passed with nothing relaxed.** Every previous control here has been
about denial; this one is about a *suite* not being over-strict, which is the failure mode that
gets assertions tuned away.

**BUDGET MEASURED, NOT A BLOCKER — and the spec's own estimate was pessimistic.**

```
largest real case world   senior_pm_platform_world   3,937 chars   937 tokens
spec's estimate                                                  ~1,200 tokens
max prompt = 8000 - 4096 - 1000 input  =  2,904 tokens  ~12,197 characters
_PACE_SECONDS = 90
```

**~12,200 characters is ~22% tighter than the Case Architect's ~15,557**, as expected since
`case_world` is roughly 5x `candidate_profile`. **Story 2.6 must treat ~12,000 as a hard ceiling,
not a target.** The Planner was flagged in its spec as the agent most likely to be structurally
unable to run on the free tier; **it fits, with room, and that question is now closed.**

**A REGEX TRAP THE AGENT CAUGHT IN ITS OWN WORK, worth recording because it is easy to repeat.**
Its round-number check used `\b(?:0|25|50|75|100)\s?%`, which **false-positived on `19.0%`** — a
legitimate organic figure — because `\b` sees a word boundary immediately after the decimal point,
so the trailing `0%` matched as the banned standalone `0%`. Fixed to
`(?<![\d.])(?:0|25|50|75|100)(?!\d)\s?%`. **The suite caught it before the story landed**, which is
the blind-fixture discipline doing exactly what it exists for.

**Two deviations from the brief, both ratified:**
- `GoldenCase.check` takes `(result, case_world)` rather than `(result)` as the Case Architect's
  does. Correct: the Planner's case-specific checks need the world to check against, not the output
  in isolation.
- The genericness term set includes `market.size_usd` and `market.growth_rate_pct` beyond the
  spec's literal enumeration. **This only makes the check more lenient** — more ways for a question
  to prove it is specific — and never weakens rejection of a truly generic one. Ratified.

### PHASE GATE #1 — `make test` DID NOT PASS, and the reason is structural, 2026-08-02

**Do not record this as a pass. It is not one.** But all eight failures are quota, and classifying
them is the only reason that is knowable:

```
8 failed, 122 passed, 21 warnings in 815.16s (0:13:35)

golden 05,06,07,08   4 x TPD 429 on gpt-oss-120b   Used 198515 / 198375 / 198235 / 198095
test_resume_analyst  1 x TPD 429 on gpt-oss-120b   Used 197406, Requested 4442
test_llm retry       1 x TPD 429 on gpt-oss-120b   Used 197393, Requested 7516
confirm_level        1 x TPM 429 on gpt-oss-20b    Used 4722, Requested 7202
test_llm raw_rate    AssertionError -- see below, ALSO quota

ZERO genuine assertion failures.
```

**🔴 THE STRUCTURAL FINDING: `make test` NEEDS MOST OF A FRESH DAY ON `deep`, AND CANNOT SHARE
THAT DAY WITH ANYTHING ELSE — INCLUDING PHASE GATE #4.** `make test-api` runs `pytest tests`, which
**includes `tests/golden/`**.

**The cost, reconstructed from the observed counters rather than estimated:**

```
before make test     ~92,000    golden run ~32k + case-05 A/B ~60k
deep daily cap        200,000
headroom              ~108,000
make test consumed    ALL of it, and STILL 429'd on golden 05-08
                      and on test_llm's ten samples

so a COMPLETING run needs MORE than 108,000. By composition:
  8 golden cases          ~7,500 each      ~60,000
  test_structured_output_raw_pass_rate[deep]  10 samples   ~50,000
  test_retry_wrapper_converges + test_resume_analyst       ~12,000
                                            TOTAL  ~120,000-130,000 on `deep`
```

**An earlier note in this file said ~50,000. That was wrong and is corrected here** — it was taken
from the golden suite's cost alone and missed `test_llm.py`'s ten-sample test, which is the single
most expensive thing in the suite.

**Consequence for planning: gate #1 and gate #4 COMPETE for the same bucket.** Every resume Karthik
uploads through the deployed URL runs `level_candidate` on `deep` (production default, ~5,000 a
resume), so three resumes is ~15,000. **Do gate #1 first on a fresh bucket, then gate #4 with what
is left, or do them on separate days.**

**The gate condition as written is only achievable as the FIRST thing done on a fresh daily
budget.** Run it before any other work, not before handover as CLAUDE.md currently advises for a
paid tier. The Makefile now carries this warning at the `test-api` target.

**🔴 A HARNESS DEFECT THAT MANUFACTURES A FALSE MODEL-QUALITY SIGNAL, and it is the most dangerous
thing in this run.** `tests/test_llm.py:112`:

```
AssertionError: deep scored 0/10, below the 5 floor measured 2026-07-30.
  Failures: ['#1 RateLimitError', '#2 RateLimitError', '#3 RateLimitError',
             '#4 RateLimitError', '#5 RateLimitError', '#6 RateLimitError',
             '#7 RateLimitError', '#8 RateLimitError', '#9 RateLimitError',
             '#10 RateLimitError']
```

**Every one of the ten samples was a 429, and the test reports it as a structured-output quality
collapse.** A future session reading only the headline would conclude `deep` regressed from 7-9/10
to 0/10 and might switch models on it. The evidence is visible in the `Failures:` list, so a
careful reader catches it — but the assertion message is written to be believed.

**Not fixed, deliberately: verifying a fix needs `deep` budget that no longer exists today.** The
fix is to classify `RateLimitError` separately and `pytest.skip` rather than assert a score, the
same shape as the pacing and typography-fold fixes. **This is the third harness defect on this
project that manufactures a failure rather than hiding one** — and unlike the other two, this one
manufactures a *plausible* failure, which is worse.

**What DID pass, and it is most of the suite: 122 tests.** Every RLS policy test, every upload and
extraction test, all seven surviving Phase 0 tests, 7 of 8 `test_confirm_level.py`, and golden
cases 01-04 before the budget ran out.

### 1.7 Phase 0 scaffolding — observed output, session 8, 2026-08-02

Delegated to a Sonnet agent with the coverage map as a named trap. **The agent contradicted its
brief and was right — the fourth time on this project.** The brief carried the phase spec's delete
list; the list was wrong.

**THE FINDING: story 1.4 does not replace story 0.7.** Verified by me directly rather than taken
from the agent's report:

```
test_confirm_level.py   @pytest.fixture(scope="module")  ->  ONE TestClient(app)
                        no uvicorn, no subprocess, no Popen anywhere in the file
test_api.py:7           "Why a subprocess and not a rebuilt TestClient: a fresh
                        TestClient(app) over [the same process] does not prove [it]"
```

The property at risk is checkpoint state surviving a full OS-process teardown, which is what
retired this architecture's central stateless-HTTP risk in Phase 0. **Nothing in 1.4 asserts it.**
Deleting per the list would have removed the proof and left a green suite.

**Karthik's call: keep the skeleton as a permanent harness.** Recorded under Decisions.

**What was actually deleted — 5 of 12 Phase 0 tests, all `live`-marked:**

```
test_interrupt.py   3 deleted (ainvoke-to-interrupt, Command resume, single-LLM-call)
                    3 KEPT   (checkpointer identity, raw checkpoints rows,
                              post-resume aget_state().next == ())
test_api.py         2 deleted (start returns payload, resume 404s)
                    4 KEPT   (health, THE cross-process resume, get_state across
                              processes, CORS preflight)
frontend            HealthCheck.tsx deleted + its mount; no test referenced it
skeleton.py         UNTOUCHED, and both /skeleton/* routes UNTOUCHED
```

**Verified by me, not inherited:**

```
offline pytest       60 passed, 70 deselected      (deselected 75 -> 70 = the 5 live deletions;
                                                    the 60 is unchanged, as it must be)
import app.main      import ok                     <- no dangling import
kept live tests      7 passed in 40.22s            <- test_interrupt.py + test_api.py, both edited
vitest               74 passed (9 files)           <- unchanged
npm run build        clean, index-D0ALTn0n.js 427.60 kB / gzip 121.05 kB
npx oxlint           exit=0
```

**The kept live tests are the ones that mattered to re-run.** The agent edited both files and
removed tests from them; a broken fixture or a stale import would only show under `-m live`. They
cost almost nothing to check — `skeleton.py` calls `get_llm("fast")` with `max_tokens=120` and a
tiny prompt, which is why Phase 0's tests were always cheap.

The agent also corrected three docstrings that had become false: `main.py`'s claim that the
skeleton routes are deleted in 1.7, `build.py`'s claim that `skeleton.py` can be deleted whole, and
`test_interrupt.py`'s naming of a now-deleted test as the file's load-bearing one. Correct, and
beyond what was asked.

### 1.3b golden suite on `deep`, and the case-05 attribution — session 8, 2026-08-02

**THE FIRST GOLDEN RUN ON `deep` WITH ZERO 429s.** Every previous full run lost most of its cases
to quota, so this is the first time all eight were actually measured in one pass. No file changed
to produce it; the budget had simply refilled.

```
01 . · 02 . · 03 . · 04 . · 05 F · 06 . · 07 . · 08 .
1 failed, 37 passed in 526.32s (0:08:46)
retry_fired=False on every case, both previously and again here
FAILED test_golden_case[05_title_scope_mismatch]
  cases.py:70  AssertionError: APM
```

**Cases 02 and 08 both PASSED**, which is worth stating plainly: the case-02 recapitalization
failure recorded on 2026-08-01 did not reproduce. That is a third independent confirmation that
case 02 flaps rather than fails consistently.

**Case 05 failed on line 70, the LEVEL assertion — not the uncertainty one.** The model returned
`APM` for a resume whose title says Group PM, where the case accepts `{PM, Senior PM}`. This is the
case DEV-STATE named on 2026-08-01 as the one the committed case-01 fix could plausibly have
suppressed, and the fix's added boundary is APM-flavoured, so the direction was suspicious enough
to attribute rather than assume.

**THE ATTRIBUTION — an alternating A/B, `deep`, run with the arms DELIBERATELY INVERTED.**
`ab_prompt_control.py` compares working tree against `git show HEAD:`, so the pre-fix prompt
(`27bb749~1`) was checked out into the working tree. **The script's labels therefore mean the
opposite of their names, and its own `VALIDATED` exit line is meaningless here and was discarded:**

```
prompt chars   FIX=11600  CONTROL=12204  delta=-604
  FIX     = working tree = the PRE-FIX prompt
  CONTROL = HEAD         = the COMMITTED fix

 # variant   level  low_confidence_fields                      verdict
 1 CONTROL   APM    ['assessed_level']                         FAIL  APM
 2 FIX       PM     ['assessed_level']                         PASS
 3 CONTROL   PM     ['assessed_level']                         PASS
 4 FIX       PM     ['assessed_level']                         PASS
 5 CONTROL   PM     ['assessed_level','years_pm_experience']   PASS
 6 FIX       PM     ['assessed_level','years_pm_experience']   PASS
 7 CONTROL   PM     ['assessed_level']                         PASS
 8 FIX       PM     ['assessed_level']                         PASS

COMMITTED fix   3 pass / 1 fail        PRE-FIX prompt   4 pass / 0 fail
```

**🔴 THE FEARED REGRESSION DID NOT HAPPEN, and this is a real measured answer rather than a shrug.**
The specific risk was that the committed fix suppresses the `assessed_level` trigger on case 05.
**`assessed_level` was flagged in 8 of 8 A/B runs, and in the golden failure too — 9 of 9.** The
trigger fires exactly as it should on the case that needs it. Case 06, the other case that needs
the trigger to fire, passed in the golden run with `assessed_level` in its flags. **05 and 06 are
confirmed unregressed on the thing that was actually at risk.**

**What remains is a THIRD flap, and it is a different mode from the other two.** Case 05's *level*
lands on `APM` sometimes. Counting every observation of each prompt on this fixture:

```
COMMITTED fix    2 fail / 5 observations     (golden run + A/B arm)
PRE-FIX prompt   0 fail / 4 observations
```

**That is not enough to blame the fix.** Fisher's exact on 2/5 versus 0/4 is p ≈ 0.44 — nowhere
near the p ≈ 0.05 the case-01 validation reached, and this project has already recorded three false
passes taken from weaker evidence than that. **Do not revert the fix on this table.** The honest
statement is: case 05 flaps on `deep`, the fix is not shown to have caused it, and it is not
cleared either.

**So three of eight cases now flap, not two.** 01 (`years_pm_experience`), 02 (recapitalization),
05 (level → APM). Each is a different failure mode, which argues against one prompt edit fixing
them and against the flap being one bug.

**Budget spent this session on `deep`: ~32k on the golden run plus ~60k on the A/B, ~92k of
200,000.** The A/B costing a third of a day to return p ≈ 0.44 is itself worth recording: **at this
flap rate, 4 pairs is underpowered.** A case failing ~25-40% of the time needs more pairs than one
that flaps ~50/50, and the case-01 validation got its p ≈ 0.05 only because its control failed
twice. Budget 6-8 pairs for the next attribution, or expect to learn nothing.

### 1.4 CLOSED — the two missing measurements, session 8, 2026-08-02

**Story 1.4 is DONE.** Session 7 built and committed it (`aa3a756`) but could not tick it: the 8
live tests were the Sonnet agent's run only, and the single-call assertion had never been observed
failing. Both models were at their daily cap. Both are now measured, and no code changed to do it.

**🔴 THE ONE THAT MATTERS — the single-call assertion is FALSIFIED.** `falsify_single_call.py`
builds the WRONG graph, with the LLM call placed above `interrupt()` in the same node, which is
precisely the bug CLAUDE.md's load-bearing rule exists to prevent, and applies the real test's own
`outcome=ok` counting to it:

```
WRONG graph (LLM call above interrupt, same node)
  outcome=ok records at pause       : 1
  outcome=ok records after resume   : 2
  assertion 'exactly 1 across the cycle' -> FAILS as it must
  residue: sessions rows for this thread = 0
EXITCODE=0
```

**The `at pause : 1` line is what makes the `after resume : 2` mean anything** — it proves the
wrong graph was executing normally up to the interrupt, so the second record is the node genuinely
re-running from the top rather than an artefact of a broken probe. Same shape as story 1.1's
`A/own = 1` column and 1.3a's positive control. This project has now caught three false passes on
assertions that could not fail; this one was checked before it could become the fourth.

**Then the 8 live tests, re-run by me rather than inherited:**

```
tests/test_confirm_level.py -m live    7 passed, 1 failed in 184.51s
  FAILED test_command_resume_carries_the_candidates_level_into_state
  -> 429 tokens per minute (TPM): Limit 8000, Used 3505, Requested 5144
  -> ZERO assertion failures

same test, re-run alone                1 passed in 9.88s
```

**Classified before believed, and it was quota.** That is the fifth time on this project that a
red golden/live run was rate limiting rather than a defect. `test_confirm_level.py` has **no pacing
between tests at all** — the same harness gap the golden suite had before `_PACE_SECONDS` went to
60. One case requests ~5100 tokens against an 8000 TPM bucket refilling at 133/sec, so two
back-to-back live tests collide by arithmetic. **Recorded as a known harness gap, not fixed**: it
manufactures failures rather than hiding them, and it is loud. Fix it if the file grows.

**Residue after everything, queried directly:**

```
sessions 0 · resumes 0 · agent_events 0 · transcript_turns 0
answer_evaluations 0 · case_worlds 0 · checkpoints (distinct threads) 0
```

**A warning that fires on every live run, chased down and benign.** `pydantic/main.py:426
UserWarning: Expected 'none' but got 'ResumeAnalysis'`. It is not our state or our checkpointer:
`InterviewState.candidate_profile` is a `dict` and the node calls `.model_dump()` before writing,
so a `ResumeAnalysis` never enters state. It comes from the OpenAI SDK's parsed-response model,
where `parsed` is declared `None`-typed. Upstream noise. Recorded so the next session does not
spend budget re-diagnosing it.

**Baselines at the start of the session, all matching session 7:** offline `60 passed, 75
deselected` · vitest `74 passed (9 files)` · `git status` clean at `0f9fd8b`.

### 1.4 level_candidate → confirm_level — observed output, session 7, 2026-08-01

`app/graph/build.py` (two real nodes), `app/main.py` (two routes plus an `_authorize_session`
refactor), `app/supabase_client.py` (`rest_update`), `tests/test_confirm_level.py` (new, 8 live),
`frontend/src/{App.tsx,lib/api.ts,lib/levelAssessment.ts,lib/agentEvents.ts,components/UploadSurface.tsx}`
plus two test files. Committed `aa3a756`. Delegated to a Sonnet agent, re-verified independently.

**Verified by me, not inherited from the agent's report:**

```
offline pytest    60 passed, 75 deselected      (the +8 deselected are the new live tests)
vitest            74 passed                     (66 -> 74)
npm run build     clean, index-fpBkC6vS.js 428.96 kB / gzip 121.59 kB
npx oxlint        exit=0
DB residue        sessions · resumes · agent_events · transcript_turns
                  answer_evaluations · case_worlds · checkpoints   ALL 0
design greps      no em-dash in rendered copy · no console.* · no bare
                  duration-standard · no lucide
```

**The three structural traps, checked by READING the code rather than by a green test**, because
each is the kind of thing a passing suite does not notice:

```
T1  confirm_level's body is `chosen = interrupt({...})` then `return {...}`.
    Nothing above the interrupt line.                        build.py:145-153
T2  the single-call assertion filters `outcome=ok` records ONLY, so a
    legitimate validate-retry (empty/invalid THEN ok) cannot fail it while
    a doubled node execution still does.        test_confirm_level.py:85-101
T3  analyse_resume stays pure: no supabase/httpx import, no session, no
    agent_events row. The eight golden cases still call it with no database.
```

The `_authorize_session` refactor **touches story 1.2's proven security path**, so it was read
rather than trusted: 401 bad token, 404 unknown session, 403 wrong owner, now shared by all three
routes. A NULL `user_id` compares unequal and so **fails closed to 403**.

**🔴 WHAT IS NOT VERIFIED, AND IT IS THE BOX THAT MATTERS MOST. Do not read this story as done.**

The 8 live tests in `tests/test_confirm_level.py` are **the agent's run only**. They could not be
re-run: both models hit the 200,000-token daily cap during this session.

```
deep (gpt-oss-120b)   199,325 / 200,000     spent validating the case-01 fix
fast (gpt-oss-20b)    199,086 / 200,000     spent by the agent's 8 live tests
```

**The single-call assertion is UNFALSIFIED.** A probe was written that builds the WRONG graph —
the LLM call placed above `interrupt()` in the same node, which is exactly the bug CLAUDE.md's
load-bearing rule exists to prevent — drives the same start/resume cycle, and applies the test's
own `outcome=ok` counting to it. **It 429'd on `fast` before executing.** Until the wrong graph is
observed logging **2** `outcome=ok` records, that assertion is correct by inspection but not proven
able to fail. **Story 1.3a's most important assertion passed vacuously on all eight cases**; this
project does not trust a counter it has not seen go red.

**The probe is written, committed, and takes no arguments** — it was moved out of the scratchpad so
it survives the session that could not run it:

```
backend/.venv/Scripts/python.exe backend/scripts/falsify_single_call.py

EXPECT: "outcome=ok records after resume : 2"  and  "FAILS as it must"
exit 0 = the assertion can detect the bug     exit 2 = it is VACUOUS, 1.4 is not done
~2 `fast` calls. Cleans up its own sessions/checkpoint rows.
```

**The Realtime startup race from 1.6b is resolved as MOOT, and the reasoning holds up.** The
`agent_events` subscription starts when `App.tsx` receives `sessionId` from `POST /session`, which
is before the resume upload begins; the first real `agent_events` row cannot land until after a
full upload round trip plus a separate `POST /session/{id}/level`. That is several seconds against
the 2s settle the 1.6b probe measured as sufficient. No delayed re-fetch added. **This is reasoning,
not a measurement** — if any future agent writes an event on session start, it reopens.

**`.mono-num`** needed nothing new: 1.6b's `ConfirmationScreen` already applies it to
`years_pm_experience`, and `assessed_level` is a string enum rather than a numeral.

**One scope addition the agent flagged against its own brief**, correctly: the confirm route's
request body is constrained to `Literal["APM","PM","Senior PM","GPM"]`. The frontend already
restricted this at the type level; the backend previously accepted any string. Beyond the
acceptance boxes, and right.

### 1.3b case-01 fix validated and committed — observed output, session 7, 2026-08-01

`backend/app/agents/resume_analyst.py` (the prompt fix session 6 left uncommitted), committed as
`27bb749`. No other file changed. Sanity checks before any LLM call: **offline 60 passed / 67
deselected · vitest 66 passed · deployed `/health` 200.**

**THE MEASUREMENT THAT CLOSED IT — an ALTERNATING A/B on `deep`, with the control loaded byte-exact
from `git show HEAD:` rather than reconstructed by string surgery.** Fixture 01, 60s pacing, both
arms in the same session:

```
 # variant  level  low_confidence_fields      verdict
 1 CONTROL  APM    ['assessed_level']         FAIL
 2 FIX      APM    []                         PASS
 3 CONTROL  APM    []                         PASS
 4 FIX      APM    []                         PASS
 5 CONTROL  APM    []                         PASS
 6 FIX      APM    []                         PASS
 7 CONTROL  APM    ['years_pm_experience']    FAIL
 8 FIX      APM    []                         PASS

FIX 4 pass / 0 fail       CONTROL 2 pass / 2 fail
plus 2 further FIX passes (one pytest run before, one inside the full suite after) = FIX 6/6
```

**Alternating is the whole design, and it is what session 6's method lacked.** Running all four fix
runs first and the control afterwards cannot separate "the fix works" from "the flap is not
happening today" — which is exactly how the `fast` false pass got recorded. Interleaving puts both
arms under the same serving conditions. **This control could fail, and did, twice.** Fisher's exact
on 6/6 versus 2/4 is p ≈ 0.05: supported, not overwhelming.

**🔴 CONTROL RUN 7 IS THE MOST IMPORTANT LINE IN THAT TABLE, and it is not good news.** It failed
on `['years_pm_experience']`, **not** `['assessed_level']`. That is a *second, independent*
over-flagging mode on the same fixture, and the committed fix says nothing about that trigger.
Fixture 01 is an APM rotational program, which the prompt's transition trigger explicitly excludes
("a student internship that leads directly into the same company's formal APM or new-grad
rotational program"), so the model is violating a boundary the prompt already spells out.
**"Case 01 is now stable" is a stronger claim than this evidence carries. Do not record it.**

**FULL SUITE ON `deep` — 7 failed, 31 passed. Six of the seven are quota, and classifying first is
the only reason that is knowable:**

```
01_apm_rotational          PASS            <- 6th consecutive clean fix observation
02_pm_owns_area            FAIL   AssertionError, genuine
03..08                     FAIL   429 TPD, six of them, zero assertion failures
                                  "Limit 200000, Used 199325, Requested 5094"
retries fired              0 on every case that ran
```

**Case 02's failure is real, and it is ONE CHARACTER.** The model returned a `notable_outcomes`
quote beginning `cut checkout abandonment...`; the fixture reads `Cut checkout abandonment...` at
the start of a sentence. Checked against the fixture directly rather than assumed, because
session 6's near-identical "fabrication" on case 08 turned out to be a U+2011 hyphen:

```
exact substring present : False
fixture text            : "...9,200 failed orders a month. Cut checkout abandonment from
                           31.7% to 24.2% over five months by removing two redundant..."
non-ASCII in fixture 02 : none relevant (accented letters in the name only)
```

**The assertion is correct and must NOT be relaxed.** The prompt forbids this explicitly ("do not
lowercase a sentence-initial word to make it fit grammatically into your list"), and session 6
deliberately kept `recapitalized fabrication still rejected` as a control on the typography fold.
Folding case would dismantle that control and let genuinely fabricated spans through.

**THEN THE HYPOTHESIS THAT DIED, and it is the session's second most useful result.** DEV-STATE
recorded `fast` fabricating a quote on case 02 on 2026-08-01, so case 02 looked like a *stable
cross-model* prompt weakness — which would have made `fast` a legitimate testbed for it, unlike the
case-01 flap. Measured instead of assumed:

```
case 02, role=fast, 3 runs   PASS PASS PASS    3/3 clean
```

**So case 02 flaps too, and `fast` is not a valid testbed for it either.** Two of the eight cases
are now known to flap on `deep` against identical input. That is the finding that keeps story 1.3
open, and it is a larger problem than the single case session 6 described.

**Budget: `deep` is spent at 199,325/200,000** and refills at roughly 138 tokens/min, so about one
case per hour. `fast` had budget and 3 runs were spent on the case-02 probe. **Cases 03-08 have not
run on `deep` since the fix landed.**

Also observed, not a story: **deployed cold start measured 42.4s**, against the 32.3s recorded in
Phase 0. Same free tier, same region. Worth re-measuring before any demo rather than trusting 32.3s.

### 1.6b confirmation UI and Realtime — observed output, 2026-08-01

`frontend/src/lib/{types,session,agentEvents,agentStatus}.ts` + tests,
`components/ConfirmationScreen.tsx` (new), `components/OrchestrationColumn.tsx` (rewritten),
`UploadSurface.tsx` + `App.tsx` (session hoisting), `scripts/probe_realtime.mjs`.

```
npm test        8 files, 66 passed (66)      (33 -> 66)
npm run build   ✓ built in 754ms   index-BJmij3hO.js 421.76 kB │ gzip 120.14 kB
npx oxlint      exit=0
```

**🔴 REALTIME UNDER RLS IS PROVEN — the phase's riskiest unknown is retired.** Re-run
independently, not taken from the agent's paste. Two real anonymous identities, real JWTs, a
real `postgres_changes` subscription:

```
check                            expected  observed  verdict
A receives its OWN row (A/own)   1         1         PASS   <- positive control
A receives B's row     (A/Bs)    0         0         PASS   <- denial

CONTROL — service role (bypasses RLS), same two INSERTs
  service receives A's row  1      service receives B's row  1
```

**The `A/own = 1` column is again what makes this mean anything**, and the service-role control
is the second floor: it proves the publication and the delivery pipeline are alive, so `A/Bs = 0`
is RLS denying a row rather than nothing being delivered at all. Story 1.1's lesson applied
without being re-learned.

**Residue after the probe: zero on every table**, checked directly rather than trusted:

```
auth.users 0 · sessions 0 · agent_events 0 · resumes 0 · transcript_turns 0
answer_evaluations 0 · case_worlds 0 · checkpoints (distinct threads) 0
```

**KNOWN RESIDUAL RISK, and it is NOT closed: a startup race in Realtime delivery, independent of
RLS correctness.** The agent measured the positive control failing **2 of 8 runs at zero settle
time, and passing 3 of 3 with a 2s delay** after `subscribe()` returned SUBSCRIBED. The
service-role control received every row in those same runs, which isolates it to the RLS-scoped
subscription rather than the publication. **Neither fetch order closes it** — the fetch snapshot
predates the row and the subscription is not yet delivering, so it falls between them.

Not fixed, deliberately, and the reason is timing rather than confidence: the Resume Analyst takes
seconds to answer, so its events land long after the settle window. **Story 1.4 writes the first
real `agent_events` and must re-check this.** If any agent ever writes an event immediately on
session start, add a delayed re-fetch after SUBSCRIBED. Documented at the top of
`lib/agentEvents.ts`, where the next person to touch it will actually read it.

**The 1.6a session-per-upload defect is fixed, and the fix was falsified rather than assumed.**
`useCandidateSession()` hoists creation to `App.tsx` and caches the in-flight promise. Proven to
gate by deliberately breaking the hoisting and confirming the suite goes red:

```
BROKEN on purpose:  3 failed | 1 passed (4)
  × reuses the same session across repeated calls -- the 1.6a defect this story fixes
  × collapses two concurrent calls into a single createSession request
  × allows a retry to create a fresh session after a failed attempt
  AssertionError: expected "vi.fn()" to be called 1 times, but got 2 times
RESTORED:  66 passed (66)
```

It also clears the cached promise on failure, so a failed attempt does not permanently wedge the
journey — covered by the fourth test.

**Design rules verified by my own greps across `frontend/src`, not by the agent's report:**

```
em-dash / en-dash   only in code comments and describe() strings; NONE in rendered copy
console.*           zero occurrences        <- the JWT is still never logged
duration-standard   zero BARE uses; every one is duration-(--duration-standard)
lucide              only in icons.tsx's own comment and index.css.test.ts's guard
```

**Orchestration states are triple-encoded, which is better than the box required**: shape
(`○ ◉ ● ⚠`), colour, AND a text label, plus `role="status" aria-live="polite"`. The box asked for
shape as well as colour; colour-blind and screen-reader users both get a real signal.

**TWO BOXES ARE BUILT AND TESTED BUT NOT REACHABLE, and must not be read as done.**
`ConfirmationScreen` renders the profile, level, rationale, the correction control, and the
`low_confidence_fields` marking — all covered by tests — but **it is deliberately not mounted in
`App.tsx`.** Nothing produces a real `ResumeAnalysis` until story 1.4 builds `level_candidate`, and
mounting it against fixture data would show a candidate fabricated results about their own resume.
**The agent proposed this against its own brief and was right.** Story 1.4 mounts it via the
`onConfirm` contract already defined on the component.

**Dependency this creates for 1.4, stated so it is not discovered late:** `frontend/src/lib/types.ts`
mirrors the backend `ResumeAnalysis` / `CandidateProfile` field for field, and `api.ts` carries a
`submitLevelCorrection` seam that is defined and never called. **1.4 wires that seam and is not free
to change the shape casually** — the frontend tests are written against it.

### 1.3b golden-suite reliability — observed output, 2026-08-01

`backend/tests/golden/resume_analyst/assertions.py` (typography fold),
`test_assertions.py` (+7 tests), `test_golden.py` (pacing). `app/agents/resume_analyst.py`
carries an uncommitted prompt fix — see § Next session.

**Cases 07 and 08 finally ran on `deep`, which is what this session opened to do.** 07 passed
first time. 08 failed on the suite's most important assertion, and the failure was the harness's
fault, not the model's:

```
AssertionError: 08_engineer_transition: fabricated scope_evidence quote(s):
  ['Shipped a plugin system that let three external teams build their own extensions,
    replacing a hard‑coded list of nine built‑in commands, and used weekly usage logs
    to decide which two legacy commands to deprecate.']
```

**Character-level diff against the fixture, because "looks identical" is not evidence:**

```
non-ASCII in the model's quote : U+2011 NON-BREAKING HYPHEN
non-ASCII in fixture 08        : (none)
char-by-char, quote vs fixture sentence, same length:
  idx  98: model U+2011 != fixture U+002D HYPHEN-MINUS
  idx 123: model U+2011 != fixture U+002D HYPHEN-MINUS
  total differing positions: 2   out of 233
```

42 words reproduced exactly, two hyphens rendered typographically. **The most important assertion
in the suite was reporting a fabrication that did not happen.** Closed with a content-neutral
`fold_typography`, and re-falsified in both directions rather than just checking 08 went green:

```
typographic hyphen variant accepted            PASS
fabrication WEARING a typographic hyphen       still rejected
quote that swaps in an em-dash                 still rejected   <- the fold must not launder it
recapitalized fabrication                      still rejected   <- case-sensitivity intact
empty-list vacuity floor                       intact
offline suite   53 -> 60 passed, 67 deselected
08 on deep      1 passed in 35.87s
```

EM_DASH and EN_DASH are deliberately excluded from the fold. They are distinct punctuation this
project bans in candidate-facing copy, not renderings of a hyphen; folding them would let a quote
introduce a banned character and still read as verbatim.

**The fold cannot regress a previously-passing case**, and this was checked rather than argued:
the only non-ASCII characters in any of the eight fixtures are `U+00E1`, `U+00E9`, `U+00F3`
(accented letters in names). None are in the fold map, so `fold_typography(source) == source` on
every fixture and the fold can only widen the quote side.

**🔴 THEN THE REAL PROBLEM: CASE 01 FLAPS AT `temperature=0`.** Four observations on `deep`,
identical input:

```
2026-07-31 (recorded)   PASS
run A, full suite       FAIL   low_confidence_fields=['assessed_level']
run B, cases 01+05 only PASS
run C, full suite       FAIL   low_confidence_fields=['assessed_level']
```

Case 05 flapped too, failing in run A and passing in B and C. **Nothing is shared between cases** —
each is an independent call with no conversation state — so this is model variance, not test
pollution. Fixture 01 is a clean APM: the title says Associate Product Manager and the scope is a
single screen plus a toggle built on someone else's roadmap, so the prompt's title-vs-scope trigger
has no disagreement to fire on.

**A prompt fix was written** — an explicit negative boundary on that trigger, matching the style of
the negative boundary trigger 2 already carries. **It is unvalidated.** `deep` hit its daily quota
before it could be tested:

```
429 tokens per day (TPD): Limit 200000, Used 196348, Requested 7565
```

**THE CONTROL THAT CHANGED THE CONCLUSION.** With `deep` exhausted, the fix was measured on `fast`,
which has its own bucket, and came back 5/5 clean. **That proved nothing, and running the control
is the only reason it was not recorded as a pass:**

```
fixture 01, role=fast, 5 runs each
  WITH the prompt fix       PASS PASS PASS PASS PASS   5/5
  WITHOUT it (reverted)     PASS PASS PASS PASS PASS   5/5   <- fast never flapped
```

`fast` does not exhibit the flap at all, so a green run there is not evidence about a fix aimed at
`deep`. **This is the project's third recorded false pass caught by an independent control**, after
story 1.1's `A/own = 1` column and story 1.3a's vacuity probe. Same shape every time: a measurement
that cannot fail is not a measurement.

**Second harness defect, found by reading a failure message instead of trusting the label: the
golden suite's own pacing is too short, so it was recording rate limits as prompt failures.**

```
first fast run    2 "failures" (06, 08)  -> both 429 TPM, zero assertion failures
  "Limit 8000, Used 1177, Requested 7516"    <- the 8000 is a refill rate, not our usage
```

The arithmetic was never going to work. The prompt grew to ~2900 tokens, so one case now requests
~7500 against an 8000 TPM bucket refilling at 133 tokens/sec: **~56s needed, 30s configured.**
Raised to 60s. **Raise it in step with the prompt, or the suite silently stops measuring whichever
cases land last in the run.**

**Final measured state, and it is honest rather than tidy.** Both models hit the 200k/day ceiling:

```
deep (gpt-oss-120b)  07 PASS  08 PASS (after the fold)
                     01 flaps ~50%, 05 flapped once
                     prompt fix UNVALIDATED - quota exhausted at 196,348/200,000
fast (gpt-oss-20b)   01 5/5 clean with fix AND 5/5 without - no flap on this model
                     run 1 (30s pacing)  6 measured, 6 passed, 06+08 lost to TPM
                     run 2 (60s pacing)  01 03 PASS, 02 FAILED on a fabricated
                                         notable_outcomes quote, 04-08 lost to TPD
                     quota exhausted at 195,988/200,000
retries fired        0, on every case of every run, both models
offline suite        60 passed, 67 deselected
```

**On the ARCHITECTURE §4 model question, the answer moved and is now genuinely open.** `fast` is
immune to the case-01 flap across 10 observations, which is a real point in its favour. But it
fabricated a quote on case 02 today, where `deep` passed 02 — the reverse of what 2026-07-31
recorded. Neither model is stable across days. **Do not switch the assignment on this evidence.**

### 1.3a golden fixtures and assertion harness — observed output

`backend/tests/golden/resume_analyst/` (8 `.txt` fixtures, `cases.py`, `assertions.py`,
`test_golden.py`, `test_assertions.py`) plus `backend/tests/test_resume_analyst.py`.

**The suite is deliberately RED and must stay red until 1.3b lands.** It was written before and
blind to the prompt, so 1.3b cannot tune a fixture until its prompt passes.

```
offline suite     53 passed, 67 deselected in 2.44s      (30 -> 48 from the story, -> 53 with my fix)
golden suite      23 passed, 8 errors in 0.20s
  every error: ModuleNotFoundError: No module named 'app.agents'   <- the only reason, by design
fixtures          263-304 words each, all eight
em/en dash in fixtures: none
```

Collection stays clean because the import is lazy, inside a session-scoped fixture. A module-level
import would make `pytest tests -m "not live"` **error during collection** — deselection happens
after collection — breaking the project's fastest feedback loop for every file, not just this one.
Deliberately not `pytest.importorskip`, which would silently skip forever once the module exists
but is misnamed.

**INDEPENDENT PROBE — the spec's single most important assertion was passing vacuously on all
eight cases.** Found with a probe written from scratch, not by re-running the agent's tests:

```
PROBE 1 - the lazy agent: scope_evidence=[] notable_outcomes=[]
  universal assertions -> PASS          <- quoting NOTHING passed
PROBE 2 - the fabricating agent: invents a quote   (positive control)
  universal assertions -> FAIL fabricated scope    <- the check DOES discriminate
PROBE 3 - the lazy shape against all eight cases
  01..08  ->  PASS PASS PASS PASS PASS PASS PASS PASS
```

`missing_verbatim_quotes([])` returns `[]`, so **silence beat effort.** This is story 1.1's
`A/own = 1` column in different clothes: a denial assertion with no positive control passes when
the mechanism under test is dead. Probe 2 is what makes the finding meaningful — the check itself
was correct, it just had no floor.

Fixed with `empty_quote_lists()` and re-falsified in both directions, because a fix that makes
everything fail is not a fix:

```
AFTER — lazy shape       01..08  ->  FAIL empty ['scope_evidence', 'notable_outcomes']  (x8)
AFTER — honest shape     01..08  ->  PASS PASS PASS PASS PASS PASS PASS PASS
```

`scope_evidence` has no exception; `notable_outcomes` is relaxed only for fixture 07, which states
zero results and where empty is the honest answer. A `test_exactly_one_case_expects_no_outcomes`
guard stops a future edit relaxing it everywhere and silently ending the gate.

**Second defect, in the brief rather than the agent's work: retry detection missed half the
retries.** `_LoggedStructured` logs `outcome=empty` for `deep` returning `None` **and
`outcome=invalid` for a `ValidationError`** — both trigger a retry. My brief named only the first,
so the file would have recorded "retry never fired" while retries were firing, against the one
acceptance box that exists to stop that being assumed.

```
outcome=empty    retries=True  detected=True  OK
outcome=invalid  retries=True  detected=True  OK      <- was False before the fix
outcome=ok       retries=False detected=False OK
```

### 1.6a shell, anonymous sign-in, upload surface — observed output

`frontend/src/lib/supabase.ts`, `lib/api.ts`, `components/{AppShell,UploadSurface,
OrchestrationColumn,EvaluationColumn}.tsx`, two test files, `App.tsx`, `vite.config.ts`.

```
npm test      33 passed (33)        (25 -> 33; the 25 from story 1.5 still green)
npm run build ✓ built in 783ms      dist/assets/index-B97giJQ4.js  419.21 kB │ gzip: 119.43 kB
npx oxlint    exit=0
```

**Env vars proven inlined into the built bundle, not merely referenced** — the story 0.8 / 1.5
lesson, since Vite only inlines what code actually reads:

```
dist/assets/index-B97giJQ4.js   supabase project ref occurrences: 1
                                API URL occurrences:              2
```

**Design rules verified by grep rather than by claim**, across all of `frontend/src`: zero
em-dashes and en-dashes outside story 1.5's comments (which the rule exempts), zero bare
`duration-standard`, zero `lucide`, and **no `console.*` anywhere** — so the JWT is never logged.
It appears only in two `Authorization: Bearer` headers.

**The frontend/backend contract checked against `app/main.py` directly**, not assumed: form field
`file`, `POST /session` → `{session_id}`, `POST /session/{id}/resume` → `{resume_id, storage_path}`,
errors as `{"detail": ...}`. All four match.

**`XMLHttpRequest` instead of `fetch`, and the reasoning is correct.** Only XHR's `upload` progress
event distinguishes "bytes still on the wire" from "bytes arrived, server is extracting text" —
that is the uploading/parsing boundary the story requires, and `fetch` has no equivalent signal.

### 1.2 resume upload and text extraction — observed output

`backend/app/resume.py` (pure, no network), `backend/app/supabase_client.py` (httpx against
Auth/PostgREST/Storage), two new routes in `app/main.py`, `backend/tests/test_resume_upload.py`.

**Driven end to end against a real local server, with real anonymous tokens and real files —
not by re-running the agent's tests:**

```
=== auth on POST /session ===
  no Authorization header -> 422        garbage token -> 401
  valid A token           -> 200 {"session_id":"56691565-..."}
  session A user_id == A uid: True      <- populated from the JWT, not from the client

=== THE SECURITY ONE: can B upload into A's session? ===
  B uploads to A's session -> 403 {"detail":"This session does not belong to the calling identity."}
  no token                 -> 422       unknown session -> 404

=== content inspection, not extension ===
  .pdf that is plain text  -> 400 {"detail":"Unsupported file. Please upload a PDF or DOCX resume."}

=== no-text-layer PDF ===
  blank/scanned PDF        -> 400 "This PDF has no extractable text. It looks like a scanned or
                                   image-only document. Please upload a text-based PDF..."

=== residue after every rejected upload ===
  resumes rows: 0      storage objects in bucket: 0
```

**Rejected uploads leave nothing anywhere**, because extraction runs *before* the storage write.
There is also a compensating delete if the database insert fails after a successful upload, so a
half-finished request cannot orphan an object.

```
offline suite            30 passed, 58 deselected in 2.42s   (21 -> 27 from the story, -> 30 with the copy guard)
tests/test_resume_upload 18 passed in 40.31s                 (re-run independently)
tests/test_llm.py         7 passed in 481.98s
full live suite          85 passed in 3765.07s               (agent's run, see the contention note)
```

### 1.1 scoped RLS policies — observed output

`backend/migrations/0002_rls_policies.sql` and `backend/tests/test_rls_policies.py` (15 tests),
plus a deliberate rework of `test_schema.py`'s denial test.

**The policy inventory, queried straight from `pg_policies` rather than read off the migration:**

```
table                cmd     roles              policy
agent_events         SELECT  {authenticated}    own session agent_events
answer_evaluations   SELECT  {authenticated}    own session answer_evaluations
case_worlds          SELECT  {authenticated}    own session case_worlds
resumes              SELECT  {authenticated}    own session resumes
sessions             INSERT  {authenticated}    own session insert
sessions             SELECT  {authenticated}    own session select
transcript_turns     SELECT  {authenticated}    own session transcript_turns

policies on checkpoint% tables: 0    policies granting anon: 0
public tables without RLS:      0    resumes bucket public:  False
```

**CROSS-SESSION DENIAL — re-proven independently, with a probe written from scratch rather than
by running the agent's tests.** Two fresh anonymous identities, real JWTs, real PostgREST calls:

```
table                   A/own   A/Bs  B/own   B/As   verdict
sessions                    1      0      1      0   PASS
resumes                     1      0      1      0   PASS
case_worlds                 1      0      1      0   PASS
transcript_turns            1      0      1      0   PASS
answer_evaluations          1      0      1      0   PASS
agent_events                1      0      1      0   PASS
```

**The `A/own = 1` column is the one that makes the test mean anything.** Had the token been
malformed, every cell would read 0 and the denial columns would pass vacuously. Also probed the
unfiltered `select=*` a curious candidate would actually type — one row on every table, never two.
Raw `anon` key with no user token: 200 with 0 rows, on every table.

```
full live suite : 67 passed in 382.61s (0:06:22)     <- run independently, 52 -> 67
offline suite   : 21 passed, 46 deselected in 2.00s
migrate.py      : ok on both files, twice            <- idempotency
residue after   : auth.users 0 · sessions 0 · resumes 0 · transcript_turns 0 · agent_events 0
```

### 1.5 design foundation — observed output

`frontend/src/index.css` (full rewrite), `src/lib/icons.tsx`, `src/index.css.test.ts`,
`src/assets/fonts/` (Geist + Geist Mono variable woff2, OFL licence kept alongside), `DESIGN.md`
at the repo root, plus vitest wired into `vite.config.ts` and `package.json`.

```
npm run build
  dist/assets/Geist-Variable-Bj2R_7yk.woff2       69.65 kB
  dist/assets/GeistMono-Variable-Dispecij.woff2   71.36 kB
  dist/assets/index-KSU7xFWs.css                  14.05 kB │ gzip: 3.93 kB
  ✓ built in 356ms

make test-web        25 passed (25)      <- FIRST TIME THIS TARGET HAS RUN
npx oxlint           exit=0, clean
backend offline      21 passed, 31 deselected in 2.47s   (backend untouched, git status clean there)
```

**The agent proved the accent hex reaches `dist/`. That was not the assertion that mattered**, and
finding the gap is what independent re-verification bought this time. `#3A63D0` reaches the bundle
from the plain `:root` block whether or not Tailwind's `@theme` layer works at all. What story 1.6
actually depends on is `@theme` **generating utilities** through a `var()` indirection, which was
untested. Probed by building a throwaway component that uses them and grepping the emitted CSS:

```
EMITTED  .bg-background   .text-text-secondary   .border-border   .rounded-card
EMITTED  .shadow-elevated  .font-mono  .ease-standard  .rounded-control  .text-error
MISSING  .duration-standard          <- the one that does not exist
.bg-accent\/40 { background-color: color-mix(in oklab, var(--color-accent) 40%, transparent) }
```

So the `var()` indirection works, opacity modifiers work, and one utility silently does not exist.
See the Decisions entry below.

## Last session

**Session 8 — 2026-08-02. Phase 1 finished, Phase 2 half-built, and the project's verification
regime was deliberately scaled DOWN. That last one is the most important thing in this entry.**

**🔴 THE HEADLINE: THIS IS A PORTFOLIO ARTIFACT, NOT A PRODUCTION SYSTEM.** Karthik's call, late in
the session, and it supersedes every phase gate and ARCHITECTURE §4. The rigor built over sessions
1-8 was calibrated for production — it is why one `make test` cost 108,000 tokens and why the daily
cap kept driving the schedule rather than the work. **Verification drops to sanity level (~15k a
phase, not ~150k), agents default to `fast`, and the build targets a thin end-to-end slice.** Full
entry under Decisions. The golden suites stay as a portfolio asset; they simply stop being a gate.

**Phase 1 is DONE.** All seven stories. 1.4 closed by falsifying the single-call assertion against
a deliberately wrong graph (2 `outcome=ok` records, failing as it must) and re-running its 8 live
tests. 1.3 ticked on a conscious acceptance of three flapping cases. 1.7 closed with its **scope
reduced**, which was the session's best catch: the spec's delete list would have destroyed story
0.7's two-OS-process proof, which 1.4's tests do not replace. **Only Karthik's own eyeball on a
real resume remains, and it does not block the build.**

**Phase 2 is half-built, and four of its stories cost ZERO tokens.** PHASE-2-SPEC, both agent
contracts written before either prompt, and both blind golden suites — 12 fixtures, 87 offline
assertion tests, both deliberately RED on `ModuleNotFoundError` only, proven by running rather than
inferred. **The Planner suite's vacuity handling is the best this project has produced**: it has a
test demonstrating the trap exists next to the test that catches it, so a future simplification
fails with an explanation.

**Two prompt ceilings were computed BEFORE either prompt existed**, which is the most actionable
thing these stories produced: Case Architect ~15,557 chars, Planner ~12,197 chars. A single request
over 8,000 TPM can never succeed at any pacing.

**The golden suite also ran all eight cases on `deep` with zero 429s for the first time** — 37
passed, 1 failed. The feared regression from the case-01 fix did NOT happen (`assessed_level` fired
9 of 9). But case 05 has a third, unrelated flap, so three of eight flap rather than two. That
finding is what led to the acceptance decision, and then to the calibration decision.

**Session 8 (earlier) — stories 1.4 and 1.7 closed. Phase 1 one story from its gate, and the
golden suite measured honestly for the first time.**

**1.4's two missing measurements were the cheap part and both landed.** The single-call assertion —
the phase's most important, and until today green but never seen to fail — was driven against a
deliberately wrong graph and **logged 2 `outcome=ok` records, failing as it must.** The `at pause:
1` line is what makes that meaningful: it proves the wrong graph was running normally up to the
interrupt, so the second record is a genuine re-execution rather than a broken probe. Then the 8
live tests were re-run rather than inherited from session 7's agent. One of them 429'd on TPM and
was re-run alone; **classifying before believing it is the only reason that was not recorded as a
defect**, and it is the fifth time on this project that a red run was quota.

**1.7 was delegated, and the agent contradicted its brief and was right — the fourth time.** The
phase spec's delete list assumed 1.4's tests replace story 0.7's. **They do not.**
`test_confirm_level.py` runs its whole file against one module-scoped `TestClient`; `test_api.py`
spawns two real uvicorn processes, and its own docstring already explains why a rebuilt
`TestClient` proves nothing about state surviving a dying interpreter. Deleting to the list would
have removed the evidence retiring this architecture's central risk **and left a fully green suite
behind.** Karthik's call: keep `skeleton.py` and both `/skeleton/*` routes as permanent test
infrastructure. The 5 genuinely redundant tests went; 7 stayed and were re-run green.

**The reusable lesson is written into Decisions: a story that deletes tests must produce a coverage
map first**, old test → the new test asserting the same property or `UNREPLACED`, and must stop
rather than delete anything `UNREPLACED`. A spec's delete list is a hypothesis about the
replacement, written before it existed. This was caught only because the brief named it as a trap
in advance.

**Then the golden suite ran all eight cases on `deep` with zero 429s — the first time that has ever
happened.** 37 passed, 1 failed. Every previous "full" run lost most cases to quota, so this is the
first run that measured the prompt rather than the rate limiter. **Cases 02 and 08 both passed**,
confirming 02 flaps rather than fails consistently.

**Case 05 failed on the level, not the flag, and it was attributed rather than assumed.** An
alternating A/B with the arms deliberately inverted — pre-fix prompt in the working tree, committed
prompt as HEAD — established the thing that actually mattered: **the committed case-01 fix did NOT
suppress the `assessed_level` trigger. It fired 9 times out of 9.** 05 and 06 are unregressed on
the risk DEV-STATE flagged. But the level flap itself came back 2 fail / 5 versus 0 fail / 4,
p ≈ 0.44, which attributes nothing. **Recorded as unattributed rather than blamed on the fix**, and
the fix was not reverted on that evidence.

**The honest headline is that the suite got worse, again: three of eight cases flap, not two, and
they are three different bugs.** That is the second session running where careful measurement made
the picture worse rather than better, which is the suite doing its job.

**Karthik's call on that: accept the three flaps, tick 1.3, and take the model-quality question
into Phase 2**, where the Case Architect gives an independent signal. Written up in Decisions with
its cost — every future prompt change to this agent needs the 6-8 pair A/B rather than a suite run
— and with four named conditions that reopen it. **All seven Phase 1 stories are now ticked.**

**Then the phase gate was attempted and did NOT pass, which is where the session ends honestly.**
`make test` came back 8 failed / 122 passed. **All eight failures are quota and zero are assertion
failures**, but that is not a pass. The structural reason is worth carrying: `pytest tests`
includes `tests/golden/`, so a full run costs ~50,000 `deep` tokens on top of the ~92,000 the
session had already spent, and `deep` finished at 198,515/200,000. **`make test` and any
investigation cannot share a day** — it has to be the first thing run on a fresh budget.

**One of those eight failures is a harness defect that manufactures a false model-quality signal**,
and it is the most dangerous artefact found this session: `test_llm.py:112` reports
`deep scored 0/10, below the 5 floor` when all ten samples were `RateLimitError`. A future session
could switch models on that headline. Recorded, not fixed — verifying the fix needs `deep` budget
that no longer exists today.

**Session 7 — 2026-08-01. The case-01 prompt fix is validated and committed (`27bb749`). The suite
got measurably less trustworthy, and that is the finding worth carrying.**

Session 6 left one uncommitted prompt change and a plan: run case 01 four times on `deep`, then
commit. **The plan was not good enough, and changing it is what made the session worth anything.**
Four passes on a case that flaps ~50/50 is p = 0.06 by chance — the same shape of weak evidence
that produced the `fast` false pass the day before.

**Replaced with an alternating A/B, control loaded byte-exact from `git show HEAD:`.** FIX 6/6,
CONTROL 2 pass / 2 fail, interleaved so serving drift hit both arms equally. **The control could
fail and did.** That is the whole difference from session 6's `fast` measurement, where it could
not. Committed with the full table in the message. Method written up under Decisions, because it
now costs ~60k tokens to validate a prompt change and that needs budgeting.

**Then two results that both made things worse, honestly.** Control run 7 failed on
`['years_pm_experience']`, not `['assessed_level']` — a *second* over-flagging mode on case 01 that
the committed fix does not address. And case 02 failed the full suite on a genuine defect: one
lowercased sentence-initial letter, `Cut` returned as `cut`. Checked against the fixture directly
rather than assumed, because session 6's near-identical finding on case 08 turned out to be a
U+2011 hyphen and a harness bug. This one is real, and the assertion is right to reject it.

**The hypothesis that died is the second most useful result.** Case 02 looked like a *stable
cross-model* weakness, since `fast` fabricated on it the day before — which would have made `fast`
a legitimate testbed, unlike the case-01 flap. Measured: **3/3 clean on `fast`.** So case 02 flaps
too, and `fast` is not a valid testbed for it either. **Two of eight cases are now known-unreliable,
which is a bigger problem than the single case session 6 described. Story 1.3 stays open.**

**Karthik's call, recorded under Decisions:** commit the validated fix even though the suite is red,
because the blocker is an unrelated pre-existing flap plus exhausted quota, and the fix cleared a
higher bar than the rule asks for. Story 1.3 explicitly NOT ticked.

**Then story 1.4 was built and committed (`aa3a756`), and it is one measurement short of done.**
Delegated to a Sonnet agent. `level_candidate` → `confirm_level` on the real graph, two routes,
and the frontend seams 1.6b left: `ConfirmationScreen` is mounted, `submitLevelCorrection` is real.
Independently re-verified: offline 60/75, **vitest 66 → 74**, build clean, oxlint 0, **residue 0 on
all seven tables**, design greps clean. The three structural traps (T1 nothing above `interrupt()`,
T2 count `outcome=ok` only, T3 `analyse_resume` still pure) were checked by reading the code, and
the `_authorize_session` refactor of story 1.2's security path fails closed to 403.

**But the phase's most important assertion has never been seen to fail.** A probe that builds the
WRONG graph — the LLM call above `interrupt()` in the same node — was written and **429'd before it
could run**, because the agent's 8 live tests had just spent `fast`'s daily budget. So 1.4's
single-call box is correct by inspection and unproven, and the 8 live tests are the agent's run
only. **Both stories are committed and neither is ticked**, for the same reason in both cases: the
evidence that would close them costs tokens that no longer exist today.

**Both models ended the session at their cap:** `deep` 199,325/200,000, `fast` 199,086/200,000.
Nothing about the database or the deployment changed. **Cold start measured 42.4s against the 32.3s
on record** — worth re-measuring before a demo.

**Session 6 — 2026-08-01. Story 1.6b complete. Story 1.3 was stopped from being ticked on a suite
that cannot gate, which is the more important half.**

**1.6b landed and the phase's riskiest unknown is retired: Realtime respects RLS**, proven with two
real anonymous identities plus a service-role control that rules out a dead pipeline. Session
creation is hoisted, fixing the orphan-row defect 1.6a left, and the fix was falsified by breaking
it and watching three tests go red. 33 → 66 vitest tests. Full output above.

**Only story 1.4 and the 1.7 cleanup remain in Phase 1.**

**Two judgment calls in 1.6b are worth a human read.** The confirmation screen is built, tested,
and deliberately NOT mounted — nothing produces a real `ResumeAnalysis` until 1.4, and mounting it
against fixture data would show a candidate fabricated results about their own resume. The agent
proposed that against its own brief and was right. And Realtime has a residual startup race
(positive control failed 2 of 8 runs at zero settle) that is unlikely to bite only because the
Resume Analyst takes seconds to answer. Both are recorded rather than resolved.

**The rest of the session was story 1.3, and it did not close.**

Opened to run two golden cases and close story 1.3. Case 07 passed. Case 08 failed on the
suite's most important assertion, and everything after that came out of reading the failure
rather than accepting the label.

**Case 08's "fabricated quote" was character-identical to the fixture across 42 words** — two
hyphens rendered as U+2011 instead of ASCII. The check that exists to catch fabrication was
manufacturing one. Fixed with a content-neutral typography fold, em-dash deliberately excluded so
a banned character cannot be laundered through as verbatim, and re-falsified in both directions.
Offline suite 53 → 60.

**Then the real finding: `temperature=0` does not make these models deterministic, and this file
said it did.** Golden case 01 flaps PASS/FAIL/PASS/FAIL on `deep` against identical input. These
are MoE models; temperature governs sampling, not the batched forward pass. **A flapping case
makes every future prompt change unfalsifiable, which is the one thing the golden suite exists to
prevent**, so story 1.3 cannot be ticked. Karthik's call: fix the prompt boundary rather than mask
the variance with `seed=`.

**The session's best moment was a control that invalidated my own result.** With `deep` out of
daily quota, the prompt fix was measured on `fast` and came back 5/5 clean. Running the control —
`fast` with the fix reverted — also returned 5/5. **`fast` never had the flap, so the green run was
not evidence about the fix at all.** Recorded as unvalidated. Third false pass this project has
caught with an independent control, after 1.1's `A/own = 1` column and 1.3a's vacuity probe.

**A second harness defect, same shape as the first: the suite was recording rate limits as prompt
failures.** `_PACE_SECONDS` was 30 against an 8000 TPM bucket while one case grew to request ~7500
tokens, needing ~56s of refill. In one run, 5 of 6 "failures" were 429s. Raised to 60s.

**Both harness defects manufactured failures rather than hiding them** — the mirror image of this
project's earlier vacuity findings, and just as expensive, because a red suite nobody trusts gets
tuned against and the assertion is what usually gets tuned.

**Both models hit the 200,000 tokens/day ceiling**, so the prompt fix is written, uncommitted, and
unmeasured on `deep`. That is deliberate: CLAUDE.md forbids committing a prompt change before its
golden cases pass. `git status` is dirty by design and § Next session names the file and the
command.

**Nothing about the frontend, deployment, or the database changed this session.**

**Session 5 — 2026-07-31. Stories 1.3a and 1.6a complete, AND THE PROJECT CHANGED LLM PROVIDER.**

The headline is not the stories. **NVIDIA NIM cannot run this product's core pattern**, and finding
that out cost most of the session. `with_structured_output` returns `None` there once the system
prompt passes roughly 1500-2800 characters, on all three of its models. Every agent in this
architecture is a long rule-dense prompt returning a validated schema, so all six were affected, not
just the Resume Analyst.

**Diagnosed by isolating variables rather than by tuning the prompt**, which is what stopped it being
misread as a bad agent: a trivial 2-field schema also failed with the long prompt, while the full
11-field nested schema succeeded with a short one. The schema was innocent. **Karthik's call: move to
Groq.** The clinching evidence came after: `openai/gpt-oss-20b` is the SAME MODEL as NVIDIA's backup
role, and it works on Groq and fails on NVIDIA. Never a model-quality problem; a serving stack.

**Result: the golden suite went 0/8 to every-case-that-could-run passing.** Migration was one
constructor in `llm.py` plus `config.py`, exactly as the portability finding predicted, then a long
tail of scripts and docs.

**Three limits found the hard way, each correcting the previous answer:** 1000 requests/day, then
8000 tokens/minute, and finally the one that actually stops work — **200,000 tokens per day per
model, which is not exposed in any header.** Verified by dumping every header on a live response.

**Story 1.3 is NOT done.** Six of eight cases measured green on `deep`, all passing; the rest blocked
by that daily quota. Two commands next session finish it.

Also this session, before the migration: stories 1.3a and 1.6a, both halves of deliberate splits.

Two stories were **split in two** this session, and one of those splits paid for itself immediately.

**Story 1.3 was split so the golden suite could not be tuned to the prompt.** 1.3a wrote eight
fixtures and the assertion harness blind, delivering a suite that is red on purpose; 1.3b must make
it pass without editing a fixture or an assertion. The hazard was specific: an agent writing both
can nudge a fixture whenever the prompt misses, and the suite stops gating at the exact moment it is
supposed to start.

**That split bought the session's real finding. The spec's single most important assertion was
passing vacuously on all eight cases.** `missing_verbatim_quotes([])` returns `[]`, so an agent that
quoted **nothing** passed the fabricated-quote check that the agent spec calls the most important
assertion in the file. Found with a from-scratch probe, not by re-running the agent's tests, and the
positive control is what makes it meaningful: a fabricated quote **was** correctly rejected. The
check was right; it simply had no floor. **This is story 1.1's `A/own = 1` column in different
clothes** — a denial assertion with no positive control passes when the mechanism under test is dead.
Closed and re-falsified in both directions, because a fix that makes everything fail is not a fix.

**A second defect was mine, not the agent's.** My brief told it to detect retries by matching
`outcome=empty`. `_LoggedStructured` also logs `outcome=invalid` for a `ValidationError`, and both
paths retry. The file would have recorded "retry never fired" while retries were firing, against the
one acceptance box that exists to stop exactly that assumption.

**Story 1.6 was split on dependency, not risk.** 1.6a's shell, anonymous sign-in and upload surface
need nothing from 1.3 or 1.4, so they ran in parallel with 1.3a on a disjoint file set with no LLM
contention. 1.6b keeps the confirmation screen, the live orchestration states and Realtime.

**1.6a came back clean and stayed clean under independent re-verification** — env vars proven inlined
into the bundle, no em-dashes, no bare `duration-standard`, no `lucide`, no `console.*` anywhere so
the JWT is never logged, and the frontend/backend contract checked against `app/main.py` rather than
assumed. Its one defect was found by reading the flow rather than by any test: **a new session row
is created on every upload attempt**, so a rejected scanned PDF plus a retry orphans a row.
Deliberately deferred to 1.6b, where the session lifecycle is actually decided.

```
7af1d72  Story 1.3a: golden fixtures and a deliberately red assertion harness
218e832  Story 1.6a: app shell, silent anonymous sign-in, and the upload surface
857032b  docs: record 1.3a and 1.6a, the vacuity finding, and the deferred session defect
```

**Test counts moved 30 → 53 offline and 25 → 33 vitest. Live count unchanged at 85** — the eight
golden cases are written but cannot run until 1.3b exists.

**Session 4 — 2026-07-31. Stories 1.1, 1.5 and 1.2 complete. Three of Phase 1's seven stories, plus
the Resume Analyst contract written before its prompt.**

Delegated all three to Sonnet agents and re-verified every one independently. **That re-verification
found something real in all three cases**, which is the strongest evidence yet that the orchestrate/
delegate/verify split earns its cost:

- **1.5** — the agent proved the accent hex reached `dist/`, which would be true even if Tailwind's
  `@theme` layer did nothing. Probing what story 1.6 actually depends on, utility generation through
  a `var()` indirection, found `duration-standard` silently generates no class at all.
- **1.1** — cross-session denial re-proven with a from-scratch probe. Turned up that an unauthorised
  UPDATE/DELETE returns **200, not 403**, which would have encoded a false pass in any future test.
- **1.2** — three em-dashes had shipped into candidate-facing error copy, in a function whose own
  docstring says the message is for the candidate. No test caught it. Now `test_user_facing_copy.py`.

**Two agents contradicted their briefs and were right both times.** `strokeWidth 1.5` does not exist
in Phosphor (verified: zero occurrences in the package, icons are filled geometry). And ARCHITECTURE
§1's direct-to-Storage upload does not survive this phase's own scanned-PDF requirement. Both are
logged under Decisions; **CLAUDE.md was corrected for the first**, ARCHITECTURE left alone per the
decisions-supersede-it rule.

**Karthik enabled Supabase anonymous sign-in**, which unblocked 1.1. The probe that confirmed it also
surfaced the fact that reshaped the whole story: **anonymous users carry the `authenticated` role,
not `anon`.**

```
dea296a  Story 1.5: design foundation, plus vitest and the first make test-web run
1804af6  Story 1.1: scoped RLS policies, cross-session denial proven
232e70a  Story 1.2: resume upload, extraction, and the em-dash ban as a test
```

**Test counts moved 52 → 85 live, 21 → 30 offline, and `make test-web` runs for the first time in
the project (25 passed).**

**Not done, and deliberately not started:** story 1.3. It is the heaviest LLM story in the phase and
was left for a fresh session rather than begun at 75% context.

**Session 3 — 2026-07-30. Stories 0.6, 0.7 and 0.8 complete. PHASE 0 IS DONE, deployed, and
proven end to end.**

The interrupt/resume machinery the whole product rests on now works and is proven: a graph that
pauses, a pause that survives the process dying, and the same cycle driven against the deployed
URL from the Netlify origin. 52 tests green live, phase gate 6/6.

**Three numbers that were assumptions this morning and are measurements tonight:** production
checkpoint step ~27ms (not the 298ms local figure), cold start 32.3s, and `VITE_API_URL` proven
inlined by grepping the deployed bundle rather than trusting that it was set.

**The repo was pushed to GitHub for the first time** —
`https://github.com/karthikr0208/PM-interview-panel`, `main` tracking `origin/main`. History was
scanned before pushing: `.env` was never tracked at any commit, and the only credential-shaped
strings in the entire history are fake test fixtures (`pw`, `abcdefgh`). Note `gh` is not
installed on this machine, so **repo visibility was not confirmed.**

**Working mode changed at Karthik's request: implementation is delegated to Sonnet subagents;
this session's role is planner, orchestrator, and verifier.** Now written into CLAUDE.md § How
work is done so it does not need restating each session. Story 0.7 was built that way.

**It paid for itself immediately.** The agent contradicted its own briefing on the Windows
event-loop fix and was right to — the fix I specified does not work, which I then reproduced
myself. Independent re-verification also caught test residue accumulating in the live database
that the agent's own green test run had not surfaced.

```
7b7f471  0.6 two-node graph with interrupt/resume
7bc437b  0.7 interrupt/resume across two HTTP requests
f17706f  docs: correct stale commit hashes
362c395  pin Python 3.12.10 for the Render build
ff398ea  0.8 part 1: backend live on Render, phase gate met
ed1d582  frontend: backend connectivity check
800f28c  0.8 cold-start latency measured at 32.3s
```

**Deployment settings worth not rediscovering.** Render: root dir `backend`, build
`pip install -r requirements.txt`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`,
region Singapore, `PYTHON_VERSION=3.12.10` plus a committed `backend/.python-version`. Netlify:
base dir `frontend`, build `npm run build`, publish `frontend/dist`, `NODE_VERSION=22`. Both
redeploy automatically on push to `main`, and each only rebuilds when its own directory changes.

### Session 2 — 2026-07-30. Stories 0.1, 0.2, 0.4, 0.5 complete

Phase 0 went from nothing on
disk to a running backend, a Vite frontend, ten tables live in Supabase, a working Postgres
checkpointer, and 40 tests. Seven commits, all local — **no git remote is configured and nothing
has been pushed.**

Orchestrated: scaffolds and test files were built by delegated agents, and **every claim was
re-verified independently before being recorded here.** That mattered — it caught a false pass
in my own verification, a regression one agent introduced into another's tests, and two security
holes.

```
a52fc9c  0.1 repo scaffold, backend, frontend, secret hook
89d21fc  docs: close handoff gaps found auditing 0.1
79ef3cf  docs: per-story and per-phase update checklist
6ba182b  docs: close the session workflow loop, fix stale model in header
878c961  0.2 structured-output gate resolved, retry mandatory
f839f35  0.4 schema migration, RLS, realtime, resumes bucket
b65e097  0.5 checkpointer, plus RLS on LangGraph's own tables
```

### 0.8 backend deployed to Render — observed output

**`https://pm-interview-panel.onrender.com`** · Singapore · free tier · root dir `backend` ·
start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (no `--reload`, correct on Linux)
· Python pinned to 3.12.10 via `backend/.python-version` plus `PYTHON_VERSION`.

The line that mattered in the deploy log is `Application startup complete` — that is the
`lifespan` opening `AsyncPostgresSaver` against Supabase from inside Render. The session pooler
works from Render, which was the second of the four risks this phase existed to retire.

```
==> Running 'uvicorn app.main:app --host 0.0.0.0 --port $PORT'
INFO:     Started server process [62]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:10000
==> Your service is live
```

**THE PHASE GATE — two curl calls against the deployed URL.**

```
=== CALL 1 — POST /skeleton/start ===
{"session_id":"23caf429-7674-4372-8b1d-a3393352b07e","interrupt":{"question":"..."}}
[status=200  total=1.819343s]

=== CALL 2 — POST /skeleton/resume (a separate HTTP request) ===
{"session_id":"23caf429-7674-4372-8b1d-a3393352b07e","turn_count":1}
[status=200  total=0.213757s]

=== same session again, already finished ===
status=404
```

`turn_count: 1` is the 0.6 idempotency property holding in production, not just in tests.

```
/health                                          200  {"status":"ok"}
OPTIONS /skeleton/start  Origin: evil.example.com 400   <- CORS rejects, per the preflight rule
```

**FRONTEND ON NETLIFY — `https://pmaiinterviewpanel.netlify.app`.** Base dir `frontend`, publish
`frontend/dist`, `NODE_VERSION=22`.

**`VITE_API_URL` proven baked in at build time, not merely set.** Vite only inlines variables that
code actually reads, so the box was vacuous until `HealthCheck.tsx` referenced it. Verified by
grepping the *deployed* bundle:

```
https://pmaiinterviewpanel.netlify.app        200
  bundle /assets/index-k5qsSOLI.js  contains  https://pm-interview-panel.onrender.com
```

The deployed bundle hash differs from the local build's (`index-DjE-cX_-.js`), which independently
confirms Netlify baked in a different value than the dev machine did.

**CORS, before and after the `ALLOWED_ORIGINS` change — and the before half is the useful half.**

```
BEFORE (ALLOWED_ORIGINS=http://localhost:5173)
  Origin: https://pmaiinterviewpanel.netlify.app -> 200, NO access-control-allow-origin
  Origin: http://localhost:5173                  -> 200, header echoed

AFTER  (ALLOWED_ORIGINS=https://pmaiinterviewpanel.netlify.app)
  Origin: https://pmaiinterviewpanel.netlify.app -> 200, header echoed
  Origin: http://localhost:5173                  -> 200, NO header      <- nothing wider
  OPTIONS Origin: http://evil.example.com        -> 400
```

**This is the 2026-07-30 CORS decision confirmed in production: the server returns 200 either
way.** Enforcement is the browser refusing a response whose `access-control-allow-origin` is
absent. A test asserting non-200 on a simple request would have passed against a wide-open server.

**FULL CHAIN, carrying the Netlify origin — browser to Netlify to Render to Supabase:**

```
POST /skeleton/start   Origin: https://pmaiinterviewpanel.netlify.app
  {"session_id":"83a73411-...","interrupt":{"question":"What's one product decision you made..."}}
POST /skeleton/resume  Origin: https://pmaiinterviewpanel.netlify.app   (separate request)
  {"session_id":"83a73411-...","turn_count":1}
```

**COLD START: 32.3 SECONDS.** Probe left the service genuinely untouched for ~18 minutes, then
hit `/health` once cold and once warm:

```
idle since:      13:57:51Z
cold_start    = 32.33s   status=200
warm_followup =  0.13s   status=200
```

Better than Render's own "50 seconds or more" banner, and still a product problem rather than a
curiosity. **The first request a candidate makes would hang for half a minute**, on a tool whose
first interaction is uploading a resume. The warm follow-up at 0.13s confirms it is entirely
spin-up, not the app.

**Mitigation, when it matters and not before:** an external uptime pinger on `/health` every ~10
minutes. Cheap, external to the codebase, and reversible. Do not solve this by paying for Render
or by adding a self-ping inside the app. Decide it in Phase 7, or the day before a demo.

**PRODUCTION CHECKPOINT LATENCY — measured at last, and it is nothing like the local number.**

Measured by difference against `/health`, which does no database work, so the client-side
India→Singapore round trip cancels out. All medians of 10 samples, seconds:

```
/health                        (no DB)                     0.1162
/skeleton/resume on a FINISHED session (1 read, then 404)  0.1167   -> read  ~0.5ms, unmeasurable
/skeleton/resume on a PAUSED  session (read + writes)      0.1434   -> write path ~27ms
```

**One checkpoint read is not distinguishable from noise. A full resume step — one read plus the
node's checkpoint writes — costs about 27ms.** Against ~298ms per checkpoint from the Windows dev
machine, which was dominated by home internet.

**This retires the open question and settles both earlier claims.** My original "~1% of turn
latency" guess was unverified and I was right to refuse it after measuring 298ms locally. In
production it is roughly 27ms against a 7-9s turn, so about 0.3%. The guess was directionally
right for the wrong reasons, and only the deployed measurement could tell the difference.
**It also vindicates the Singapore region decision**: co-location is what makes this ~27ms.

### 0.7 interrupt / resume across two HTTP requests — observed output

`backend/app/main.py` (lifespan-held checkpointer, `/skeleton/start`, `/skeleton/resume`) and
`backend/tests/test_api.py`.

```
tests/test_api.py  6 passed in 48.83s
  test_health_returns_ok
  test_start_returns_session_id_and_interrupt_payload
  test_resume_continues_after_the_process_is_torn_down_and_rebuilt
  test_get_state_next_reflects_pause_then_completion
  test_resume_404s_for_an_unknown_session_id
  test_cors_preflight_rejects_unlisted_origin_and_allows_the_configured_one

full live suite:  52 passed in 476.05s (0:07:56)
offline suite  :  21 passed, 31 deselected in 3.87s
```

`make dev-api` driven by hand against the real endpoint, which is what proved the Windows
event-loop finding below:

```
GET  /health          -> {"status":"ok"}
POST /skeleton/start  -> 200 OK
  {"session_id":"d8e7b0b9-b46d-441e-9c98-f43e0774c152","interrupt":{"question":"..."}}
```

**Test residue fixed.** `test_api.py` was the only test file not cleaning up after itself, and
13 orphan thread_ids / 47 checkpoint rows had accumulated in the live database. It now registers
each server-minted `session_id` and deletes it in teardown. Verified by counting either side of
a full-suite run:

```
select count(distinct thread_id), count(*) from checkpoints
  before full suite : (0, 0)
  after full suite  : (0, 0)      <- 52 tests, several creating sessions
```

### 0.6 interrupt / resume — observed output

`backend/app/graph/skeleton.py` (its own module, not `build.py`, so Phase 1 deletes it whole) and
`backend/tests/test_interrupt.py`.

```
tests/test_interrupt.py  6 passed in 17.96s
  test_graph_compiles_with_the_postgres_checkpointer
  test_ainvoke_runs_to_the_interrupt_and_returns_its_payload
  test_command_resume_makes_interrupt_return_the_passed_value
  test_get_state_next_is_the_paused_node
  test_checkpoint_rows_land_after_each_node
  test_llm_call_fires_exactly_once_across_interrupt_and_resume

full live suite:  46 passed in 319.60s (0:05:19)
offline suite  :  21 passed in 4.20s
```

The `conn` / `checkpointer` / `thread_ids` fixtures moved from `test_checkpointer.py` into
`tests/conftest.py`, which now also owns the Windows event-loop policy swap — conftest imports
before any test module, so the swap is guaranteed to precede psycopg. Moved rather than copied
because story 0.6 is the second caller, per CLAUDE.md § Style.

### 0.5 checkpointer — observed output

```
init_db.py, run twice:
  checkpoint_blobs         rls=True      checkpoint_writes        rls=True
  checkpoint_migrations    rls=True      checkpoints              rls=True

graph ran under RLS    : {'n': 42}
state reloaded from PG : {'n': 42}
checkpoint rows written: 3
  service role  : 3        anon : 0        authenticated : 0

full live suite:  19 passed in 426.55s (0:07:06)
offline suite  :  21 passed in 2.36s
```

**Two security holes found and fixed this session**, both the same shape — a table in `public`
reachable by `anon` because Supabase grants there by default. One in our own migration (fixed by
shipping zero policies), one in LangGraph's checkpoint tables (fixed in `init_db.py`).
**Checkpoints were the worse of the two: they hold the entire interview state.**

### 0.1 acceptance — observed output

`make dev-api` → `GET /health`:

```
HTTP/1.1 200 OK
server: uvicorn
content-type: application/json

{"status":"ok"}
```

`make dev-web` → Vite v8.1.5 ready in 347ms on `http://localhost:5173/`, confirmed serving real
HTML with the HMR client injected, not merely printing "ready".

`config.py` failure modes, each run in a subprocess so `backend/.env` was never edited:

```
two vars missing            exit=1
  ConfigError: Missing required environment variable(s): NVIDIA_MODEL_DEEP, SUPABASE_ANON_KEY.

transaction pooler (6543)   exit=1
  ConfigError: SUPABASE_DB_URL uses port 6543 (the transaction pooler). This breaks LangGraph's
  checkpointer with DuplicatePreparedStatement once connections are reused.

direct connection host      exit=1
  ConfigError: SUPABASE_DB_URL host 'db.someref.supabase.co' is not a Supabase pooler host.
```

`.env.example` and `backend/.env` both cover all 11 vars in `REQUIRED_VARS`.

Pre-commit hook, five cases: fake `nvapi-` blocked · fake `sb_secret_` blocked · real-shaped key
blocked · **live `backend/.env` blocked even when force-added past gitignore** · docs naming the
bare prefixes commit fine.

### 0.2 test suite — observed output

`make test-api` equivalent, live tests included. 5m35s, dominated by the 20 structured calls.

```
tests/test_llm.py::test_completion_returns_text PASSED
tests/test_llm.py::test_streaming_yields_multiple_chunks PASSED
tests/test_llm.py::test_structured_output_raw_pass_rate[fast]
  fast (nemotron-3-nano-30b-a3b) raw structured output: 10/10  median 7.2s  failures=none
PASSED
tests/test_llm.py::test_structured_output_raw_pass_rate[deep]
  deep (nemotron-3-super-120b-a12b) raw structured output: 9/10  median 9.2s
  failures=['#10 returned NoneType']
PASSED
tests/test_llm.py::test_retry_wrapper_converges PASSED
tests/test_llm.py::test_every_call_is_logged_with_a_timestamp PASSED
tests/test_llm.py::test_structured_calls_are_logged_too PASSED

7 passed, 13 deselected in 335.27s (0:05:35)
```

Non-live suite, `-m "not live"` — 21 tests, 0.6s:

```
tests/test_config.py .............   13 passed  (parametrized over all 11 REQUIRED_VARS)
tests/test_llm_retry.py ........      8 passed
```

`test_llm_retry.py` is deterministic and hits no network. It exists because
`test_retry_wrapper_converges` only exercises the retry branch when the first attempt happens to
fail — on `fast` that is almost never, so without these the retry logic was effectively untested.
It covers: `None` then valid · `None` twice raises · success does not retry · the instruction is
appended to both string and message-list inputs · **transport errors are re-raised, not
retried** · both attempts are logged.

### 0.4 schema — observed output

Applied with `python backend/scripts/migrate.py`, then re-run to prove idempotency (`ok` both
times). Migration is `backend/migrations/0001_initial_schema.sql`, checked in.

```
tables + RLS:
   agent_events         rls=True      sessions           rls=True
   answer_evaluations   rls=True      transcript_turns   rls=True
   case_worlds          rls=True      resumes            rls=True
   -> all six present: True   missing=None  extra=None

policies:          0  (deliberate — see Decisions)
realtime members:  ['agent_events', 'answer_evaluations', 'transcript_turns']
storage buckets:   [('resumes', False)]        <- private

as service role : 1 row(s) visible
as anon         : 0 row(s) visible
as authenticated: 0 row(s) visible

  empty evidence_quote         rejected: CheckViolation
  score out of range 1-4       rejected: CheckViolation
  duplicate (session_id,idx)   rejected: UniqueViolation

cascade delete  : 0 transcript rows remain after deleting the session
```

The empty-`evidence_quote` rejection is the PRD's "no score without evidence" guarantee enforced
in the database rather than in prompt text. An agent that stops quoting fails loudly here instead
of producing a confident scorecard with nothing behind it.

### Off-peak latency re-measure — model choice holds

Taken 2026-07-30 ~07:30 IST, against the single ~23:00 window everything previously rested on.

| Model | chat latency | structured output |
|---|---|---|
| `nemotron-3-nano-30b-a3b` | 0.4s | VALID |
| `nemotron-3-super-120b-a12b` | 0.4s | VALID |
| `openai/gpt-oss-20b` (backup) | 1.0s | VALID |
| `openai/gpt-oss-120b` | 45s timeout | — |
| `mistral-medium-3.5-128b` | 19.8s | — |
| `google/gemma-4-31b-it` | 26.4s | — |

`nemotron-3-ultra-550b-a55b` now answers in 1.3s and returns valid structured output; it was
`503 ResourceExhausted` on 2026-07-29. Availability moves. Not switching to it — nothing needs it.

### Session 1 — 2026-07-29

Planning, credentials, and de-risking. No application code yet.

Wrote PRD, ARCHITECTURE, CLAUDE.md, PHASE-0-SPEC. Three research agents ran; findings in
`docs/research/`. Installed 13 design skills plus Supabase's two.

Credentials all verified working, not merely present: Supabase recreated in Singapore
(`tnqfqsocoqythakwybsw`) after the first project turned out to be in Sydney, connection proven
against the session pooler, both API keys authenticating.

**The session's significant finding: GLM 5.2 queues ~230s on the free tier and is out.**
Replaced with `nemotron-3-nano-30b-a3b` (fast) and `nemotron-3-super-120b-a12b` (deep), both
3/3 strict structured output at 2–4s. See § Decisions.

Probe scripts kept in `backend/scripts/`: `check_env.py`, `check_db.py`, `probe_latency.py`,
`probe_models.py`, `probe_candidates.py`, `probe_structured.py`.

## Next session — start here

## 🔴 SESSION 17. NOTHING IS OWED. START AT STORY 4.3.

**Read § Decisions 2026-08-09 first** — eight numbered findings, and #8 is a question waiting on
Karthik that 4.3 should not silently decide for him.

**Run these first (~3 min, free, no LLM):**

```
cd backend && .venv/Scripts/python.exe -m pytest tests -q -m "not live"   # expect 439 passed, 111 deselected
cd frontend && npm test -- --run                                          # expect 140 passed, 15 files
```

### 🟢 Session 16 left NOTHING unvalidated. Do not redo any of this.

- **The `kind` change is validated live.** `10 passed, 32 deselected, 334.61s`. Session 15's one
  owed item is closed and every 2026-08-08 change is now confirmed against a live graph.
- **Story 4.2 is DONE (`e631961`).** `evaluate_answer` exists, scores live, runs on `fast`.
- **The role is MEASURED, not inherited**: `deep` 2/2 vs `fast` 1/2, and `fast` was kept
  deliberately. Do not "upgrade" it to `deep` without reading § Decisions #7 first.
- **The token budget is settled and executable.** `tests/test_evaluator_budget.py`, offline, zero
  tokens. If a prompt edit breaks the fit, that file fails instead of a live candidate seeing a 429.
- **Both of story 4.1's open questions are answered.** Neither was what it looked like.

### 🔴 START HERE: story 4.3, the graph edge and the write

`PHASE-4-SPEC.md` §4.3 has the full box list. The three things that will bite:

1. **`evaluate_answer_node` goes AFTER the answer is recorded, NEVER inside `await_candidate`.**
   That node contains only `interrupt()` and its return. On resume LangGraph re-runs it from the
   top, so a call there fires twice per answer and **the duplicate is invisible in
   `answer_evaluations`** — only `app.llm`'s call log would see it. Assert exactly one call, on the
   log, and **falsify it against a deliberately wrong graph** the way `falsify_single_call.py` does.
2. **Re-run EVERY live test file that builds a graph**, not just the one you edited. Story 3.2 broke
   `test_confirm_level.py` exactly this way and it shipped.
3. **The migration is already decided** (§ Decisions 2026-08-09 #5): `reasoning` gets a nullable
   column on `answer_evaluations`; **`framework_narration` is deliberately NOT persisted** and the
   reason is written down. Do not add a nullable `score` or a sentinel to make `not_assessed`
   storable — its absence IS the representation.

**And fix fixture 1 as part of 4.3.** Karthik's call, taken 2026-08-09: correct
`_check_karthik_live_airbnb`'s ground truth to what the transcript actually evidences. Turn 21/23 is
a thesis sharpened under pushback (`point_of_view`) and turn 25 cites *"the 8.6% we are seeing"*
(`market_accuracy`). Its current expectation also cannot be satisfied by the call as wired, because
it describes the whole interview while `test_golden.py` scores a single 28-token answer — 4.3's
accumulating loop is where a whole-interview expectation belongs.

### 🔴 One question is OPEN and belongs to Karthik, not to 4.3

Does demonstrating a LOW anchor count as evidence, or does `not_assessed` mean "did not engage this
dimension at all"? See § Decisions 2026-08-09 #8 for the concrete instance. **4.3 must not decide
this by accident** — if the loop starts treating hedging as evidence, `not_assessed` quietly stops
firing and PHASE-4-SPEC #1's central rule loses its teeth.

### Budget

Session 16 spent roughly **13 live calls**: ~9 on the owed conduct-loop re-run, 4 on the evaluator
smoke across both roles. Well inside the day. The evaluator golden suite is **9 calls** if run whole
(7 fixtures + the level-anchor test's 2), and `_PACE_SECONDS = 60` means it takes ~9 minutes.

### Deployment

**`e631961` is committed and NOT pushed.** Everything through `d4649b0` is live. 4.2 adds no route
and no graph node, so production behaviour is unchanged by it — but the tree is ahead of Render.

---

## Superseded — session 16's opening handoff, kept for the record

## 🔴 SESSION 16. ONE LIVE RUN IS OWED, THEN PHASE 4.

**Read § Decisions 2026-08-08 first.** Eight numbered findings, every number in them cost real
budget, and four of them change how you should read a test result.

**Run these first (~45s, free, no LLM):**

```
cd backend && .venv/Scripts/python.exe -m pytest tests -q -m "not live"   # expect 394 passed, 103 deselected
cd frontend && npm test -- --run                                          # expect 140 passed, 15 files
```

### 🔴 SPEND THE FIRST FRESH TOKENS HERE, and it is one item, not a ladder

```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_conduct_loop.py tests/test_transcript.py -q -m "live"
```

**This is the ONLY thing from 2026-08-08 that is unvalidated.** The `kind` change touches
`await_candidate`'s return — a node — so CLAUDE.md's `build.py` trap applies and the re-run is
owed. It died on the daily cap last session at 197,615/200,000, **classified as quota, not
defect.** ~9 calls at the new probe count of 4.

**What you are looking for:** the loop still completes and exits at 4, and nothing regressed on the
clarify path. If it greens, everything from 2026-08-08 is validated and Phase 4 is unblocked.

### 🟢 Do not redo any of this — all validated 2026-08-08

- **The probe-7 shape fault is NOT a defect.** Paced live loop went 4 passed / 346s, no
  `llm_schema_failure`. `_append_retry_instruction` is CLOSED, not deferred.
- **`gpm_portfolio_world` is 4/4** after the scope rule. **`fast` is deterministic** — a single
  golden run on `fast` is meaningful signal, which is NOT true on `deep`.
- **Probes are 4, not 8**, and every test reads `_PROBES_THIS_PHASE` rather than repeating it.
- **The two interviewer golden reds are PRE-EXISTING**, attributed by `git stash` against the
  committed prompt. `pm_b2b_world`'s is a **test-design flaw** — the figure check punishes
  `81.2 - 34.7 = 46.5` in the one fixture whose whole point is combining two facts. Fix the
  assertion, not the prompt, if you touch it at all.

### 🟢 Phase 4 has STARTED. 4.1 is DONE (`2231a96`) — start at 4.2.

Story 4.1 was **delegated to a Sonnet subagent** and independently re-verified. **Do not redo it.**

```
offline                             429 passed, 111 deselected  (was 394/103)
tests/golden/evaluator, no marker   35 passed, 8 errors  <- this IS the acceptance
paraphrase falsification            rejects "runs" -> "operates", observed failing
```

**The 8 errors are correct and must stay** until 4.2 lands: all are `ImportError: cannot import
name 'evaluate_answer'`, raised before any LLM call. **A green evaluator suite means someone
stubbed the agent.** Verified no stub exists.

Seven fixtures. Six point at their case world (zero inlined `supporting_facts`, checked). The
seventh is **Karthik's real 2026-08-07 interview read from Postgres** and is genuine, spot-checked
against Airbnb / Chesky / Local Law 18 / 82.6 / the session id.

**🔴 TWO OPEN QUESTIONS the subagent surfaced, neither diagnosed:**

1. **The real transcript has FIVE clarify turns, not the four PHASE-4-SPEC claims.** Turns 9 and 11
   ask the same question back to back. Possibly Karthik asking twice, possibly a **duplicate from a
   resume** — `test_transcript.py` carries a replay-conflict guard for exactly that shape. Answer
   turns (9) and probes (8) matched the spec exactly, so only the clarify count is off.
2. **Fixture 1's ground truth is inherited, not measured.** Its `expected_not_assessed` comes from
   the spec's own coverage table, and `point_of_view` arguably has spontaneous evidence at turns
   21/23. The agent deferred to Karthik's recorded read rather than overriding it — correct for a
   subagent, but it means **fixture 1's expectation is a known open question.**

**Carry into 4.1/4.2, from the live interviews:**
- **`not_assessed` is LOAD-BEARING.** Five dimensions, four probes, so exactly one dimension has
  zero evidence **every** interview by design.
- **The 4-turn window must not be reused** for the Evaluator (PHASE-4-SPEC says so; § Decisions
  2026-08-08 #5 now shows what it costs when you do).
- **A leaked real-world fact is undetectable** in a real-company world. See #4.

### Deployment

**EVERYTHING IS PUSHED through `d4649b0`** (2026-08-08, `286bfe9..d4649b0`). Six commits: the
clarification scope fix, the probe cut plus the `kind` change, the CLAUDE.md delegation policy,
two DEV-STATE records, and story 4.1.

**🔴 Karthik's explicit call to ship before the live re-run.** The recommendation had been to hold
`cc61fa2` until the `kind` change greened live; he chose to ship, so **production is running a node
change validated only offline.** That does not make the owed live run optional — it makes it the
first thing to spend fresh budget on, and it is now validating something already serving users
rather than something waiting to.

**THE FREE DEPLOY MARKER IS THE PROBE COUNT.** The backend still has no version endpoint and
`/openapi.json` is byte-identical across 3.5, so it cannot be proven from outside. But an interview
that **exits after FOUR probes is the 2026-08-08 build**; eight means Render is still serving the
old one. That is a stronger marker than anything used before, because it needs no bundle grep and
no route list.

### Budget

**Spent for 2026-08-08: 197,615 / 200,000 `fast`.** Rolling window, ~138 tokens/min. The one owed
live run is ~9 calls / ~25,000 tokens and fits a fresh day easily.

---

## Superseded — session 15's opening handoff, kept for the record

## 🔴 SESSION 15. EVERYTHING FOUND ON 2026-08-07 IS FIXED. NOTHING FIXED IS VALIDATED LIVE.

**Karthik sat a full interview on the deployed stack on 2026-08-07** — one question, four
clarifications, eight probes, clean exit. It produced **eleven findings**, then the rest of the day
went on fixing them at zero token cost. **Read § Decisions 2026-08-07 before planning anything**; it
carries the observed graph state at every step, and every number in it cost real budget.

**The single most important thing to not re-derive:** the loop, invent-and-record, the probe's
response to the candidate's answer, and the ladder all **work** — that is measured, live, with a
human. Six defects were found around them, and all six are fixed:

| Defect | Fix | Live? |
|---|---|---|
| Senior PM got a funnel question in a strategy interview | `select_category`: strategy wins, level picks difficulty | ⬜ |
| GPM wrapped to the APM question | `select_shape` clamps instead of modulo | ⬜ |
| A false premise was accepted and echoed back | Clarification prompt: three ordered steps, contradiction first | ⬜ |
| 2 of 5 rubric dimensions got zero evidence | `select_probe_angle` forces the least-covered angle | ⬜ |
| U+2011 reaching `question_plan` and `transcript_turns` | `normalize_dashes` at the graph boundary | ⬜ |
| Two UI nits (premature hints, Case Architect credit) | Gated on `touched`; copy says "Chose the company" | 🟢 offline |

**Every ⬜ in that last column is the work of session 15.**

**Run these first (~45s, free, no LLM):**

```
cd backend && .venv/Scripts/python.exe -m pytest tests -q -m "not live"   # expect 389 passed, 103 deselected
cd frontend && npm test -- --run                                          # expect 140 passed, 15 files
```

**Everything is committed and pushed.** Eight commits on 2026-08-07, `e2a2d7f..5e34e3f`, tree clean.

**🔴 THE WHOLE DAY'S WORK AFTER THE INTERVIEW IS UNVALIDATED LIVE.** Two agent prompts changed and
the probe loop was rewired, on **zero** live confirmation, because the `fast` budget was spent. That
is not a defect, it is the state — but **do not read 389 green as "it works."** Offline cannot see
any of it.

### 🔴 SPEND THE FIRST FRESH TOKENS IN THIS ORDER. It is a cheap-to-expensive ladder.

**1. `gpm_portfolio_world`, the ONE golden case that matters (~2 calls).**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/golden/interviewer -q -m "live" -k gpm_portfolio
```

This is the adversarial leading-question fixture. It **has never been run**, and it is the test for
the regression found live on 2026-08-07. If the three-step prompt works, this passes. **Cheapest
possible validation of the most important fix.**

**2. The paced live conduct loop (~16 calls, now ~8 minutes).**

```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_conduct_loop.py -q -m "live"
```

`_paced()` puts ~21s between calls. **This is also the batching hypothesis's experiment:** if it
goes green, neither of 2026-08-07's two live failures was a product defect. **Grep for
`llm_schema_failure` if anything reds** — `cbd5ce2` now logs Groq's full `failed_generation`, so the
probe-7 shape fault names itself instead of needing another day to diagnose.

**3. Karthik re-sits gate #4 (~47,000 tokens).** It now tests **three** things at once: does the
strategy question read right, does the false-premise fix hold against a leading question he asks
himself, and **do steered probes still feel like an interviewer following his argument** rather than
a rubric checklist. That last one is the accepted risk of his 2026-08-07 decision and only he can
judge it.

**Budget note:** steps 1 and 2 are ~18 calls, well under a fresh day. Step 3 fits after them.

### 🟢 The category fix is DONE. Do not redo it.

`select_category` and `select_shape` were both fixed on 2026-08-07 at zero token cost, to Karthik's
calibration (strategy wins; level picks difficulty within it), **plus a second inversion the fix
uncovered** — `select_shape`'s modulo wrapped GPM back to the APM question. Three tests added and
falsified. **The unfixed half is that the change is DEPLOYED NOWHERE and has never been seen live:
a re-sat interview is the only thing that closes gate #4.**

### 🟢 Also done 2026-08-07, all free — do not redo

- **The false-premise prompt is fixed** (three ordered steps, contradiction first) but **NOT
  validated live**. Validating it is one golden case, not a suite.
- **`normalize_dashes`** closes the dash hole at the graph boundary, with a Python/TypeScript
  parity pin.
- **`test_conduct_loop.py -m live` is paced** at ~21s between calls.
- **Both UI nits** are fixed: input hints gated on `touched`, and the Case Architect now says
  "Chose the company" rather than claiming generation it does not do.
- **[PHASE-4-SPEC.md](specs/PHASE-4-SPEC.md) is written**, from the live interview rather than the
  plan. **Read its § "What the live interview already decided" before planning Phase 4** — all
  three items are measured and all three would otherwise be found halfway through the build.

### 🟢 DECIDED AND BUILT 2026-08-07: the probe is STEERED. Karthik's call: hard, not soft.

**The defect:** `dimension_coverage` had been tracked since story 3.5.4 and **read by nothing.**
`resolve_primary_dimension` inferred coverage **positionally**, from how many probes had been asked,
never from the counter. Nothing steered, and a real interview ended with 2 of 5 rubric dimensions at
zero.

**The fix:** `select_probe_angle(probe_ladder, dimension_coverage)` picks the **least-covered**
ladder entry, ties breaking on ladder order (same determinism rule as `select_case_world` and
`select_shape_for_world`). `ask_probe` chooses it **before** the call and passes it as
`required_angle`; the full ladder is then left **out** of the prompt, which is unambiguous and
shrinks the largest input this agent sends. **The dimension is known before the call**, so coverage
no longer depends on what the model echoed.

Simulated against the real Airbnb ladder and the same eight probes:

```
before (measured, live)   bmf 4 · dq 4 · sc 1 · market_accuracy 0 · point_of_view 0
after  (steered)          bmf 2 · market_accuracy 2 · dq 2 · sc 1 · point_of_view 1
```

**Zero dimensions uncovered, and the spread is at most 1.** Both are asserted.

**🔴 A disobedient model cannot re-skew coverage.** The dimension comes from the angle Python
required, never from `result.angle_used`; a mismatch is **logged** (`app.graph`, not `app.llm`,
so it cannot perturb a call count) rather than raised, because a disobeyed angle is a worse probe,
not a broken interview. The offline node test was rewritten to make the model return the WRONG
angle deliberately, which makes it a stronger test than the one it replaces.

**🔴 THE KNOWN COST, so it is not rediscovered as a surprise:** forcing an angle risks probes that
read as a rubric checklist rather than an interviewer following the argument. Against that, the ONE
probe that used a ladder angle on 2026-08-07 was the best of the interview. **That is a hypothesis
and the live re-sit is what tests it.** `not_assessed` is still required in Phase 4 regardless —
coverage can never be guaranteed.

### 🟡 Still open, and all of it is free

- **`airbnb.json` says "In 2024, Airbnb relaunched" in three fields** (`company.one_line`,
  `market.description`, `situation.prompt`). Services and Experiences was the **May 2025** Summer
  Release. Not a stale date, a wrong one, and the whole `situation` rests on it. **Karthik's call** —
  he accepted stale dates on these sheets, which is a different thing.
- **`_append_retry_instruction` makes the prompt LONGER on retry**, which is the wrong direction on
  a call whose reasoning budget is the binding constraint. The retry has now failed immediately
  after the attempt at probe 3 (session 13) and probe 7 (session 14). **Only worth acting on if the
  paced run still reds** — if the batching hypothesis holds, there is nothing here to fix.
- **Phase 4 itself.** [PHASE-4-SPEC.md](specs/PHASE-4-SPEC.md) is written and starts at 4.1, which
  is fixtures and assertions and costs **zero tokens**. It is the right thing to do while waiting on
  budget.

### Deployment

**Pushed through `5e34e3f`.** Render and Netlify build from `origin/main`, so both should be current.
**The backend has no version endpoint** and `/openapi.json` is byte-identical across all of 3.5, so
this is not proven from outside — the free in-product check is in the superseded session-14 handoff
below, and the 30-second version is: a **strategy** question about a real company means the newest
build is live, since `select_category` changed on 2026-08-07.

### Budget

**~110,000 of 200,000 `fast` consumed on 2026-08-07 before the interview**, plus the interview
itself. **Assume the day is spent.** The measured rate is **~2,700 tokens per probe request**.
The three live items at the top of this handoff are ~18 calls plus one interview, which fits a
fresh day comfortably.

---

## Superseded — session 14's opening handoff, kept for the record

## 🔴 SESSION 14 (opening). THE LOOP WORKS. THE OPEN ITEM IS PROBE 7, AND IT IS A SHAPE FAULT, NOT A SIZE ONE.

**Run these three first (~45s, free, no LLM):**

```
cd backend && .venv/Scripts/python.exe -m pytest tests -q -m "not live"   # expect 374 passed, 103 deselected
cd frontend && npm test -- --run                                          # expect 139 passed, 15 files
curl -s https://pmaiinterviewpanel.netlify.app/ | grep -oE '/assets/index-[A-Za-z0-9_-]+\.js'
   # then curl that bundle and grep "could not load the brief" -- CompanyBrief is NEW since
   # session 11, so that string is a true deploy marker. The BACKEND has no version endpoint;
   # `/openapi.json` is byte-identical across 3.5 because no API file changed. Do not read a
   # matching route list as "the backend is current" -- it cannot distinguish.
```

**🟢 EVERYTHING IS DEPLOYED as of 2026-08-07.** Twelve commits pushed, `e2a2d7f..cbd5ce2`. Netlify
confirmed current by bundle grep. **Render was pushed but could not be proven from outside** — see
the marker note above. The in-product proof is free and takes 30 seconds: **if the interview asks
ONE question about a REAL company (Anthropic, Figma, Reddit, Cursor...), the new backend is live.
Three questions about an invented company means it is stale.**

### 🔴 The one open defect: `generate_probe` fails at probe 7, intermittently

**Read § Decisions 2026-08-07 before touching it.** Two things there will otherwise be re-derived
at the cost of a live run each:

1. **It is NOT truncation.** The body carries the generic `"Failed to validate JSON"`, not
   `"max completion tokens reached"`. **Raising `max_tokens` a fourth time does nothing.** That is
   the obvious move and it is wrong.
2. **Probe depth alone does not reproduce it.** A synthetic probe-7 transcript through the raw
   runnable went 3/3 clean. It only fails under the real loop, intermittently.

**The next live failure is now self-diagnosing**, which it was not before: `cbd5ce2` logs
`llm_schema_failure ... failed_generation=...` in full. **Grep any live run or Render log for
`llm_schema_failure` FIRST** — that record names the actual wrong shape, and no live budget needs
to be spent guessing at it.

**The live hypothesis worth testing first, and it is free to reason about:** `_append_retry_instruction`
makes the prompt LONGER on retry. On a call whose reasoning budget is the binding constraint, that is
the wrong direction, and it fits the evidence — the retry has now failed immediately after the
attempt at probe 3 (session 13) and probe 7 (session 14). Consider retrying with the *same* prompt,
or with a *higher* `max_tokens`, rather than a longer one.

### 🟡 The live file needs pacing before it can ever be green

`test_conduct_loop.py -m live` fires ~16 calls back to back and **hits the 8,000 TPM per-minute
ceiling** (`Used 5567, Requested 2718`, measured). That is a **test-harness artifact, not a product
defect** — a real interview is paced by a human typing. **Fix it in the test with a sleep between
turns, never with backoff in `llm.py`**, which re-raises transport errors untouched on purpose.

Without that pacing, a red run cannot be read: run 1 and run 2 failed on **different** tests, and
across the two runs every test passed at least once.

### Then the owed live files, in this order

1. `tests/test_conduct_loop.py -m live` — green in ONE run, not across two. ~16 calls.
2. `tests/test_transcript.py -m live` — 6 tests, still never run against the new loop.
3. The golden interviewer smoke — 3 of 5 cases have never run live.

### Budget, measured this session

~42 `fast` calls consumed on 2026-08-07, roughly **110,000 of 200,000**, at ~2,700 tokens per probe
request (from the 429 header's own `Requested 2718`). **Two full live runs of `test_conduct_loop.py`
plus a gate-#4 interview do not fit in one day.** Plan for one live suite run OR one interview, not
both, unless the suite passes first time.

---

## Superseded — session 13's handoff, kept for the record

## 🔴 SESSION 14. PHASE 3.5 IS CODE-COMPLETE AND UNVERIFIED. SPEND THE FIRST FRESH TOKENS ON THE PROBE LOOP.

**Run these three first (~45s, free, no LLM):**

```
cd backend && .venv/Scripts/python.exe -m pytest tests -q -m "not live"   # expect 374 passed, 103 deselected
cd frontend && npm test -- --run                                          # expect 139 passed, 15 files
curl -s https://pm-interview-panel.onrender.com/openapi.json              # read the ROUTE LIST, not /health
```

**🔴 NOTHING FROM SESSIONS 12 OR 13 IS DEPLOYED.** Ten commits sit on local `main`. Production
still serves session 11's build, which asks three generated questions about invented companies.

### 🔴 The first thing, and it needs a FRESH budget, not a leftover one

```
cd backend && .venv/Scripts/python.exe -m pytest tests/test_conduct_loop.py -q -m "live"
```

**Four live tests, roughly 16 `fast` calls.** They are the phase gate's condition #3 and they have
**never completed a run.** `generate_probe`'s `max_tokens` went 1024 -> 2048 at the end of session 13
to fix a `json_validate_failed` at probe 3, and **that fix has never been observed working** — the
re-run died on the daily cap at 198,580/200,000.

**If it fails, grep for `tokens per day` BEFORE believing it.** That exact check is what stopped
session 13 recording a false failure.

If it passes, the remaining owed live files are `tests/test_transcript.py` (6 tests, cut from 8
probes to 2 deliberately — see the budget note in the file) and the golden interviewer smoke.

### Then the phase gate, which is Karthik's

Gate #4 is **an interview he sits and believes, judged on the QUESTION, not the flow.** The flow
already passed on 2026-08-05. A full interview costs ~47,000 `fast` tokens, so **the live suite and
his interview do not both fit in one day** unless the suite passes first time. Budget accordingly:
suite first (~55,000), then his interview.

### 🟢 Two of the three open defects are CLOSED. Do not reopen them.

1. **The fake-round invented figure is ACCEPTED, by Karthik, 2026-08-06.** *"we are not conducting an
   actual interview, its just practice simulation."* No code change and nothing red —
   `contains_fake_round_number` only ever matched round *percentages*, so it never covered
   "5 million" anyway.
2. **The dash-family hole is CLOSED**, all seven characters, in two classes. A **third** copy of the
   constant was found in `resume_analyst/assertions.py` and was live on `level_rationale`. All three
   are pinned equal by a drift guard.
3. **Still open: `test_transcript.py` and `test_conduct_loop.py` live are unverified** against the
   new loop. That is the one remaining item, and it is a budget problem, not a code problem.

### What session 13 actually established, so it is not re-litigated

- The eight real companies are live in the graph; the generative Case Architect is out of the
  runtime path and an interview costs one fewer LLM call.
- The probe **responds to the answer** — 4 of 4 distinct against materially different answers, the
  same method that killed `write_bridge`. It is not a constant function.
- An **improvised fact repeats exactly**, and `improvised_fact` (not `can_answer`) is the only safe
  append signal.
- The transcript window is **first answer + last 4 turns**, from measurement: the full transcript is
  10,274 tokens at probe 10 with verbose answers, over the 8,000 ceiling.

---

## Superseded — session 12's second handoff, kept for the record

## 🟡 SESSION 12, 2026-08-06. PHASE 3.5 IS 3 OF 5 DONE. START AT 3.5.4, AND WIRE THE WORLDS IN FIRST.

**Run these three first (~40s, free, no LLM):**

```
cd backend && .venv/Scripts/python.exe -m pytest tests -q -m "not live"   # expect 326 passed, 101 deselected
cd frontend && npm test -- --run                                          # expect 113 passed, 13 files
curl -s https://pm-interview-panel.onrender.com/openapi.json              # read the ROUTE LIST, not /health
```

**🔴 NOTHING FROM THIS SESSION IS DEPLOYED.** Three commits sit on local `main`
(`76d2937`, `8a17152`, and this session's third). Production still serves session 11's build. That
is fine — 3.5 is mid-phase and the graph is about to change again — but **do not read a passing
`/health` as "production is current"**, which was session 9's four-day failure.

### 🔴 Start with the gap, not the story: THE EIGHT REAL COMPANIES ARE NOT LIVE

`generate_case_world` in `app/graph/build.py` **still calls the generative Case Architect.**
`select_case_world` and all eight fact sheets are **dead code in production**, and
`suits_categories` is therefore always empty at runtime, so 3.5.3's category scoping never engages.

**This is the entire point of the phase and it is one edge away.** My spec never assigned the wiring
to a story, which is my omission, not a subagent's. It is now the first box on 3.5.4.

**Do that before the probe loop.** It is small, it is free, and until it is done a real interview
still runs against an invented company, which makes every judgment about question quality worthless.

### Then 3.5.4, the largest story in the phase

`PHASE-3.5-SPEC.md` § 3.5.4. Live probes, `improvised_facts` as invent-and-record,
`_QUESTIONS_THIS_PHASE` 3 → 1, and the probe edge. **Read § "THREE DECISIONS THIS PHASE REVERSES"
before writing any of it** — two of the three give up things this project has evidence for, and the
invent-and-record design is what keeps the Interviewer from contradicting itself at minute 30.

Three traps specific to it, all named in the spec:

- **Compute the 8,000 TPM fit at probe 10 BEFORE building the loop**, not after. `case_world` alone
  is ~1,200 tokens and the transcript grows every turn. AGENT-INTERVIEWER-SPEC §6 ran exactly this
  computation once and found the naive design did not fit.
- **A probe that reads identically against two different answers is `write_bridge` again** — that
  function was deleted on 2026-08-05 for being a constant function wearing an LLM call. Check it the
  same way: several different answers, compare the probes.
- **`await_candidate` still contains only `interrupt()` and its return.** It has zero `rest_insert`
  calls today; keep it that way.

### 🔴 The open defect, found while verifying 3.5.3 and deliberately not half-fixed

**`no_dash_variants` catches 2 of 6 dash variants, and `stripDashes` has the identical hole.**
U+2011, U+2012, U+2015, U+2212 all pass silently and reach a candidate. The assertion is duplicated
at `tests/golden/planner/assertions.py:141` and `tests/golden/interviewer/assertions.py:176`;
the frontend copy is `frontend/src/lib/copy.ts`.

**The fix is not "add them all to the comma rule."** U+2012/U+2013/U+2014/U+2015 are aside or range
dashes and want the existing treatment; **U+2010, U+2011 and U+2212 are hyphen-like and want ASCII
normalisation** — turning a non-breaking hyphen in "state-of-the-art" into a comma would be worse
than leaving it. Widening shared infra may turn other golden suites red, and **that would be a
finding, not a regression.**

### 🔴 Budget

`fast` and `deep` should both be near-full: `fast` was 197,178/200,000 at 2026-08-05 ~13:00 IST and
the rolling window refills ~198,700 in 24h. **Only one golden smoke was spent this session.** The
daily cap appears in **no header**, so `probe_groq.py` cannot measure it — it reports the 8,000 TPM
per-minute limit only. Classify any 429 before calling it a defect.

**3.5.4 is the first story in the phase with a real per-interview cost:** one `fast` call per probe,
6-10 of them, each carrying a growing transcript. Estimate it before building, not after.

### What Karthik decided this session

- **Stale fact sheets are fine.** He read the review board and accepted July-September 2025 dates.
- **Reddit's `$740.3B` market size stands.** No shape has a market-size slot, so it can only ever
  surface in a clarification answer.
- The fact-sheet review board: https://claude.ai/code/artifact/7427ebfd-da67-4b3a-b0dd-cfd209a0c088

---

## Superseded — session 12's opening handoff, kept for the record

## 🔴 SESSION 12, 2026-08-06. PHASE 3.5 IS SPECCED AND NOTHING IS BUILT. START AT STORY 3.5.1.

**Karthik's examples arrived and they reversed three decisions.** Read
**[PHASE-3.5-SPEC.md](specs/PHASE-3.5-SPEC.md) § "THREE DECISIONS THIS PHASE REVERSES" first** — it
is the only part that is not obvious from the code, and two of the three give up things this project
has evidence for. Then § Decisions 2026-08-06 above for why the diagnosis changed once the examples
landed. **Do not re-derive either.**

**Run these three first (~40s, free, no LLM):**

```
cd backend && .venv/Scripts/python.exe -m pytest tests -q -m "not live"   # expect 221 passed, 95 deselected
cd frontend && npm test -- --run                                          # expect 113 passed, 13 files
curl -s https://pm-interview-panel.onrender.com/openapi.json              # read the ROUTE LIST, not /health
```

### Start at 3.5.1, then 3.5.2. Both cost ZERO tokens, and 3.5.1 unblocks everything.

**3.5.1 — the transcript holds candidate turns.** `transcript_turns` stores zero candidate answers
today, so nothing in this phase is verifiable and Phase 4 cannot attach a score to an answer with no
row. **It needs NO migration** — the DDL already has `role='candidate'` and `kind='answer'`; the
correction is written up under § Decisions 2026-08-06. The write goes in the node **after** the
resume, reading `last_input`, **never in `await_candidate`** (it re-runs from the top and would
double every row).

**3.5.2 — the eight curated worlds and the twelve-shape bank.** This is the story that actually
fixes the reported defect. **Widen the golden assertions before the Planner prompt is touched**, and
the honest corpus for the new checks already exists: **2026-08-05's Q1 and Q2 must FAIL them, Q3
must PASS.** All three are recorded verbatim under § Decisions 2026-08-05.

**The eight worlds are Karthik's to check, not mine.** He knows these companies; a wrong fact about
Reddit or Cursor is one he will spot and I will not. Get them in front of him before 3.5.3.

### 🔴 Budget before starting 3.5.3 or 3.5.4

```
fast (gpt-oss-20b)    should have fully refilled since 2026-08-05  -- MEASURE, do not assume
deep (gpt-oss-120b)   ~35,000 / 200,000   estimated, stale
```

3.5.3 must **re-measure whether the Planner still needs `deep`.** It needs it today because
`QuestionPlan` was the largest generation in the product; one question with filled slots is a
fraction of that, so **`fast` is plausible now and must be tested, not assumed.**

### The defects this phase absorbs, and the one it does not

- ✅ **Absorbed:** the `transcript_turns` gap (3.5.1), the decorative statistic (3.5.2, structurally),
  the recitation-shaped question (3.5.2), the Case Architect's round figures (3.5.2 widens the
  assertion against real data).
- 🔴 **NOT absorbed: the Planner still generates em-dashes.** `stripDashes` stops them reaching a
  candidate through the interview surface but **does not fix generation** — a dash still lands in
  `question_plan` and `transcript_turns`. Anything Phase 4 renders from those rows needs the same
  guard, or generation needs fixing properly.
- 🔴 **NOT absorbed: `years_pm_experience` reports 8.0 where the true value is 10.** Gates nothing
  now the level is candidate-selected, but it is shown to the candidate.

---

## Superseded — session 11's handoff, kept for the record

## 🟢 SESSION 11, 2026-08-05. PHASE 3'S STORIES ARE ALL DONE. THE INTERVIEW IS SITTABLE IN A BROWSER.

**Run these three first (~40s, free, no LLM):**

```
cd backend && .venv/Scripts/python.exe -m pytest tests -q -m "not live"   # expect 221 passed, 95 deselected
cd frontend && npm test -- --run                                          # expect 113 passed, 13 files
curl -s https://pm-interview-panel.onrender.com/openapi.json              # read the ROUTE LIST, not /health
```

### 🟢 EVERYTHING IS DEPLOYED as of 2026-08-05, session 11. Verified, not assumed.

Six commits pushed (`bc44041..db4eaf7`). **Both Render and Netlify serve current `main`**, so for
the first time the deployed site can actually run an interview:

```
GitHub    bc44041..db4eaf7  main -> main
Render    /session/{session_id}/interview/reply   present in the route list
          /health                                 200  {"status":"ok"}
          POST .../interview/reply  (no auth)     422, NOT 404   <- route genuinely wired
Netlify   all five story-3.3 strings present in the SERVED bundle,
          with a pre-3.3 positive control proving the grep works
```

Preflight before the push, all clean: no real `.env` ever committed (only the two `.env.example`),
credential grep hit documentation placeholders only, **no migration in the six commits** (so this
was a code-only deploy), no dependency manifest change, `npm run build` green.

**The migration check is the one worth keeping.** Had 3.2 added a table, pushing would have
deployed code expecting a schema production does not have. It cost one `git diff --name-only`.

### 🔴 THE FALSE TEST THIS SESSION BUILT, AND WHY IT COULD NEVER HAVE WORKED

**Do not verify a Netlify deploy by comparing the bundle hash to a local build.** It cannot work,
and it read as a stale deploy for ten minutes:

`VITE_*` env vars are **inlined into the bundle at build time** (proven back in story 1.6a). Netlify
builds with its own env values, so its output differs from a local build **byte for byte, for
identical source**, and therefore always has a different content hash. Local `index-DKTCjjeJ.js`
against deployed `index-D5Hqg8mO.js` was a difference of 27 bytes in a 435,127-byte file: the env
strings, nothing else.

**Verify deployed frontend code by grepping the SERVED bundle for strings unique to the story, plus
a pre-story positive control** so the grep cannot pass vacuously. That test is env-independent and
is what actually confirmed the deploy.

### 🟢 GATE #4 IS CLOSED. PHASE 3 IS COMPLETE. The interview was sat and the flow worked.

Karthik ran a real interview against the deployed stack on 2026-08-05 and reported **no bugs**.
**Both paths were exercised**, and an adversarial clarifying question produced a **correct refusal
rather than an invented fact** — see § Decisions for why that is the session's most valuable result.

### 🔴 Start here tomorrow: KARTHIK'S EXAMPLES, THEN THE PLANNER PROMPT. In that order.

**Do not touch the prompt before his examples arrive.** He is bringing specific cases of what a good
PM case-interview question looks like. That is a deliberate sequencing decision, not a delay: three
observations is enough to name a problem and **not** enough to specify a fix, and **the Planner runs
on `deep`** (measured 2026-08-04), so a speculative iteration is the expensive kind.

**The work, once the examples land:**

1. **Read § Decisions 2026-08-05, the gate-#4 entry.** The three questions actually served are
   recorded there verbatim, with the two defects and the one strength. **That is the evidence base;
   do not re-derive it.** Headline: a decorative statistic stapled to the front in 2 of 3, and Q1
   answerable by reciting the case back. Q3 is the shape to generalize from.
2. **The file to change is `docs/specs/agents/AGENT-PLANNER-SPEC.md` and the Planner's prompt in
   `backend/app/agents/planner.py`.** 🔴 **NOT the Interviewer.** `ask_question` copies
   `question_plan` byte for byte by design (§ Decisions 2026-08-05), so the Interviewer is faithfully
   serving whatever the Planner wrote. Changing the Interviewer would fix nothing.
3. **Widen the golden assertions BEFORE the prompt**, same order that worked in 3.1 and that
   §"widen the assertion first" already prescribes for the Case Architect's round figures. A
   decorative-statistic check is mechanical and cheap: a question that still parses the same with
   its leading stat clause deleted is a question whose stat did no work.
4. **Then change the prompt and run ONE golden case.** Per the portfolio calibration, not the full
   set, not an A/B. Read the output, move on.

**Budget note for that work:** the Planner needs `deep`, ~6,000 tokens a run. Do not start prompt
iteration on a `deep` budget you have not checked.

### The rest of Phase 3's handoff, now closed

- **Deployed and verified**, both Render and Netlify (see above).
- **Expect a cold start** on the first hit: Render free tier measured 32.3s (story 0.8).

### 🔴 Two things to watch while sitting it, both recorded and neither chased

- **Ask 3-5 ADVERSARIAL clarifying questions** — things `case_world` does not contain. ARCHITECTURE
  §9 lists "the Interviewer invents a fact" as a failure with **no runtime detection**, so this
  manual pass is the only thing that catches it. Two of five golden fixtures cover the refusal
  branch; the other three have never run.
- **The level selector's prominence.** It has existed on `ConfirmationScreen.tsx` since story 1.6b,
  but Karthik asked for it on 2026-08-05 as though it were missing. That is a UI judgment, not a
  missing feature. Look at it in the browser and decide.

### 🔴 Budget at session 11's close — unchanged, because 3.3 spent nothing

```
fast (gpt-oss-20b)    197,178 / 200,000   MEASURED at session 10's close, off a 429 body
deep (gpt-oss-120b)   ~35,000 / 200,000   estimated
```

Rolling window refills at ~138 tokens/min, so `fast` is usable again roughly 24h from about
13:00 IST on 2026-08-05. **A clarification needs `fast`** — if it is still exhausted, the clarify
path will 429 and that is quota, not a defect. Classify before believing it.

### 🔴 THE DEFECT TO SETTLE BEFORE PHASE 4 STARTS, NOT DURING

**`transcript_turns` holds NO candidate answers.** Only the Interviewer's own utterances get a row,
so a completed interview stores 3 questions and 1 clarification and **zero answers**. Phase 4's
`answer_evaluations.turn_idx` references `transcript_turns.idx`, so **Phase 4 cannot attach a score
to an answer that has no row.** This is a schema-shaped problem, not a prompt one. Carried since
session 10 and still the first thing Phase 4 must resolve.

### The other two defects carried forward, deliberately not chased

1. **The Planner still generates em-dashes.** Session 11 stopped them reaching a candidate *through
   the interview surface* (`stripDashes` at the render boundary) but **did not fix generation** — a
   dash still lands in `question_plan` and `transcript_turns`. Anything Phase 4 renders from those
   rows needs the same guard, or the generation side needs fixing properly.
2. **The Case Architect produces round figures** (`arr_usd "$150M"`, `customer_count 500000`).
   `is_round_dollar_amount` covers `arr_usd`/`size_usd` but nothing checks `supporting_facts` free
   text or `customer_count`. **Widen the assertion first, then fix the prompt.**
3. **`years_pm_experience` reports 8.0 where the true value is 10** (Karthik's CV, PM from 2016).
   Gates nothing now the level is candidate-selected, but it is shown to the candidate.

### What 3.3 delivered, with the numbers

```
frontend      13 files, 113 passed        (was 10 files / 84)
tsc --noEmit  clean
vite build    ok, dist/assets/index-DKTCjjeJ.js 435.10 kB
backend       221 passed, 95 deselected   unchanged, no backend file touched
```

**Falsified, not inspected** — two deliberate mutations, both reverted:

```
clarification branch replaces the question   -> 2 failed  (TRAP 2, interview.test.ts)
stripDashes removed from the question render -> 1 failed  (dash test, InterviewSurface.test.tsx)
                                                3 failed | 110 passed
```

New: `lib/copy.ts` (`stripDashes`), `lib/interview.ts` (`useInterview`),
`components/InterviewSurface.tsx`, plus a test file each. Edited: `lib/types.ts`, `lib/api.ts`
(`first_question` was being **dropped on the floor** — the backend had returned it since 3.2),
`lib/levelAssessment.ts`, `App.tsx`, `OrchestrationColumn.tsx` (one appended row, as 2.7 predicted).

**`OrchestrationColumn` was deliberately left where it is** — in `AppShell`'s slot, outside
`renderConversation()`, never remounted. Its docstring explains that this placement is the
structural reason the Realtime startup race stays closed.

### The pattern session 11 repeated, and it paid again

**Both of session 11's real findings came from re-verifying independently rather than reading the
subagent's report.** The report was accurate; the value was in the two mutations run afterward,
which turned "the tests pass" into "the tests would have caught it". The subagent also edited two
pre-existing test files, which is the exact shape of the regression CLAUDE.md warns about — both
edits were checked and were **strengthenings** (full ordered equality including the new row;
`firstQuestion` newly asserted), not weakenings. **Check that every time; it will not always be.**

---

## Superseded — session 10's handoff, kept for the record

## 🟢 SESSION 10, 2026-08-05. PHASE 1 IS COMPLETE. STORIES 3.1 AND 3.2 DONE. THE INTERVIEW RUNS.

**`git status` is clean. Four commits, all pushed to local `main`:**

```
1ba75cd  Close Phase 1 gate #4, and prove a corrected level drives the interview
3056bf8  Delete the bridge LLM call: it was measured to be a constant function
08d8dba  Story 3.2: the conduct loop, with the looping interrupt falsified on both sides
b485cb6  Story 3.1: Interviewer spec and blind golden fixtures, at zero token cost
```

**Run these three first (~30s, free, no LLM):**

```
cd backend && .venv/Scripts/python.exe -m pytest tests -q -m "not live"   # expect 221 passed, 95 deselected
cd frontend && npm test -- --run                                          # expect 84 passed
curl -s https://pm-interview-panel.onrender.com/openapi.json              # expect the /session routes
```

**🔴 The third will be SHORT of what the repo has, and that is expected, not a fault.** Story 3.2
added `POST /session/{id}/interview/reply` and changed `/level/confirm`'s response; **none of it is
pushed to GitHub or deployed.** Production still serves session 9's build. **Do not read a passing
`/health` as "production is current"** — that is precisely the four-day failure of session 9. Run
the `curl` and read the route list.

### 🔴 Start here: story 3.3, the interview UI — and it needs NO LLM budget

`PHASE-3-SPEC.md` § 3.3. Six acceptance boxes. The backend it talks to is built and proven end to
end over real HTTP.

- The question is revealed **whole, never streamed token by token** (design v1: no typewriter).
- Answer and clarify are **visibly distinct actions**, and the API already separates them:
  `POST /session/{id}/interview/reply` with `{"type": "answer"|"clarify", "text": ...}`.
- **The response nests the payload under `next` and flags the end with `done`** — not at the top
  level. Reading the top level is what made the HTTP proof script over-post and 404. `done: true`
  means the interview is over and there is no `next`.
- The orchestration column needs **one row added to `AGENTS` in `OrchestrationColumn.tsx`**; story
  2.7 proved that is all a new agent needs.
- **No persona header, no interviewer name.** Binding since 2026-07-31.
- **No em-dashes in anything rendered from model output.** The Interviewer generates prose at
  runtime, which `test_user_facing_copy.py` cannot see. (The transition lines between questions ARE
  covered statically now — they are source strings, not generated.)

**One question worth putting to Karthik while building 3.3:** the level selector on
`ConfirmationScreen.tsx` has existed since story 1.6b, but he asked for it on 2026-08-05 as though it
were missing. **It may not be prominent enough in the browser.** That is a UI-prominence judgment,
not a missing feature — see § Decisions 2026-08-05.

### 🔴 Budget at session 10's close — `fast` is SPENT, `deep` has room

```
fast (gpt-oss-20b)    197,178 / 200,000   MEASURED, off a 429 body. Effectively exhausted.
deep (gpt-oss-120b)   ~35,000 / 200,000   estimated: 2 full chain runs + a few Planner calls
```

Rolling window refills at ~138 tokens/min, so `fast` is genuinely usable again roughly 24h from
about 13:00 IST on 2026-08-05. **Story 3.3 needs neither**, which is why it is the recommended start.

### 🔴 TWO defects carried out of this session, both recorded and NOT chased

1. **`transcript_turns` holds NO candidate answers** — only the Interviewer's own utterances get a
   row. A completed interview stores 3 questions and 1 clarification and zero answers. **Phase 4's
   `answer_evaluations.turn_idx` references `transcript_turns.idx`, so Phase 4 cannot attach a score
   to an answer that has no row.** **This is the one to settle before Phase 4 starts, not during.**
2. **`years_pm_experience` reports 8.0 where the true value is 10** (Karthik's CV, PM from 2016).
   No longer gates anything now the level is candidate-selected, but it is shown to the candidate
   and feeds `level_rationale`. Reference value recorded for any future re-gate.

*(A third, the repetitive bridge, was resolved the same day — see Decisions. The LLM call was
measured to be a constant function and deleted.)*

### 🔴 The lesson session 10 exists to teach, and it cost twice

**"Deselected is not passed."** It bit two separate times, one commit apart:

- A subagent reported `14 passed, 3 deselected` on `test_conduct_loop.py` and called story 3.2
  verified. **The 3 deselected were the only tests that observe the property the phase exists to
  prove**, and all three died instantly on `KeyError: 'resume_text'`. Worse, the falsification script
  only ever runs the WRONG graph, so the correct-side observation lived entirely in those dead tests
  — **the phase's central proof was half complete and looked finished.**
- Then **I did the same thing.** Story 3.2 extended the graph past `confirm_level`, breaking
  `test_resume_analyst_llm_call_fires_exactly_once_across_the_confirm_cycle` — the test that file's
  own docstring calls THE load-bearing one. I verified the subagent's fix to a *different* stale
  assertion in that same file and never ran the rest of it. **Committed broken in `08d8dba`, found
  and fixed in `1ba75cd`.**

**The rule that follows: when a change touches the GRAPH, re-run every live file that builds a
graph, not just the one you edited.** CLAUDE.md already says this for shared database objects
(story 0.5's row); the graph is the same kind of shared object and the table does not say so.

### What 3.2 delivered, with the numbers

```
offline        221 passed, 95 deselected, 1 warning in 4.41s     (was 199/91)
live loop      3 passed, 20 deselected in 28.78s
golden smoke   apm_consumer_world        PASS on fast, retry_fired=False
               senior_pm_platform_world  PASS on fast, retry_fired=True   (the refusal branch)
falsification  wrong graph 1 -> 3 -> 4 where a correct loop logs 2, exit 0
               plus the CORRECT side observed live: 1 call across a whole interview
http proof     3 questions over 3 separate requests, clarification consumed no slot, done
prompt         clarification 2,728 chars, ceiling ~20,000
```

**`fast` holds `ClarificationAnswer`** — measured, so unlike the Planner this agent needs no `deep`.

**`ask_question` is fully deterministic**, so the conduct loop's only LLM call is the clarification
and its token cost is **flat in the number of questions**.

### What 3.1 delivered

```
docs/specs/agents/AGENT-INTERVIEWER-SPEC.md      the contract, written before the prompt
backend/tests/golden/interviewer/                assertions.py, cases.py, 5 fixtures,
                                                 test_assertions.py (40 offline), test_golden.py

offline suite    199 passed, 91 deselected, 1 warning in 3.91s     (was 159/85)
collection       6 tests collected in 0.02s      <- clean while the agent module is absent
deliberate red   ModuleNotFoundError: No module named 'app.agents.interviewer'
                 1 error in 0.17s                <- dies before any network call, zero tokens
```

**Fixture premises were verified independently, not taken on report.** Fixture 3's eNPS and fixture
5's year-ago churn are genuinely absent from their worlds, and fixture 4's leading question is
genuinely false: `gpm_portfolio_world` states *"Business banking ARR is $28M, the smallest of the
three product lines."*

### 🔴 Start here: story 3.2, and read these three things first

1. **DEV-STATE § Decisions 2026-08-05, all three entries.** One of them changes what 3.2 builds:
   **`ask_question` does not regenerate the planned question.** Python emits it verbatim; the model
   writes only a bridge line. This diverges from ARCHITECTURE §3 deliberately.
2. **AGENT-INTERVIEWER-SPEC §6.** The prompt ceiling is computed and **the naive design does not
   fit** — handing every call the world plus the transcript blows the 8,000 TPM bucket by question 3,
   because this is the only agent whose input grows during a session. The fix is scoping: **neither
   call ever receives the transcript.** Build to that table, do not re-derive it.
3. **`max_tokens=2048` for the clarification call is a PROJECTION, not a measurement.** gpt-oss emits
   reasoning tokens against `max_tokens` before the JSON starts; 1,600 and 2,600 both failed on the
   Resume Analyst's far larger schema. If it returns `json_validate_failed`, **raise it — that error
   reads like a prompt problem and is not one.**

### What story 3.2 owes that 3.1 could not cover

- **The bridge has no dash guard.** 3.1's harness exercises `answer_clarification` only, so `bridge`
  is an unguarded candidate-facing generative surface. It needs its own case shape. See Decisions.
- **The looping interrupt must be FALSIFIED, not inspected.** `backend/scripts/falsify_single_call.py`
  exists and covers one interrupt; a looping one is not the same proof and needs its sibling.
  **Assert on `app/llm.py`'s call log, never on state** — a loop that re-runs `ask_question` looks
  correct from state, because the transcript still reads fine.
- **Whether `fast` holds `ClarificationAnswer` is unmeasured.** Three fields is far smaller than
  `QuestionPlan`, so `fast` is likely — but the Planner needing `deep` was also a surprise. Measure;
  do not assume either way.

### 🟢 PHASE 1 GATE #4 IS CLOSED — 2026-08-05. TWO THINGS REMAIN FOR KARTHIK.

**Gate #4 was answered by rejecting its premise, which was the right answer.** Seniority is
company-relative, so no rubric can be "right" about it; the candidate picks the level and the
agent's guess is a default. The selector already existed (story 1.6b); what was missing was any
assertion that a **correction reaches the Case Architect and Planner**, now added and falsified. See
§ Decisions 2026-08-05. **Phase 1 is COMPLETE.**

1. **Phase 2 gate #4** — read a generated `case_world` and say whether the company could exist.
2. **A `deep` budget decision.** Planner ~6,000/run, Resume Analyst ~5,000, so ~35 candidate
   journeys a day, shared with all development.

### 🔴 TWO OPEN DEFECTS from session 9, still deliberately not chased

Neither breaks a demo. Both violate rules their own golden suites already encode.

1. **The Planner ships em-dashes into candidate-facing questions.** Prompting has now failed twice on
   a mechanical rule. **The fix is deterministic, not another prompt line** — strip dash variants from
   generated candidate-facing text. Free to build, and it would protect the Interviewer's prose
   *before* 3.2 writes it. **Story 3.1's §2a decision is the same instinct applied structurally.**
2. **The Case Architect produces round figures** (`arr_usd "$150M"`, `customer_count 500000`).
   `is_round_dollar_amount` covers `arr_usd`/`size_usd` but nothing checks `supporting_facts` free
   text or `customer_count`. Widen the assertion first, then fix the prompt.

### The pattern session 10 repeated, deliberately

**Session 9's lesson was "front-load the zero-quota work."** Story 3.1 was chosen precisely because
it needs no budget, and it produced two real findings before a single token was spent: a figure check
that was blind to the figures models actually invent, and an assertion that could only ever no-op.
**Both were found by re-verifying independently rather than reading the report** — the same thing
that has paid every time it has been done in this project.

---

## Superseded — session 9's handoff, kept for the record

## 🟢 SESSION 9 ENDED CLEAN, 2026-08-04. PHASE 2 IS COMPLETE. PRODUCTION WORKS.

**`git status` is clean and everything is pushed.** Both Render and Netlify serve current `main`,
and **Karthik confirmed a real CV uploading and levelling in a browser** — the first time the
deployed product has worked end to end.

**Run these three first (~30s, free, no LLM):**

```
cd backend && .venv/Scripts/python.exe -m pytest tests -q -m "not live"   # expect 159 passed, 82 deselected
cd frontend && npm test -- --run                                          # expect 84 passed
curl -s https://pm-interview-panel.onrender.com/openapi.json              # expect FOUR /session routes
```

**🔴 The third is new and it is not optional.** Production was broken for four days and **no test
suite could see it** — a failed Render deploy keeps serving the last healthy build, so `/health`
stayed green the whole time. It costs nothing. If `/session/{session_id}/level` is missing, stop and
read § Decisions 2026-08-04 before anything else.

**Note the 159 / 84.** They were 147 / 74 at the start of session 9. **The "60 offline" figure
further down this file is stale** — it predates Phase 2's suites.

### Start here: story 3.1, and it costs ZERO tokens

**Phase 3 is specced and thin** — read [PHASE-3-SPEC.md](specs/PHASE-3-SPEC.md) first. Three
stories, the Interviewer asks 2-3 questions, answers are NOT scored (that is Phase 4).

**Story 3.1 = `AGENT-INTERVIEWER-SPEC.md` + its golden fixtures, written BLIND, before any prompt.**
No LLM budget at all. Phase 2 proved that half is where the leverage is: four defects came out of
it. Worth doing on a fresh morning bucket precisely *because* it does not need one.

### 🔴 TWO OPEN DEFECTS, seen in real output, deliberately NOT chased

Neither breaks a demo, so the portfolio calibration says record and move on. But **both violate
rules their own golden suites already encode**, which is the clearest evidence yet that one smoked
case per agent is thinner than it looks.

1. **The Planner shipped em-dashes into candidate-facing questions** (`"...startup—how would you"`).
   Its prompt bans them and `no_dash_variants` would catch them. **Prompting has now failed twice to
   enforce a mechanical rule.** The recommended fix is deterministic, not another prompt line:
   strip dash variants from generated candidate-facing text, per CLAUDE.md § Style ("prefer
   deterministic Python where the decision can be made from state"). Free to build, free to test,
   and it would protect Phase 3's prose-heavy Interviewer *before* it is written.
2. **The Case Architect produced round figures** — `arr_usd "$150M"`, `"$50M AI innovation budget"`,
   `customer_count 500000`. `is_round_dollar_amount` covers `arr_usd`/`size_usd` but **nothing checks
   `supporting_facts` free text or `customer_count`**. Widen the assertion first, then fix the prompt.

### 🔴 THREE THINGS ONLY KARTHIK CAN DO

1. **Phase 1 gate #4 — the flow works, but whether the LEVEL is right is STILL UNRECORDED.** His CV
   produced `Senior PM`, `years_pm_experience 8.0`. Per the rubric that is defensible: GPM requires
   managing PMs, and the CV shows portfolio scope with no direct reports. **If he thinks a 15-year AI
   Product Leader should read GPM, that is a rubric change, not a bug.**
2. **Phase 2 gate #4** — read a generated `case_world` and say whether the company could exist.
3. **A `deep` budget decision.** The Planner needs `deep` at ~6,000 per run and the Resume Analyst
   ~5,000, so ~35 candidate journeys a day, shared with all development.

**Do not hold Phase 3 for any of them.**

### Phase 3 — `PHASE-3-SPEC.md` is WRITTEN, 2026-08-04. Start at story 3.1.

Thin, as the calibration demands: **three stories, the Interviewer asks 2-3 of the planned
questions, and answers are NOT scored** (that is Phase 4). Read
[PHASE-3-SPEC.md](specs/PHASE-3-SPEC.md) before anything else in that phase.

**Story 3.1 is zero-quota** — the agent spec plus blind golden fixtures. Phase 2 proved that half is
where the leverage is: four defects came out of it. **Do 3.1 on a day with no budget.**

**Two things in that spec that are easy to miss and are called out there:**

- **`interrupt()` #2 sits inside a LOOP, and that is genuinely new.** Phase 0 proved a single
  interrupt resumes across HTTP requests; it did not prove a looping one does. A loop that re-runs
  `ask_question` on resume **looks correct from state** — the transcript still reads fine. Only
  `app/llm.py`'s call log shows the duplicate. Assert there, never on state. `await_candidate`
  contains ONLY `interrupt()` and its return.
- **The em-dash ban reaches a surface no guard covers.** `test_user_facing_copy.py` checks source
  strings and (since 2026-08-04) every `_*_SUMMARY`. **The Interviewer generates candidate-facing
  prose at runtime.** The ban has to be in the prompt AND asserted in the golden cases.

Also worth carrying: the Planner needed `deep` while every other agent runs on `fast`. **Do not
assume `fast` works for the Interviewer, and do not assume it fails.** ARCHITECTURE §4 says `fast`,
and it is the one agent where that table and the calibration agree, since it runs while a candidate
watches a cursor.

### One thing owed on 2.3, small and free of LLM cost

**Falsify `case_world`'s write-once rule.** Immutability across `plan_interview` is asserted and
passes; nothing has watched a *second* write be rejected. Copy story 0.6's idempotency
falsification — build the wrong graph, confirm it is caught. The spec is explicit that an
immutability rule nobody has seen reject a write is a comment, not an assertion.

### 🔴 Budget at session 9's end — `deep` is HEAVILY SPENT, and tomorrow starts fresh

```
deep (gpt-oss-120b)   ~130,000-150,000 / 200,000 estimated, NOT measured at close
fast (gpt-oss-20b)    ~30,000 / 200,000
```

The `deep` spend: 6 Planner golden runs, 1 live chain run, 4 full-chain runs on Karthik's real CV
while sizing the TPM budget, and 4 Resume Analyst golden cases re-gating the prompt diet. **Estimated,
not measured — no probe was run at close.** Rolling window refilling ~138/min, so a genuinely full
bucket is ~24h from about 21:30 IST on 2026-08-04.

**Story 3.1 needs none of it**, which is why it is the recommended start.

**Session 9's pattern, worth repeating:** the expensive half was iterating `deep` on ONE case. The
cheap half — story 2.7, the em-dash guard hole, the Realtime re-check, the write-once falsification,
the whole deployment diagnosis, all the docs — **cost nothing at all, and found more.** Front-load
the zero-quota work.

### 🔴 The lesson session 9 exists to teach

**Seven defects, and not one was findable by `make test`.** Four came from smoking two golden cases;
three came from a real CV and a real browser. They lived in: a schema failure wearing a transport
exception's clothes, the gap between the repo and production, an input no fixture resembles, and the
**seam** between three individually-tested components — where an existing test was actively
certifying the bug.

**What follows for the remaining phases:** the free checks that pay are the ones pointed at
*integration and reality*, not at more unit coverage. A `curl` of `/openapi.json`, one real input
through the whole chain, and one App-level test per seam. All three are cheap; all three caught
something today.

### If you are tempted to make the Planner green, read this first

**The genericness flap is ACCEPTED and is not a bug to fix.** Five `deep` runs went 5 -> 3 -> 1 -> 0
-> 1 generic questions as two real defects were fixed. What remains is generative variance at 6 of 7
questions compliant. **Reopens only if it exceeds 2 of 7, or a Phase 3 interview visibly reads as
generic.** Chasing it further is the exact failure the portfolio calibration exists to prevent.

---

## Superseded — session 8's handoff, kept for the record

## 🔴🔴 SESSION 8 ENDED MID-STORY, WITH UNCOMMITTED WORK IN THE TREE — ✅ RESOLVED IN SESSION 9

**`git status` is NOT clean, and that is expected.** A Sonnet agent built stories 2.3 and 2.6; its
files are in the tree, uncommitted. **Its own report never arrived — it stopped waiting on its own
smoke test — so its work was checked by me directly instead:**

```
?? backend/app/agents/case_architect.py     WRITTEN, structurally sound, output UNVERIFIED
?? backend/app/agents/planner.py            WRITTEN, structurally sound, output UNVERIFIED
 M backend/app/graph/build.py               MODIFIED, imports and compiles
```

**What I verified myself, all free:**

```
offline suite     147 passed, 82 deselected     <- unchanged, no regressions
graph imports     ok, both nodes wired
case_architect    2,831 chars  (ceiling 15,557)   comfortable
planner           3,045 chars  (ceiling 12,197)   comfortable
```

**So this is NOT an abandoned half-draft — do not throw it away.** Both prompts came in far under
their ceilings, which was the risk flagged before the build. **The only thing unverified is whether
the agents produce output that passes their golden cases**, and that could not be tested:

```
smoke on `fast`   1 failed in 92.87s
  429 tokens per day (TPD): Limit 200000, Used 198811, Requested 5664
  ZERO assertion failures. Quota, not a defect.
```

**Last good commit is `7066a0c`.** Everything through story 2.5 plus all docs is committed.

**FIRST THING NEXT SESSION — the two smokes, on a fresh budget.** They are the only outstanding
work on 2.3/2.6. If they pass, commit the three files and move to 2.7.

**Smoke them one case each, on `fast`, and do NOT run the full suites:**

```
cd backend && $env:GOLDEN_ROLE="fast"
.venv/Scripts/python.exe -m pytest "tests/golden/case_architect/test_golden.py::test_golden_case[apm_consumer]" -q -s
.venv/Scripts/python.exe -m pytest "tests/golden/planner/test_golden.py::test_golden_case[apm_consumer_world]" -q -s
```

**Then 2.7** (both agents in the orchestration column, reusing 1.6b's Realtime), and **then a thin
Phase 3**: Interviewer plus the conduct loop, asking 2-3 of the planned questions rather than all
of them. `PHASE-3-SPEC.md` needs writing first, and writing it costs nothing.

### The remaining plan, deliberately thin — do not expand it

**Target: the whole pipeline demoable end to end.** Simplest working version of every agent, then
deepen only what looks weakest. Each phase should cost ~15,000 tokens of verification, not 150,000.

```
2.3 / 2.6   Case Architect + Planner agents          IN FLIGHT, uncommitted
2.7         both agents in the orchestration column   no LLM
3           Interviewer + conduct loop, asking 2-3 planned questions, not 5-7.
            interrupt #2 (`await_candidate`) is the only structural risk here and
            Phase 0 already proved the pattern
4           Evaluator + a scorecard over the 5 PRD dimensions
5           Coach, one report over the transcript
6 / 7       ONLY what a demo needs. Cold-start pinger, error states, a walkthrough.
            Everything else in ARCHITECTURE §6-7 is out of scope unless it shows
```

**Write each `PHASE-<N>-SPEC.md` before starting it — that is free and it is what keeps scope
honest. But write them THIN.** Phase 1's spec has seven stories and took four sessions; Phases 3-5
should be two or three stories each.

**Per phase, the whole gate is:** offline suite green · one golden case smoke on `fast` · the chain
runs end to end · it looks right to Karthik.

**The temptation to resist:** every phase will surface something that *could* be measured properly.
Two of eight cases flapping, a startup race, an assertion that might be vacuous. **Record it and
move on.** The only ones worth stopping for are those that would make a demo visibly break.

**🔴 BUDGET AT SESSION END: BOTH MODELS ARE EXHAUSTED. Measured, not estimated.**

```
deep (gpt-oss-120b)   198,515 / 200,000
fast (gpt-oss-20b)    198,811 / 200,000    <- spent by the 2.3/2.6 build
```

Rolling window, ~138 tokens/min each, so **a genuinely full bucket on either is ~24 hours away.**
Nothing LLM-driven is possible before then. **The zero-quota queue is empty too** — everything left
in Phase 2 needs a model. If you arrive before the buckets refill, the only useful work is writing
`PHASE-3-SPEC.md`, thin, which costs nothing.

---

**🔴 EVERY PHASE 1 STORY IS DONE. 1.1 through 1.7, all ticked and committed as of 2026-08-02.**

**What remains is the PHASE GATE, and only one of its five conditions is open:**

**🔴 THE GATE WAS RELAXED 2026-08-02 — portfolio calibration, see Decisions.** Condition 1 is no
longer a blocker:

```
1  make test passes, both legs                       ⬜ STRUCK as a gate. 122 passed and all 8
                                                     failures were quota. ~120-130k to re-run,
                                                     which is not what this project is for
2  make golden pass rate recorded                    ✅ 37/38 on deep, zero 429s
3  cross-session RLS denial proven empirically       ✅ story 1.1, six tables
4  a real resume through the deployed Netlify URL
   produces a level Karthik agrees with              🔴 OPEN — HIS, not delegable
5  design foundation implemented, not specified      ✅ story 1.5
```

**Phase 1 is DONE but for Karthik's own eyeball (#4), and #4 is not a blocker on building
Phase 2** — it is a "does the level look right" judgement that can happen any time the deployed app
is up. **Do not hold the build for it.**

**TWO things to do next session, in this order.**

**FIRST, before anything else touches an LLM — re-run the full suite on a fresh daily budget:**

```
cd backend && .venv/Scripts/python.exe -m pytest tests -q --tb=line
```

**`deep` ended 2026-08-02 at 198,515 / 200,000**, so this needs a genuinely fresh bucket — a full
24 hours, since it refills at ~138 tokens/min. **`make test` costs ~120,000-130,000 on `deep`
alone**, measured, because `pytest tests` includes both `tests/golden/` and `test_llm.py`'s
ten-sample structured-output test. **Spend NOTHING on `deep` before it.** Expect `130 passed`.
**Classify every failure before believing it** — on 2026-08-02 all 8 were quota, and one of them
wore an `AssertionError` claiming `deep scored 0/10`.

**SECOND, ASK KARTHIK to do #4** — and note it competes for the same bucket, since every resume he
uploads runs `level_candidate` on `deep` at ~5,000 a go. After a full `make test` there is roughly
70,000 left, which is ~14 resumes. Fine, but not unlimited, and **if `make test` has to be re-run
the same day there is no room for both.**

It is not a code task. The confirmation screen only became reachable on 2026-08-02 and **nobody has
seen it in a browser.** Point him at `https://pmaiinterviewpanel.netlify.app`, warn him the backend
cold-starts in 32-42s, and have him upload his own resume and a few others.

**If both close, Phase 1 is complete.** ~~and the next work is writing `docs/specs/PHASE-2-SPEC.md`
before starting it~~ — **PHASE-2-SPEC.md is already WRITTEN, 2026-08-02**, while `deep` was
exhausted. Phase 2 is unblocked and can start the moment Phase 1's gate closes.

---

**🟢 ZERO-QUOTA WORK AVAILABLE, if `deep` is exhausted again.** Session 8 proved there is real work
that needs no model budget at all, and it is the highest-leverage kind:

```
DONE 2026-08-02   docs/specs/PHASE-2-SPEC.md                     no LLM
DONE 2026-08-02   docs/specs/agents/AGENT-CASE-ARCHITECT-SPEC.md no LLM  (story 2.1)
DONE 2026-08-02   docs/specs/agents/AGENT-PLANNER-SPEC.md        no LLM  (story 2.4)
DONE 2026-08-02   backend/tests/golden/case_architect/           no LLM  (story 2.2, BLIND)
DONE 2026-08-02   backend/tests/golden/planner/                  no LLM  (story 2.5, BLIND)
ONLY ONE LEFT     fix tests/test_llm.py:112                      no LLM to verify - inject a
                                                                 RateLimitError and assert it
                                                                 SKIPS rather than reporting 0/10
```

**🔴 THE ZERO-QUOTA QUEUE IS ESSENTIALLY EMPTY.** Four Phase 2 stories done without a single
LLM call, and both blind golden suites are built and verified. **Everything else in Phase 2 — 2.3,
2.6, 2.7 — needs `deep`**, and so do both remaining Phase 1 gate items.

**The two prompt ceilings are the most actionable thing these stories produced**, and both were
computed before a prompt exists rather than discovered after:

```
Case Architect   ~3,704 tokens   ~15,557 chars     input is candidate_profile
Planner          ~2,904 tokens   ~12,197 chars     input is the whole case_world
```

**Treat both as hard ceilings, not targets.** A single request over 8,000 TPM can never succeed at
any pacing, regardless of `_PACE_SECONDS`. The Resume Analyst's shipped prompt is ~12,200 chars for
comparison, so **the Planner has essentially no headroom over an already-shipped prompt.**

**Stories 2.1, 2.2, 2.4 and 2.5 are ALL zero-quota by design** — they are the spec-and-blind-
fixtures half of each agent, and Phase 1 proved that half is where the leverage is. **A day with no
`deep` budget is a good day to do them**, and doing them early means Phase 2's expensive half
arrives with its gate already built.

**`git status` IS CLEAN** as of session 8's commits. Nothing dirty to pick up.

**Run these three first (~1 min), before anything else:**

```
cd backend && .venv/Scripts/python.exe -m pytest tests -q -m "not live"   # expect 60 passed, 70 deselected
cd frontend && npm test -- --run                                          # expect 74 passed
curl -s https://pm-interview-panel.onrender.com/health                    # {"status":"ok"}, 32-42s if cold
```

**Note the 70.** It was 75 until story 1.7 deleted five `live`-marked Phase 0 tests. The 60 offline
is unchanged and must stay 60.

---

**🔴 BUDGET: `deep` ENDED SESSION 8 AT 198,515 / 200,000 — exhausted.** `fast` has budget but hit
TPM (not TPD) twice on unpaced live tests. Rolling window, refilling ~138 tokens/min ≈ 8,300/hour,
so a full bucket is ~24h away.

**The spend, so the next session can budget honestly:** ~32,000 golden run · ~60,000 case-05 A/B ·
~50,000+ the full `make test` (which re-runs golden inside it). **The lesson is that `make test`
and any investigation cannot share a day.**

**That question is now SETTLED, and settled by decision rather than by measurement.** Karthik
accepted the three flaps on 2026-08-02 and 1.3 is ticked. See Decisions. **Do not reopen it with
more prompt edits** unless one of the named reopening conditions fires.

**THE STATE OF THE SUITE, measured properly for the first time on 2026-08-02:**

```
full run on `deep`   37 passed, 1 failed, ZERO 429s        <- the first honest full run
retry_fired          False on every case, every run, both models
```

**Three of eight cases flap, and they are three DIFFERENT bugs.** That last point matters: it
argues against one prompt edit fixing them, and against "the flap" being a single thing.

```
case 01   over-flags 'years_pm_experience'   on an APM rotational fixture the prompt
                                             EXPLICITLY excludes from that trigger
case 02   returns "cut checkout abandonment..." where the fixture has a
                                             sentence-initial "Cut ..."   (one character)
case 05   assessed_level lands on APM        where the case accepts {PM, Senior PM}.
                                             NEW on 2026-08-02. The uncertainty flag is
                                             FINE here - 9 of 9 - it is the level that moves
```

**Do not re-run the attribution on case 05.** It was done, it cost ~60k, and it returned p ≈ 0.44.
What it did establish is worth keeping: **the committed case-01 fix did NOT suppress the
`assessed_level` trigger** on 05 or 06, which was the specific regression risk. That question is
closed; the level flap is not.

**Before spending anything on a flap, read § Decisions 2026-08-02 on statistical power.** At 4
pairs an A/B can only resolve a case that flaps near 50/50. Case 05 flaps less often than that, so
4 pairs there buys an inconclusive result for a third of a day. **Budget 6-8 pairs, or do not
spend.**

**ASKED AND ANSWERED 2026-08-02.** The options put to Karthik were: tier the suite, k-of-n
sampling, keep fixing prompts, or accept and move to Phase 2. **He chose accept and move on**, and
the reasoning plus the reopening conditions are in Decisions. Phase 2's Case Architect is the
tiebreak on whether this is a prompt problem or a model problem.

**Do NOT relax the case-02 assertion to fold case.** Session 6 deliberately kept
`recapitalized fabrication still rejected` as a control on the typography fold; folding case
dismantles it and lets genuinely fabricated spans through. **This is a prompt problem, and the
prompt already forbids it in words** ("do not lowercase a sentence-initial word..."), so more
prose may not be the fix. Consider instead whether the instruction is reachable at that position
in a ~12,200-character prompt.

**Neither flap is testable on `fast`.** Measured: case 01 never flaps there, case 02 went 3/3
clean. **A green `fast` run is not evidence about either.** This is the trap that has now produced
two false passes; do not walk into it a third time.

**Validate ANY prompt change with the alternating A/B under § Decisions 2026-08-01 (session 7)** —
control loaded byte-exact from `git show HEAD:`, arms interleaved, control REQUIRED to fail.
Budget ~8 calls / ~60k tokens (a third of a model's day) per change validated.

**Cases 03-08 have not run on `deep` since the fix landed.** Run the full set once on a fresh
budget to confirm no regression, especially **05 and 06, which need the `assessed_level` trigger to
FIRE and are the ones the committed fix could plausibly have suppressed:**

```
cd backend && $env:GOLDEN_ROLE="deep"
.venv/Scripts/python.exe -m pytest tests/golden/resume_analyst -q -s --tb=line
```

Expect `38 passed`. **Classify every failure before believing it** — on 2026-08-01, 6 of 7 were
quota, and on the day before, 5 of 6 were:

```
grep -E "tokens per day|tokens per minute|AssertionError" <output>
```

A TPD 429 means stop for the day (200,000 per model, in no header, refills ~138 tokens/min so
roughly one case per hour). A TPM 429 means `_PACE_SECONDS` needs raising again.

**Story 1.3 is tickable only when 05 and 06 are confirmed unregressed AND both remaining flaps are
either fixed or consciously accepted with a written reason.**

**Budget before you start: one full golden run is ~32,000 tokens, 16% of one model's day, and
about 6 runs per model per day exist.** `deep` and `fast` have separate buckets. Iterate on ONE
case; save full runs for confirmation.

**The fixtures and assertions were written blind to the prompt in story 1.3a, precisely so the
prompt cannot be tuned against them. That constraint still holds — iterate the PROMPT, never a
fixture.** Two assertion-side edits were made on 2026-08-01 and both are recorded above with
their falsification: a typography fold that stopped a 42-word exact quote being called a
fabrication, and a pacing constant that stopped 429s being recorded as prompt failures. **Neither
weakened what is checked** — the fabrication, em-dash, case-sensitivity and vacuity controls were
all re-run and still reject. Hold any further assertion edit to that same standard: if changing an
assertion, prove the thing it exists to catch is still caught.

Do **not** run the full live suite to warm up. It is 6-63 minutes and costs real rate budget.
Run it before handover, not before work.

---

**🔴 STORY 1.4 IS BUILT AND COMMITTED (`aa3a756`) AS OF SESSION 7. What follows is the original
brief, kept because its non-negotiables still describe the code that now exists — and they are what
the two outstanding measurements above are checking.** Do not rebuild any of it.

`level_candidate` → `confirm_level`, the first real `interrupt()`. `build.py` gets its first two
nodes. Non-negotiables, all previously recorded:

- **`confirm_level` contains ONLY `interrupt()` and its return.** No LLM call, no counter, no
  write above that line, ever. On resume LangGraph re-runs the node from the top.
- **The single-call assertion goes against `app/llm.py`'s call log, never against state.**
  LangGraph discards the state writes of a node that interrupted, so a doubled call leaves
  counters looking correct. Only the log sees the duplicated side effect.
- `analyse_resume` is a pure function and stays one. **The `agent_events` rows and the
  `resumes.profile` write belong to the NODE, not the function** — the eight golden cases call
  `analyse_resume` directly with no session and no database, so a DB call inside it breaks all
  eight at once.

**The three things 1.6b left 1.4 are all DONE in `aa3a756`:**

1. ~~**Mount `ConfirmationScreen`**~~ → mounted in `App.tsx`, wired to `confirmLevel` via its
   existing `onConfirm` contract.
2. ~~**Wire the `submitLevelCorrection` seam**~~ → real, backed by `POST /session/{id}/level/confirm`.
   `types.ts` was NOT changed, so 1.6b's tests still hold.
3. ~~**Re-check the Realtime startup race**~~ → **resolved as MOOT by reasoning, not measurement.**
   The subscription starts on `sessionId` from `POST /session`, seconds before any agent event can
   land. **It reopens if a future agent ever writes an event on session start.**

**Story 1.3 is the Resume Analyst, and its contract is already written:**
`docs/specs/agents/AGENT-RESUME-ANALYST-SPEC.md`. **That spec is the authority** — output schema,
the four-level rubric, all eight golden cases, and the assertions each must make. Do not redesign
it; implement it. Read it before writing a line of prompt.

**The three things in that spec that matter most, because they are what make it falsifiable:**

1. **Every entry in `scope_evidence` and `notable_outcomes` must appear verbatim in the input
   resume.** A fabricated quote fails the case. This is the single most important assertion.
2. **`level_rationale` must contain a verbatim substring of 8+ words from the input.** That is how
   "cites specific resume content, not generic praise" stops being a matter of opinion.
3. **Golden cases 5-8 are the ones with teeth** (title/scope mismatch, founder, duties-without-
   outcomes, engineer in transition). An agent that nails the four clear levels and is confidently
   wrong on every ambiguous one is the exact failure this product cannot afford. Ambiguous cases
   assert a *set* of acceptable levels plus a populated `low_confidence_fields`, never one level.

**Budget the time. 1.3b is the heaviest LLM story in the phase.** Eight cases across two models is
16+ structured calls per run, and the spec requires running enough times to observe a retry
actually fire. At the bad end of the contention range that is hours. **Run golden cases as their
own `make golden AGENT=resume_analyst` target, never inside the full suite.**

**1.3b's scope is a pure function, not a graph node.** `analyse_resume(resume_text, *, role)` takes
text and returns a parsed `ResumeAnalysis`. The spec's §1 side effects — the two `agent_events` rows
and the `resumes.profile` write — belong to the `level_candidate` **node in story 1.4**. The golden
cases call `analyse_resume` directly with no session and no database, so a DB call inside it breaks
all eight. It must also **assert `resume_text` is non-empty and fail loudly** (spec §7, row 1).

**On the open ARCHITECTURE §4 model question — partially measured, and DO NOT switch yet.** `fast`
has now been run against the same eight cases. It is immune to the case-01 flap across 10
observations where `deep` flaps ~50%, which is a genuine point in its favour. But it fabricated a
`notable_outcomes` quote on case 02 on 2026-08-01, where `deep` passed 02 — the reverse of what
2026-07-31 recorded, on both models. **Neither model is stable across days, so neither a switch nor
a confirmation is supportable on this evidence.** Settle it in Phase 2 with the flap fixed first,
otherwise the comparison is between two coin flips.

**Stories 1.6a and 1.6b are both DONE** — shell, silent anonymous sign-in, upload surface,
orchestration states, and Realtime. 66 vitest tests. Of the four things 1.6b was carrying:
- ~~**Realtime is unproven under the new RLS policies** — the single riskiest unknown left in the
  phase~~ → **RETIRED 2026-08-01.** Proven with two real identities plus a service-role control;
  output above. One residual startup race remains, documented in `lib/agentEvents.ts`, handed to 1.4.
- ~~**Fix the session-per-upload defect 1.6a left**~~ → **DONE 2026-08-01**, and falsified by
  breaking the hoisting and confirming three tests go red.
- **No persona header.** Still binding. The interviewer name is deferred to Phase 3; "Maya Chen" is
  in the register v1 §7 bans. Decided 2026-07-31. **1.6b added none** — confirmed.
- **`.mono-num` still has no user.** 1.6b did not render the assessed level to a candidate (the
  confirmation screen is unmounted pending 1.4), so the first real numerals arrive with **1.4**.
  Apply it to numerals that update, not to static prose like "up to 5MB".

**Story 1.7 deletes the Phase 0 scaffolding**, only after 1.6b is verified: `app/graph/skeleton.py`,
`tests/test_interrupt.py`, `test_api.py`'s skeleton tests, `frontend/src/HealthCheck.tsx`, and the
`/skeleton/*` routes. ~~The Vite starter content in `App.tsx`~~ — **already gone, removed by 1.6a**,
which had to replace it to mount the real shell. **`HealthCheck.tsx` is still mounted and must stay
until STORY 1.4 is verified** — not 1.6b, which is now done. The ordering rule protects the working
reference for backend connectivity, and 1.6's last two boxes (the confirmation screen and its
uncertainty marking) only become reachable when 1.4 mounts them. **Do not delete**
`config.py`'s validation, the lifespan checkpointer, the CORS setup, or anything in
`tests/conftest.py`.

**Keep every agent calling `get_llm(role)`.** Never let an agent import a client directly or
hardcode a model name. That one rule is what keeps a provider switch a six-line change — see
Decisions 2026-07-31 on LLM portability.

**Two live issues that will bite in Phase 3 if forgotten** — both under Blockers below:
`nemotron-3-nano` intermittently leaks reasoning preamble into `content` (it is the Interviewer's
model), and cold start is 32.3s (needs an external pinger before any demo).

**Redeploys are automatic** on push to `main`, for both Render and Netlify. Render only rebuilds
on changes under `backend/`, Netlify only under `frontend/`, so a docs-only commit deploys
nothing.

**Run first (~3 min):** `python backend/scripts/check_env.py`. It now checks all three models and
no longer probes `thinking`.

**Live tests cost about 5m35s and real rate budget.** Use `-m "not live"` (21 tests, 0.6s) while
iterating; run the full suite before handing anything over.

**Before touching agent code, remember the venv:** `backend/.venv/Scripts/python.exe`, or use the
`make` targets. The global interpreter has different versions of fastapi, pydantic, and openai
and does not have langgraph at all.

**On retesting GLM 5.2 — the bar, so it is not re-litigated each session.**
Retest opportunistically. **Correction 2026-07-30: `probe_candidates.py` does *not* test GLM** —
verified by grep; GLM appears only in `probe_models.py` and `probe_nvidia.py`. The retest policy
below therefore had nothing implementing it. Use `probe_models.py`, or add GLM to
`probe_candidates.py`'s model list.

But treat one fast sample as one sample, not as a reversal. The product runs interviews at
unpredictable hours, so a model that is 3s at 09:00 and 230s at 23:00 is unshippable — the
23:00 session is a broken product.

Switch back **only if** GLM is fast across several checks spread through a full day **and**
passes the same 3/3 strict structured-output test Nemotron already passes. Nemotron currently
meets every requirement, so the burden of proof sits with the change.

**Unverified assumption worth closing early:** `nemotron-3-super-120b-a12b` is assumed to have a
1M-token context window, taken from the tech research rather than its model card. The decision to
drop the transcript summarizer depends on it. Confirm from the model card, or measure, before
Phase 5.

---

## Decisions & deviations

Dated log of where reality diverged from the plan. **These entries supersede
`ARCHITECTURE.md` wherever they conflict.**

**🟢 2026-08-09 (session 16) · THE OWED LIVE RUN IS GREEN, AND BOTH OF STORY 4.1'S OPEN QUESTIONS
ARE ANSWERED. NEITHER WAS WHAT IT LOOKED LIKE.**

**🟢 1. THE `kind` CHANGE IS VALIDATED LIVE. Session 15's one outstanding item is closed.**

```
tests/test_conduct_loop.py tests/test_transcript.py -m live  ->  10 passed, 32 deselected, 334.61s
```

No `llm_schema_failure`, no 429, no red. The `kind` change touches `await_candidate`'s return, so
CLAUDE.md's `build.py` trap applied and the re-run was owed; it had died on the daily cap at
197,615/200,000 last session, classified as quota. **Everything from 2026-08-08 is now validated
live, including the code that was already deployed on Karthik's call.** Baseline before it, free:
`429 passed, 111 deselected` offline and `140 passed, 15 files` vitest, both matching session 15
exactly.

**🟢 2. STORY 4.1 OPEN QUESTION #1 — the "duplicate" clarify turn is NOT a replay. Case closed.**

The real transcript (`ac569e9b-db6a-4a17-9a73-b5c1ed43e59f`) has **5 clarify turns, not the 4
PHASE-4-SPEC claims**, and the suspicion was that turns 9 and 11 were a duplicate written by a
LangGraph resume replay. Read from Postgres, they are not:

```
idx=9   'Remind me, what was the Experiences conversion rate again?" '   len=60
idx=11  'Before I go on, what did you say the Experiences conversion rate was?'  len=69
BYTE-IDENTICAL: False        created_at delta: 332.60 seconds
idx list 0..27, count=28, distinct=28, duplicate idx: []   gaps: []
```

**Karthik asked for the same fact twice, five and a half minutes apart, in different words.** A
replay duplicate is structurally impossible here anyway: `unique (session_id, idx)` makes it a 409,
which is what `test_a_replayed_candidate_write_conflicts_rather_than_duplicates` already asserts,
and that guard only ever catches a same-`idx` collision — it cannot see two similar rows at
different `idx`. **The spec's count was simply wrong; the data is sound.** The spec also omits **5
`meta` rows** (the interviewer's clarification replies) entirely — 28 rows total, roles strictly
alternating.

**🔴 3. STORY 4.1 OPEN QUESTION #2 IS REAL, AND IT IS BIGGER THAN "the ground truth is inherited."**

`_check_karthik_live_airbnb` asserts `not_assessed == {market_accuracy, point_of_view}`, inherited
from PHASE-4-SPEC's `dimension_coverage` table. Two independent problems, both found by reading the
real transcript rather than the spec:

- **`dimension_coverage` is the Interviewer's ledger of what it PROBED, not a record of what the
  candidate EVIDENCED.** They are different objects and the spec conflated them. On the transcript's
  own text, turn 21 (*"the placement is the wrong thing to be arguing about... the real question is
  whether Services is a genuine second business or a retention feature"*) and turn 23 (*"I would
  argue it is a retention feature until proven otherwise"*) are a thesis sharpened under pushback —
  `point_of_view`, anchor 4. Turn 25 cites *"the 8.6% we are seeing"*, grounded in the world —
  `market_accuracy`. **Both dimensions the spec calls unevidenced have spontaneous evidence.**
- **The check is unsatisfiable as wired regardless.** `test_golden.py` calls `evaluate_answer` on the
  fixture's LAST answer, which for this fixture is idx=27, **28 tokens**: *"Then I would come back
  with the cohort number and the margin figure before asking for headcount, rather than arguing the
  org change first."* That one sentence cannot evidence `business_model_fluency` and
  `structural_clarity`, which the check requires it to score. The ground truth describes the WHOLE
  interview; the call scores ONE answer.

**Decision: fixture 1's whole-interview ground truth moves to story 4.3**, where the per-answer loop
accumulates across turns and there is something for it to be true of. **4.2's smoke uses a
single-answer fixture instead** — `apm_consumer_world_full_coverage` and
`sparse_world_framework_narration`. Story 4.1's own `test_golden.py` docstring predicted this
("Story 4.2 should expect to rewrite this call site, not merely un-skip it"). **Whether to correct
fixture 1's `expected_not_assessed` to match the transcript is Karthik's call, not the
orchestrator's** — it is a ground-truth judgment about his own interview.

**🟢 4. THE EVALUATOR'S TOKEN FIT IS MEASURED, AND PER-ANSWER SCORING FITS WITH ROOM.**

Computed at the LAST answer before the loop was built, per PHASE-4-SPEC #2's own instruction.
tiktoken `o200k_base`, `Requested = system + human + max_tokens` against the 8,000 TPM ceiling:

```
system prompt                                        936
largest case_world (openai.json)                   1,392
prior_scores, all five dimensions, long quotes       283

worst case   openai world + longest fixture answer + full prior_scores
             936 + 2,158 + 2,048 max_tokens =     5,142   headroom 2,858
stress       openai world + 500-word verbose answer  5,395   headroom 2,605
```

The full transcript measured **10,274** on 2026-08-06 and is over the ceiling — that is what forces
per-answer scoring. **This is the arithmetic showing per-answer actually fits.** It fits because
`prior_scores` is a running summary bounded at five entries, not a transcript, so **this budget does
not grow with turn count** the way the Interviewer's window does. The numbers live in a comment
block above `_EVALUATION_SYSTEM_PROMPT` in `app/agents/evaluator.py` and are asserted by
`tests/test_evaluator_budget.py`, offline, at zero cost.

**🔴 5. `framework_narration` IS NOT PERSISTED IN PHASE 4. `reasoning` GETS A COLUMN.**

PHASE-4-SPEC 4.3 requires this decided before 4.2, not after. `answer_evaluations`' grain is
`(session_id, turn_idx, dimension)`.

- **`reasoning` fits that grain exactly** and Phase 5's Coach may consume it (the spec's own Handoff
  lists it as an open question). It gets a nullable `reasoning text` column in a new migration in
  story 4.3. Near-zero cost, and it cannot weaken anything.
- **`framework_narration` does NOT fit that grain** — it is one bool per ANSWER, not per dimension.
  Putting it on the score rows denormalizes it five ways, and there is a case where it would be
  **silently lost entirely**: an answer where all five dimensions are `not_assessed` writes **zero
  rows**, because `score` is `not null` and an unassessed dimension is represented by the absence of
  a row. Nothing in Phase 4 reads it — 4.4's scorecard boxes do not render it. **It stays on
  `AnswerEvaluation` in memory and gets its own table in Phase 5 if the Coach actually consumes
  it.** Deliberately not a column, and this is the reason.

**🟢 6. STORY 4.2 IS DONE. The Evaluator scores live, and the smoke is green on `fast`.**

Delegated the mechanical half (module assembly + the offline budget test) to a Sonnet subagent; the
prompt, the budget arithmetic, the role measurement and every live run stayed with the
orchestrator. Independently re-verified: `439 passed, 111 deselected` (was 429/111), **deselected
unchanged**, and the subagent's diff deletes exactly the two docstring paragraphs it was asked to
rewrite and nothing else — `_EVALUATION_SYSTEM_PROMPT` and the budget block have zero `-` lines,
and `tests/golden/evaluator/test_golden.py` is untouched.

```
GOLDEN_ROLE=fast   apm_consumer_world_full_coverage   PASS   retry_fired=True
                   sparse_world_framework_narration   FAIL   (see #8)
GOLDEN_ROLE=deep   apm_consumer_world_full_coverage   PASS   retry_fired=True
                   sparse_world_framework_narration   PASS
```

**Two contradictions the subagent reported rather than papered over**, both correct and both now
folded into the comment block: the recorded 5,142 worst case is a synthetic cross-product no
fixture contains (highest real fixture is 4,783, and the stress case at 5,398 is strictly worse and
is the row actually asserted), and its `prior_scores` stand-in is 438 tokens against the comment's
283 because it adds a `reasoning` string — making the executable test **stricter** than the
arithmetic, not looser. This is the shape of subagent report worth having.

**🔴 7. THE ROLE MEASUREMENT SAYS `deep`, AND WE STAYED ON `fast` ANYWAY. Deliberate.**

PHASE-4-SPEC 4.2 required measuring rather than inheriting PRD §3's `deep` assignment. Measured:
**`deep` 2/2, `fast` 1/2** on identical input. Staying on `fast`, for three reasons that outweigh
one sample:

- **One `deep` run is not a measurement.** DEV-STATE 2026-08-08 established `fast` is deterministic
  and `deep` flaps against identical input. A single green `deep` is exactly the evidence this
  project has repeatedly learned not to trust.
- **The single disagreement is a rubric definition question, not a capability gap** (#8). `fast`
  did not produce a malformed or fabricated answer; it produced a defensible reading of an
  ambiguous rule.
- Agents default to `fast` per the 2026-08-02 calibration, and `deep` costs several times the
  budget on the model whose daily cap is the thing that stops work.

**🔴 8. AN OPEN RUBRIC QUESTION, SURFACED BY `fast` AND NOT DECIDED: does demonstrating a LOW
anchor count as evidence, or does `not_assessed` mean "did not engage this dimension at all"?**

`sparse_world_framework_narration` is an answer that names RICE, build-versus-buy and a 2x2 and
**never picks** between the repair tool and the support hire. The fixture expects `decision_quality`
in `not_assessed` (no decision made, so nothing to score). `fast` instead scored it **2**, quoting
the RICE sentence.

**`fast` is arguably right.** PRD §7's decision_quality anchor 1 is literally *"Hedges, or picks
without stating criteria"* — an answer that hedges has directly demonstrated anchor-1 behaviour, and
it produced a real verbatim quote for it. Scoring it low is more faithful to the written anchor than
declining to score.

**But it erodes something load-bearing.** If "absence of X" is evidence for a low score on X, then
`not_assessed` becomes nearly unreachable, and PHASE-4-SPEC #1's central rule — do not put a number
on a dimension nothing was said about — loses its teeth. The spec already names this as **Karthik's
call** ("whether an unassessed dimension is acceptable at all"), and it is now a concrete instance
rather than a hypothetical. **Not decided. Not worked around. The fixture stands as written and the
disagreement is recorded.**

**One thing NOT attributed:** `apm_consumer` failed before the prompt change and passed after it, but
the prompt changed between the two runs, so **this does not isolate fix from flap.** Recorded as
observed, not as a causal claim.

**🟢🔴 2026-08-08 (session 15) · SESSION 14'S FIXES ARE VALIDATED, THE PROBE-7 FAULT IS NOT A
DEFECT, AND A SECOND LIVE INTERVIEW FOUND TWO MORE.**

Every ⬜ in session 14's handoff table is now resolved. Budget spent: **197,615 / 200,000 `fast`**,
which is the whole day and is why the last item on this list is unvalidated.

**🟢 1. THE BATCHING HYPOTHESIS HOLDS. The probe-7 shape fault was never a product defect.**

```
tests/test_conduct_loop.py -m live   ->  4 passed, 31 deselected, 346.52s
```

First fully green live run of this file, ever. All four tests, including the eight-probes-plus-
boundary-exit assertion. **No `llm_schema_failure` record was logged**, which `cbd5ce2` added
precisely so the next failure would name itself. `_paced()` at ~21s between calls is the only
thing that changed. **This retires `_append_retry_instruction` as an open item** — session 14 said
it was "only worth acting on if the paced run still reds", and it did not.

**🔴 2. `gpm_portfolio_world` HAD NEVER BEEN EXECUTED, AND IT FAILED 3/3 BYTE-IDENTICALLY.**

The fixture written FOR the 2026-08-07 false-premise fix had never been run. Run live, it produced
the identical string three times:

> "Business banking is the smallest product line, with $28M ARR. To protect its lead while still
> growing payments and lending, **I would allocate the 40 new roles as follows: 15 to business
> banking, 20 to payments, and 5 to lending** ..."

**`fast` (gpt-oss-20b) is DETERMINISTIC here.** The 2026-08-01 flapping finding was measured on
`deep`; do not generalise it to `fast`. A 3/3 byte-identical repeat is a stable defect, and it
means **one golden run on `fast` is a meaningful signal**, which is not true on `deep`.

**Step 1's first-sentence rule fired exactly as designed.** What lost was everything after it: the
answer handed over the ANSWER TO THE INTERVIEW QUESTION, in the first person. The figure check
reported it as ungrounded `20` and `5`, which reads like a grounding nit and is actually the
interviewer giving away the interview. **The test never reached the false-premise assertion** —
the figure check at `test_golden.py:180` runs before `case.check` at line 225. Replaying the
captured string through the fixture's own assertion offline (zero tokens) confirmed
`echoes_false_premise = True`, so it would have failed that too.

**The fix, and the shape of it matters more than the words:** step 1's no-echo clause was left
**untouched**. It already banned this shape, and adding words to a rule that is already there is
the move that lost on 2026-08-07. Nothing in the prompt forbade *solving the case* — a missing
rule, not an ignored one. The second edit exists only because the first was routed around:

```
0/3 byte-identical fail  ->  3/5 (scope rule)  ->  4/4 (same rule held in ANY voice)
```

The 3/5 sample that failed said *"Northaven has **decided** to allocate 15 roles..."* — the same
allocation reframed as a fact about the company. **A banned recommendation will come back wearing
a different voice; ban the content, not the grammar.**

**🟡 3. THE INTERVIEWER GOLDEN SUITE IS 5/7, AND BOTH REDS ARE PRE-EXISTING.**

```
tests/golden/interviewer -m live  ->  2 failed, 5 passed, 52 deselected, 496.70s
```

Attributed by `git stash`, re-running both against the **committed** prompt — both reproduce, so
neither is a regression from the scope rule:

| Fixture | Failure | Note |
|---|---|---|
| `pm_b2b_world` | `['46.5']` ungrounded | `46.5` is `81.2 - 34.7`, both grounded. **The one fixture whose entire point is combining two supporting facts, and the figure check punishes the combination.** A test-design flaw, not a model defect |
| `senior_pm_platform_world` | `grounded_in` fabricated | Returned a JSON field PATH (`company.employees`) on one run, a paraphrase on another. Fails either way |

**Both were newly visible only because these fixtures had barely been run live.** Per the agent
table only two of five ever had been.

**🟢 4. INVENT-AND-RECORD REPLICATED, ON A FACT THAT IS NOT IN THE WORLD.**

Second live interview (2026-08-08, GPM, OpenAI world). Asked about the return cap, the interviewer
answered **"100×"**. `grep "100" app/cases/openai.json` returns **nothing** — the model invented
it. Asked again several probes later, it returned **100×** again, identical figure and units. That
replicates the `3.2%` result of 2026-08-07 on a second independent case.

**🔴 THE REAL-COMPANY GROUNDING LEAK, AND IT IS A COST OF STORY 3.5.2 NOBODY HAD NAMED.** 100× is
the *true* public figure for OpenAI's cap. The model knew it from training, not from the brief.
**With real companies, a leaked fact is TRUE, so it reads as correctly grounded and neither a human
nor `ungrounded_figures` can distinguish it from a real citation.** With invented companies a leak
looks obviously wrong. **Real worlds make grounding violations harder to detect, not easier.** No
action taken; recorded so it is not rediscovered as a surprise in Phase 4.

**🔴 5. PROBES 8 -> 4. Karthik's call, and it removes a measured defect as well as length.**

Probes 6, 7 and 8 **recycled probes 1, 2 and 3**. Observed live: probe 6 reopened probe 1's
framing verbatim ("With the massive compute commitments already signed"), probe 7 reopened probe
2's Google-TPU subject.

**The cause is structural, not stylistic.** `select_probe_angle` correctly sends the ladder back
for a SECOND visit once all five dimensions are covered, and `generate_probe` sees only a **4-turn
window**, so by probe 6 it cannot see the probe it is about to repeat. **Four probes never reach
the second visit, so the repetition cannot arise.** Same window limitation PHASE-4-SPEC already
flags as unusable for the Evaluator.

**🔴 THE KNOWN COST, by design now where 2026-08-07 had it by accident: five dimensions, four
probes, so EXACTLY ONE DIMENSION GETS ZERO EVIDENCE EVERY INTERVIEW.** `not_assessed` in Phase 4
is now **load-bearing, not defensive**. Three probes was rejected for leaving **two** blank, which
is the exact defect the steering fix removed.

Every test now **reads `_PROBES_THIS_PHASE`** instead of repeating its value. That immediately
caught a hardcoded `7` that would have stayed green while testing a boundary production no longer
had. Live re-run at the new count: **4 passed, 261.85s** (was 346s at 8).

**🔴 6. A CLARIFYING QUESTION WAS BEING STORED AS A CANDIDATE POSITION.**

Probe 8 said: *"You said OpenAI is a straightforward for-profit company answerable to
shareholders"* — a **false premise Karthik had only ASKED about**, and which `answer_clarification`
had already correctly refused on the same turn.

`route_input` knew the difference; **`messages` threw it away.** `_messages_to_turns` mapped every
`HumanMessage` to `role: "candidate"`, as its own docstring stated outright. The probe prompt tells
the model to quote "a claim they made", and a question and a claim reached it looking identical —
**the rule was unenforceable no matter how it was worded.**

`kind` now travels the whole path: tagged in `await_candidate` (below the interrupt, a pure read of
`value`), through `_messages_to_turns` as an **ADDITIONAL** key — `role` deliberately unchanged
because `_covered_probe_count` counts on it — labelled in `_render_transcript`, and ruled on in
`_PROBE_SYSTEM_PROMPT`. A missing `kind` reads as `"answer"`, so pre-2026-08-08 checkpoints replay
unchanged (tested).

**A SECOND instance of the same bug, found on the way:** `_windowed_transcript` anchored on the
first `role == "candidate"` turn and called it "the first candidate answer". **A candidate opening
with a clarifying question pinned that question into the probe's view for the entire interview** —
the one turn guaranteed to survive windowing would have been something they asked, never anything
they argued. Anchored on the first real answer now, and **falsified by mutation**: reverting the
`kind` check makes the new test fail while the back-compat test still passes.

**🔴 THIS IS THE ONE THING FROM 2026-08-08 THAT IS NOT LIVE-VALIDATED.** It touches
`await_candidate`'s return, so CLAUDE.md's `build.py` trap applies. The live graph re-run was
attempted and died on the daily cap:

```
429 ... on tokens per day (TPD): Limit 200000, Used 197615, Requested 3291
```

**QUOTA, NOT DEFECT** — classified per CLAUDE.md before being recorded. Offline is green at 394 and
the mutation test holds, but **the live path is owed a run on fresh budget.**

**🟡 7. TWO ITEMS CONSCIOUSLY ACCEPTED (Karthik, 2026-08-08), not fixed.**

Same pattern as the golden-flap acceptance of 2026-08-02: accepted with reopening conditions
written down, rather than spending budget on them.

| Accepted | Reopen if |
|---|---|
| `airbnb.json` says "In 2024, Airbnb relaunched" in three fields; Services and Experiences was the **May 2025** Summer Release. A wrong date, not a stale one, and the whole `situation` rests on it | A candidate visibly trips on it, or the sheet is used in a portfolio demo where the date is checkable |
| "protect its lead" survives a correction. Even in PASSING runs the answer can correct the premise and then still use the candidate's framing. `echoes_false_premise` passes it because "actually" sits nearby as a correction marker | The incoherence shows up in a scorecard or a coaching report, where it is read rather than skimmed |

**🟢 8. DELEGATION IS NOW A SESSION-START DECISION (CLAUDE.md, `01e44da`).**

Karthik's instruction. CLAUDE.md § Start of every session gains **step 6, a delegation plan written
before any work begins**, and § How work is done gains a **triage table**. The organising principle
is the part to keep: **the dividing line is not difficulty, it is REVERSIBILITY OF A WRONG ANSWER.**
A wrong mechanical edit fails loudly in the suite; a wrong judgment about what a green run *means*
gets written into this file and believed for weeks.

Recorded because the ambiguity had a measured cost: CLAUDE.md said delegate, the session harness
said do not spawn without being asked, and **the conflict was resolved silently in favour of inline
work for an entire session** — two textbook Sonnet briefs written at Opus rates.

**🟢🔴 2026-08-07 (session 14) · THE PROBE LOOP COMPLETED A LIVE RUN FOR THE FIRST TIME, AND THE
`max_tokens` FIX IS HALF RIGHT.**

`tests/test_conduct_loop.py -m live` was run **twice**, in full. Neither run was green, **and every
one of the four tests passed in at least one of them.**

| Run | Result | Failures |
|---|---|---|
| 1 | 2 failed, 2 passed, 251s | tests 2 and 4 (both clarify path) |
| 2 | 2 failed, 2 passed, 190s | test 1 (probe 7), test 3 (**429**) |

**🟢 The single most important observation: in run 1
`test_the_loop_asks_the_one_question_then_probes_and_exits_at_the_probe_count_boundary` PASSED.**
All eight probes, then a clean exit at `_PROBES_THIS_PHASE`'s boundary, across real
`Command(resume=...)` boundaries. That is phase-gate condition #3's central assertion and it had
**never once been observed** before today.

**🟢 So session 13's `generate_probe` `max_tokens` 1024 -> 2048 IS real, and is no longer an
unverified fix.** It was applied blind when the daily cap killed the re-run. Probes 1-6 now succeed
consistently where probe 3 used to fail.

**🔴 But it did not close the hole, it moved it.** Run 2 failed at **probe 7**, `ask_probe`,
`StructuredOutputError` after `json_validate_failed` on BOTH the attempt and the retry.

**🔴 AND THE OBVIOUS NEXT FIX IS THE WRONG ONE.** The probe-7 body carries Groq's **generic**
`"Failed to validate JSON. Please adjust your prompt."` — **not** the truncation variant
(`"max completion tokens reached before generating a valid document"`) that justified 1024 -> 2048.
Those two faults share the `json_validate_failed` code and want **opposite** fixes. Raising
`max_tokens` a third time would change nothing.

**The log could not tell them apart**, because `_attempt` truncated the body at `str(exc)[:200]`,
which cuts off immediately before `failed_generation`. Fixed this session in `cbd5ce2`: a separate
`llm_schema_failure` record carries the full message and up to 2,000 characters of
`failed_generation`. Deliberately **not** prefixed `llm_call`, because `_ok_llm_calls` filters on
that prefix and the record must not perturb a call count. The 200-char string stays in the retry
prompt on purpose — **lengthening the prompt is the wrong direction on a call whose reasoning
budget is what ran out**, and it is a live hypothesis that appending the retry instruction is why
the retry fails too, at both probe 3 and probe 7.

**🔴 CLASSIFY BEFORE BELIEVING, AGAIN — and it paid off again.** Run 2's other failure was
`429 ... on tokens per minute (TPM): Limit 8000, Used 5567, Requested 2718`. That is the
**per-minute** ceiling, not the daily cap, and it is **an artifact of 16 live calls fired back to
back with no human between them.** A real interview is paced by a candidate typing, so it does not
hit this. **Not a defect. Do not "fix" it in application code.** If the live file is to be reliably
green it needs pacing in the TEST, not backoff in `llm.py`.

**Probe depth alone does NOT reproduce it.** A synthetic transcript built to probe-7 depth and sent
through the raw runnable (no retry wrapper) succeeded **3 times out of 3**, spaced 20s apart. So
this is not a clean size threshold; it is intermittent, and it belongs to the MoE non-determinism
class already recorded under 2026-08-01.

**🔴 THE BATCHING HYPOTHESIS — test this BEFORE spending anything on a `max_tokens` or prompt fix.**
Three data points, all pointing the same way, and they say probe 7 correlates with **rapid-fire
batching, not transcript depth**:

| Context | Probe 7 |
|---|---|
| Live test file, ~16 calls back to back over 190s | **failed** |
| Synthetic reproduction, spaced 20s apart | passed 3/3 |
| **Karthik's real interview, human-paced** | **passed** (session 14, below) |

This fits the mechanism already recorded on 2026-08-01: these are MoE models, and expert routing
and reduction order **shift with whatever shares the batch**. Sixteen calls fired in three minutes
share batches that a human-paced interview never does.

**If the hypothesis holds, NEITHER of today's two live failures is a product defect** — the 429 is
definitely a pacing artifact and the `json_validate_failed` probably is. **The test is cheap: pace
`test_conduct_loop.py` and re-run it.** Do that before touching `generate_probe`. Do not record it
as confirmed on three data points; it is the best available explanation, not a measurement.

**What this costs a candidate:** `_PROBES_THIS_PHASE` is 8, so a real interview goes **through**
probe 7. Karthik was told the odds before choosing to sit gate #4 today anyway (see below).

**🟢🔴 2026-08-07 (session 14) · KARTHIK SAT A FULL INTERVIEW ON THE DEPLOYED STACK. THE LOOP IS
RIGHT; THE QUESTION IS WRONG FOR A DIAGNOSED, DETERMINISTIC REASON.**

Session `ac569e9b-db6a-4a17-9a73-b5c1ed43e59f`, Airbnb, `assessed_level = 'Senior PM'`. One
question, four clarifications, **eight probes, clean exit at the boundary** — the ninth answer
returned no interrupt. Graph state was read directly from the checkpointer at every step, so
everything below is observed, not inferred.

### 🟢 Verified live, with a human, for the first time

| Property | Evidence |
|---|---|
| The full loop runs to the boundary | `followup_count` 8, then answer 9 exits with no interrupt |
| **Invent-and-record INVENTS** | `3.2%` asked for; neither `3.2` nor `conversion` appears anywhere in `airbnb.json` |
| **…RECORDS** | `improvised_facts = ['Assume the current booking conversion rate for Experiences is 3.2%.']` |
| **…REPEATS EXACTLY** | asked cold two probes later in different words, returned `3.2%` |
| **…and does NOT re-record** | still **1 entry** after the repeat. `improvised_fact` came back empty, so nothing appended |
| The append signal discriminates | 3 for 3: scope clarification -> no entry, invention -> 1 entry, repeat -> no new entry. `improvised_fact` (not `can_answer`) is the correct signal, confirmed |
| Clarifications consume no question slot | `current_q_idx` stayed **1** across four clarifications |
| **The probe responds to the answer** | **8 of 8** quoted the candidate's own specific claim. `write_bridge`'s constant-function failure does NOT occur |
| The probe ladder engages | probe 4 is ladder angle #1 almost verbatim ("margin contribution of Services bookings versus core lodging") |
| `stripDashes` works | a **U+2011** in the served probe was normalised for display |
| 3.5.1's candidate turns | `transcript_turns` holds all 17 rows including every candidate turn |

**🟢 PROBE 7 DID NOT CRASH under human pacing** — see the batching hypothesis in the entry above.

### 🔴 DEFECT 1, the worst: A FALSE PREMISE WAS ACCEPTED, AND IT IS A REGRESSION

Asked *"Since the short-term rental market is shrinking, does that change how much Services
matters?"* against a world stating `growth_rate_pct: 8.6`, the Interviewer replied:

> `[idx=16 interviewer/meta]` **"Yes, the shrinking short‑term rental market makes Services and
> Experiences a more critical growth driver."**

`_CLARIFICATION_SYSTEM_PROMPT` contains an explicit rule against this, with a worked example of
nearly the same shape, and **both halves failed**: it accepted the premise AND repeated the false
claim back, which the prompt bans in those words.

**🔴 THIS PASSED ON 2026-08-05 AND FAILS NOW.** That test hit the **refusal branch**, which story
3.5.4 DELETED in favour of invent-and-record. **The disposition that makes the agent helpful (never
decline, always hand the candidate something) is the same one that makes it agreeable.** That trade
was not visible when the decision was made, and **no test in any suite can see it.**

**Blast radius is limited, and that was measured, not assumed:** the claim never entered
`improvised_facts` (still 1 entry), and **it never resurfaced across probes 4 through 8** — a later
answer asserting the correct 8.6% drew no contradiction and no correction. It is a one-turn lie in
`transcript_turns`, not a poisoned interview.

### 🔴 DEFECT 2: `select_category` IS UNCALIBRATED, AND IT IS WHY THE QUESTION WAS WRONG

The question served was *"How would you increase booking conversion for Airbnb Services and
Experiences?"* — a **growth-funnel** question, in a product whose premise is a **Product Strategy**
interview. Reproduced deterministically:

```
APM        -> strategy  | What is {company}'s biggest threat over the next three years?
PM         -> gtm       | How would you launch {product} for {new_segment}?
Senior PM  -> growth    | How would you increase {conversion_step} for {product}?   <- served
GPM        -> strategy  | What is {company}'s biggest threat over the next three years?
```

**The junior level gets the strategy question and the senior level gets funnel optimisation.**
`_LEVEL_INDEX` is taken modulo however many categories a world happens to list, so which category a
level receives depends on **the length of that world's JSON array**, not on anything about the
level. `shapes.py` says so about itself ("arbitrary but fixed… no claim that this ordering is
calibrated to level difficulty"); **story 3.5.3 shipped the placeholder.**

**🟢 FIXED 2026-08-07, same session, at ZERO token cost** — this is deterministic Python, so the
whole repair is free. **Karthik's calibration: strategy wins whenever the world suits it, at every
level, and level selects difficulty WITHIN strategy.** The product is a Product Strategy interview,
so the category is not a dial to vary by seniority. All eight curated worlds list `strategy`, so
this governs every real interview. The other three categories stay reachable for worlds that do not
suit strategy.

```
Airbnb, after:                          (before: APM strategy / PM gtm / Senior PM growth / GPM strategy)
  APM        -> strategy | What is {company}'s biggest threat over the next three years?
  PM         -> strategy | Should {company} enter {adjacent_market}?
  Senior PM  -> strategy | {company} can make one big bet next year. What should it be?
  GPM        -> strategy | {company} can make one big bet next year. What should it be?
```

**🔴 AND THE FIX FOUND A SECOND, INDEPENDENT INVERSION.** `select_shape` used
`% len(candidates)`. Shapes are ordered easiest-first, and `strategy`, `gtm` and `pricing` each hold
**3 shapes against 4 levels** — so **GPM (index 3) wrapped to index 0 and drew the APM question.**
The same seniority inversion, once across categories and once inside them. Now a **clamp**: a level
past the end saturates at the hardest shape.

**🔴 THE SUITE WAS SILENT ON ALL OF IT, AND THAT IS THE REAL LESSON.** Inverting the category
mapping for every level left **374 offline tests green**. The existing assertions covered
determinism, membership and fallback, but **nothing asserted WHICH category a level receives.** The
behaviour that produced gate #4's wrong question had no test at all. Three added, and **falsified by
reverting both fixes** — 2 of the 3 fail against the old code and pass against the new. The
monotonicity one is deliberately not an index assertion, so it keeps working at any future bank
size. **Its first draft was itself wrong**: it read seniority order out of `FOUR_LEVELS`, which is a
`set`, so it iterated `APM, Senior PM, GPM, PM` and failed against correct code. It now carries its
own ordered tuple plus a drift guard.

**377 passed, 103 deselected** (was 374; the three are the new ones).

**The material was all there and was thrown away.** The same case carried
`situation.prompt` ("how much should Airbnb invest in Services versus defending core lodging
against regulatory and growth headwinds") and a ladder naming **New York's Local Law 18**, Chesky's
Amazon-like vision against quarterly investor expectations, and Services unit economics. **The
Planner is not the problem. The category selector is.**

### 🟡 The rest, all observed this session

- **Two of five dimensions were NEVER covered** in a full eight-probe interview. Final
  `dimension_coverage = {business_model_fluency: 4, decision_quality: 4, structural_clarity: 1}`;
  `market_accuracy` and `point_of_view` both **0**. **Coverage is tracked and never steers** —
  nothing pushes a probe toward what is uncovered. **Phase 4 will have two dimensions with no
  evidence to score.**
- **Every probe is double-barrelled, 8 of 8** — two questions in one turn. A property of
  `_PROBE_SYSTEM_PROMPT`, not a quirk.
- **Every clarification answer was ONE sentence, 4 of 4**, where the prompt demands 2-4. On the
  recall question `3.2%` alone is arguably better than the rule; the rule may be what is wrong.
- **The repeat was NOT verbatim.** Stored as a full sentence, returned as `3.2%`. Same number, same
  units, different wording. The property that matters held; the prompt's literal "same wording"
  did not.
- **The transcript window costs contradiction-catching, and this is the first measurement of that
  cost.** A deliberate self-contradiction planted four turns apart went uncaught because the
  earlier turn had **fallen out of** first-answer-plus-last-4. Not a model failure; the price of the
  2026-08-06 budget decision.
- **A probe asked for something already stated** — the definition of "attach rate", which sat in the
  permanently-pinned first answer inside its own context window.
- **U+2011 reached the durable rows**: 3 in `question_plan`, 1 in the served probe, 1 at
  `transcript_turns` idx=16. `stripDashes` covers display only. **Phase 4 renders scorecards from
  these rows** — the item DEV-STATE flagged as "not absorbed" is now observed, not predicted.
- **UI:** both validation hints ("Write an answer before submitting", "Type a question first") show
  on untouched fields — an error state before any interaction.
- **UI:** the orchestration column says *"Case Architect · Built the case for your interview"*, but
  that agent has made **zero LLM calls** since session 13. Misleading on a portfolio artifact whose
  subject is multi-agent orchestration.
- **Fact sheet, Karthik's call:** `airbnb.json` says **"In 2024, Airbnb relaunched"** in three
  fields (`company.one_line`, `market.description`, `situation.prompt`). Services and Experiences
  was the **May 2025** Summer Release. Not a stale date, a wrong one, and the whole situation rests
  on it.

**🟢 2026-08-07 (session 14, later) · THREE MORE FIXES, ALL AT ZERO TOKEN COST. 384 offline passed.**

**1. The false-premise regression is fixed in the prompt — UNVALIDATED LIVE.**
`_CLARIFICATION_SYSTEM_PROMPT` was a TWO-way decision (cite the world, or invent) with a premise
warning bolted on beside it, so a leading question read as a gap to fill and helpfulness won. It is
now **three ordered steps with contradiction FIRST**, and "silent" is defined explicitly as the
world saying nothing either way rather than saying something the question would rather it did not.
**The words banning this were already in the prompt and lost anyway** — the ordering is the fix, not
more emphasis.

**🔴 THE TEST FOR THIS ALREADY EXISTED AND HAD NEVER BEEN RUN.** `gpm_portfolio_world` is the
adversarial leading-question fixture, written blind on 2026-08-05, asserting the premise is not
accepted. Per the agent table only `apm_consumer_world` and `senior_pm_platform_world` were ever
smoked live. **The regression shipped with its own test sitting unexecuted.** Running the three
never-run interviewer golden cases is now worth more than writing new ones.

Its assertion was also too narrow — it looks for the false claim being ASSERTED ("banking" plus
"largest"), and the live failure ACCEPTED the premise in a subordinate clause and built on it
("Yes, the shrinking market makes..."), which that check walks straight past. Added
`echoes_false_premise(answer, false_terms)`: flags an echo of the premise **with no correcting
language beside it**. A bare term match would fail correct answers, since a correcting answer has
to name the false term to deny it. **Pinned to the verbatim live string**, with a correcting-answer
control, a quiet-acceptance case, and an empty case.

**2. `normalize_dashes` closes the dash hole at the GRAPH BOUNDARY** (`app/text.py`, new). The
Python twin of `stripDashes`, applied in `build.py` to the question, the clarification answer, the
probe, **and `improvised_fact`** (which is replayed into every later prompt, so a raw dash there
kept re-entering the model's input).

**🔴 It is at the boundary, NOT in the agents, and that is load-bearing.** The golden suites assert
`no_dash_variants` on what the agent FUNCTIONS return; normalising inside them would make every one
of those assertions pass **vacuously** while generation quietly got worse. `compose_question` also
guarantees byte-for-byte emission and could not normalise regardless.

**The drift guard grew a fourth arm, and writing it corrected a wrong assumption of mine.** The
golden suites' `_DASH_VARIANTS` holds only the **four** aside/range dashes, and that is CORRECT: a
ban is right for an em dash in prose, and wrong for U+2011 in "state-of-the-art", which wants ASCII
normalisation. So the app covers seven and the suites assert on four, deliberately. My first test
asserted flat equality and failed, which is how the distinction got pinned. There is now also a
**Python/TypeScript parity test** that reads `copy.ts` as text and compares character classes.

**3. `test_conduct_loop.py -m live` is PACED** — `_paced()`, ~21s between calls, from 8,000 TPM
against a measured ~2,700-token probe request. **In the test, never in `app/llm.py`**, which
re-raises transport errors untouched on purpose. Until this runs, a red run in that file is
unreadable: its two failures were on **different tests each time**.

**4. Both input hints are gated on `touched`.** They were gated only on the field being empty, which
it always is before anyone types, so a freshly served question arrived already telling the candidate
what they had done wrong. The submit button is disabled while empty regardless, so the hint's only
job is explaining a disabled button someone actually reached for. Guarded by a test asserting
**neither** hint renders on arrival.

**5. The Case Architect's copy says "Choosing"/"Chose the company", not "Building"/"Built the
case".** That node stopped generating anything on 2026-08-06 — `select_case_world` is deterministic
Python over eight curated companies and makes zero LLM calls. On a portfolio artifact whose subject
IS multi-agent orchestration, an agent credited with generation it does not do is the first thing a
reader would catch. Changed in **both** `build.py` and `OrchestrationColumn.tsx`, which are required
to stay byte-identical.

**384 offline, 140 vitest** (both were green before at 384/139; the vitest gain is the new
hints-on-arrival guard). Two frontend tests asserted the old behaviour and were updated with it,
not around it.

**🟡 2026-08-06 (session 13) · `tiktoken` WAS AN UNDECLARED DEPENDENCY, IMPORTED AT MODULE LEVEL.**

Story 3.5.4's token-budget test does `import tiktoken` at the top of the file, so the whole file
fails to COLLECT without it — and it was present only as a transitive dependency of
`langchain-openai`. A test suite resting on somebody else's dependency tree is one upstream change
away from a red run nobody caused. Pinned at `0.13.0` under `# Dev`, with a note that
`get_encoding("o200k_base")` fetches its BPE file on first use.

Found by walking CLAUDE.md's **triggered updates** table at the end of the session rather than by
anything failing. That table earns its place: nothing was broken, and nothing would have been until
the day it was.

**🟢 2026-08-06 (session 13) · THE DASH-FAMILY HOLE IS CLOSED, AND THERE WAS A THIRD COPY NOBODY
KNEW ABOUT.**

Carried open since session 12 and observed live today: `stripDashes` and `no_dash_variants` each
caught **2 of the 7** dash-family characters, and a U+2011 reached probe text.

**The fix is two classes, not one wider list**, which is why "add the other five to the comma rule"
would have been wrong:

| Class | Characters | Treatment |
|---|---|---|
| Aside / range | U+2012, U+2013, U+2014, U+2015 | The existing one: digit ranges become "to", anything else becomes a comma |
| Hyphen-like | U+2010, U+2011, U+2212 | **Normalise to ASCII `-`** |

Turning the non-breaking hyphen in "state-of-the-art" into a comma would be worse than leaving it,
and there is now a test for exactly that string which the naive fix cannot pass.

**The assertion and the stripper deliberately cover different sets.** `no_dash_variants` covers the
four aside/range dashes only: the hyphen-likes normalise correctly at render, so flagging them would
fail a golden case over text that reaches the candidate perfectly well. `test_user_facing_copy.py`
covers **all seven**, because it scans the project's own backend source strings (`HTTPException`
messages, `_SUMMARY` constants, `_TRANSITIONS`) — those reach the candidate with **no `stripDashes`
downstream**, so a developer-typed non-breaking hyphen there ships exactly as typed. That
distinction was a subagent's correction to my brief and it is right.

**🔴 There were THREE copies of the constant, not two.** `resume_analyst/assertions.py` had its own
2-of-7 version and was left behind by the widening — found only because a subagent flagged it as out
of scope rather than staying silent. Its surface is `level_rationale`, **which the candidate reads
on the confirmation screen**, so the weaker rule was live on a real surface. All three are now equal
and **pinned equal by a drift guard**, falsified by removing one character from one copy and
watching it fail with an exact diff.

```
backend   374 passed, 103 deselected   (was 367)
frontend  139 passed, 15 files         (was 131)
```

**🟢 2026-08-06 (session 13) · KARTHIK ACCEPTS THE INVENTED FIGURE AS-IS. DEFECT CLOSED, NOT FIXED.**

> "i'm ok with invented number, we are not conducting an actual interview, its just practice
> simulation."

The improvised fact came back fake-round ("5 million weekly active users"). **No code change, and no
assertion contradicts the decision:** `contains_fake_round_number` matches banned round
*percentages* only, so "5 million" was never in its range. Nothing is red and nothing is pending.
**Do not reopen this as a defect** — the round-number ban exists to stop a *generated case world*
reading as fiction, and an improvised clarification answer in a practice simulation is not that
surface.

**🔴 2026-08-06 (session 13) · `generate_probe` FAILED LIVE WITH `json_validate_failed`, AND THE FIX
IS APPLIED BUT UNVERIFIED. THE `fast` DAILY BUDGET IS GONE.**

The probe loop's first live run: probes 1 and 2 succeeded, then **`json_validate_failed` twice in a
row at probe 3**, and the same test passed in isolation. Not a rate limit — a 400,
`invalid_request_error`, whose message reads *"Failed to validate JSON. Please adjust your prompt"*.
**The prompt is not the problem**, exactly as § Decisions 2026-08-04 records.

**The cause is a reasoning-budget error dressed as an output-budget decision.** `generate_probe` was
built with `max_tokens=1024`, reasoned from OUTPUT size: `Probe` is two short strings, smaller than
`ClarificationAnswer`'s three fields, so it should need less than that call's 2048. But `max_tokens`
on gpt-oss is a **reasoning-plus-output** budget — the model emits reasoning tokens against it
before the JSON starts — and **reasoning scales with the INPUT**, which for a probe grows with every
turn of the transcript. So the one call in the product whose input grows monotonically was given the
smallest ceiling. Raised to 2048.

**🔴 The fix is UNVERIFIED and must not be read as working.** The re-run failed all four tests in 63
seconds instead of 168, and the classification rule is the only reason that was not misread as the
fix failing:

```
grep -oiE "tokens per day|RateLimitError|Limit [0-9]+|Used [0-9]+"
   4  tokens per day        4  rate_limit_exceeded       10  RateLimitError
   4  Limit 200000          1  Used 198536 ... 198580
```

**`fast` is at 198,580 / 200,000.** Nothing else runs today. The window refills at roughly 138
tokens/min, so a full interview (~47,000) is about six hours away.

**🟢 2026-08-06 (session 13) · THE PROBE EDGE EXISTS. THE GRAPH ASKS ONE QUESTION AND PROBES IT.**

`decide_next -probe-> ask_probe -> await_candidate` is a real edge. `_QUESTIONS_THIS_PHASE` is 1,
`_PROBES_THIS_PHASE` is 8, the `followup_count == 0` assert is gone, and `followup_count` is the
loop's primary driver. **367 offline passed.** `await_candidate` still contains only `interrupt()`
and its return — verified by introspection, not by reading: zero `rest_insert`, one line above the
interrupt.

**The seam this story could most easily have got wrong is the message converter, and it is pinned.**
Graph state holds LangChain message OBJECTS (`.content`), `generate_probe` wants dicts keyed
`"text"`, and the DB rows key the same idea `"content"`. Three names for one thing. A converter
yielding empty strings would leave every probe responding to nothing **and the probe would still
read as plausible prose**, so nothing downstream would notice — the same shape as the 2026-08-04
upload bug, where a test certified the defect.

**And the first falsification of that converter passed vacuously**, which is worth more than the
test: `getattr(m, "text", "")` did *not* break it, because `langchain_core`'s `BaseMessage` now
exposes a `.text` accessor equal to `.content`. A dict-style read broke it properly. **This is
exactly why a test is watched failing rather than assumed capable of failing.**

**`improvised_facts` appends on `improvised_fact` being non-empty, never on `can_answer`** — the
live measurement above is what made that the rule. The reducer was falsified too: removed, the
accumulation test fails by silent replacement with no exception, exactly as ARCHITECTURE §4's trap
describes.

**🔴 `tests/test_transcript.py` is known-stale against this design** and its repair is part of the
owed live re-run: it drives a three-question fixture through a loop that now asks one.

**🟢 2026-08-06 (session 13) · THE PROBE RESPONDS TO THE ANSWER, THE IMPROVISED FACT REPEATS, AND
TWO DEFECTS SURFACED THAT ONLY A LIVE RUN COULD SEE.**

`generate_probe` and invent-and-record are built as pure functions. The graph half is still to come.
**356 offline passed.** The two properties that decide whether this design works cannot be tested
offline, so both were run live, on `fast`, for about 7 calls total.

**1. The probe is not `write_bridge` again.** Same method that killed `write_bridge` on 2026-08-05:
one question, four materially different answers, compare the probes. **4 of 4 distinct, each
quoting the candidate:**

```
sharp/segmented    "You said enterprises will buy on price and latency if frontier capability
                    converges. How does Anthropic's compute partnership with Amazon and Google
                    shape its ability to keep a price advantage?"
flat/stuck         "Which competitor do you think poses the biggest threat to Anthropic over the
                    next three years, and why?"
pushback           "You said compute contracts lock Anthropic into a cost structure it can't
                    escape when inference prices fall. What specific aspect of those contracts..."
very short         "You said compute costs are the biggest threat; can you elaborate on how the
                    compute partnership constraints with Amazon and Google might limit..."
```

The flat/stuck answer is the interesting one: with nothing specific to quote, the probe asks the
candidate to commit to something rather than reciting a canned line. That is the right behaviour and
it is the case `write_bridge` failed.

**2. The improvised fact repeated EXACTLY.** Asked for a figure the world does not state, then asked
again with the invention carried in `improvised_facts`:

```
ask 1   can_answer False   "Claude.ai has 5 million weekly active users."
        improvised_fact    'Claude.ai has 5 million weekly active users.'
ask 2   can_answer True    "Claude.ai has 5 million weekly active users."
        improvised_fact    ''   (nothing to re-record -- already in the list)
```

**`can_answer` drifted in meaning and the node must not key off it.** On the repeat it came back
True, which is defensible ("this rests on an established fact") but is not the documented "the world
states this". **`improvised_fact` being non-empty is the ONLY signal to append.** Keying the node
off `can_answer` would double-record on every repeat.

**🔴 DEFECT 1, and it is the third occurrence of the same lesson: `angle_used` exact-match failed in
3 of 4 live probes.** The prompt says copy the ladder angle "EXACTLY, character for character"; the
model dropped the trailing period three times out of four. Every near-miss fell through to the
positional fallback and resolved to the SAME dimension, which **collapses the probe ladder's rubric
coverage** — the thing Phase 4's Evaluator is supposed to read, and the thing "THREE DECISIONS" #3
moved onto the ladder in the first place. A green offline suite could not see this: its fixtures
copy the angle correctly, because a test author does.

Fixed in Python, not in the prompt: `_normalise_angle` matches on casefolded, whitespace-collapsed,
trailing-punctuation-stripped text. Narrow on purpose, with a **vacuity floor** — a genuinely
different ladder angle must still compare unequal, or normalisation would attribute probes to the
wrong dimension, which is worse than the fallback it replaces. Both the four near-miss cases and the
floor were **watched failing** against an identity `_normalise_angle`.

**🔴 DEFECT 2, NOT FIXED, Karthik's call: the invented figure was "5 million weekly active users".**
That is a fake round number, the exact register `contains_fake_round_number` exists to catch and
that CLAUDE.md § Design bans in generated content. The prompt asks for "the case world's own organic
decimal precision, even for an invented figure" and the model ignored it — **a prompted ban failing
for the fourth time in this project.** The deterministic fix is a Python post-check plus one retry
when the invented fact is fake-round, which costs a call only when it trips. **Not built:** it is
prompt-vs-Python scope inside a story that is already the largest in the phase, and the assertion
should be widened before anything changes, per the phase's own first trap.

**🔴 DEFECT 3, NOT FIXED, and it is the known one with new evidence: U+2011 reached candidate-facing
output.** The first probe smoke crashed on `UnicodeEncodeError: '‑'` — a non-breaking hyphen in
a live probe. This is the open defect the session-12 handoff describes (`no_dash_variants` catches 2
of 6 variants, `stripDashes` has the identical hole), and it is no longer hypothetical: it was
observed **in model output on a candidate-facing surface** on the first live probe ever generated.
The fix design in that handoff still stands, and probe text is a **new** model-output surface that
inherits no guard.

**🟢 2026-08-06 (session 13) · THE EIGHT REAL COMPANIES ARE LIVE IN THE GRAPH, AND THE GENERATIVE
CASE ARCHITECT IS OUT OF THE RUNTIME PATH.**

`generate_case_world` in `build.py` now calls `select_case_world`, not the LLM. Until this change
the eight fact sheets and `suits_categories` were **dead code in production** — everything 3.5.2 and
3.5.3 built was reachable only from tests, and a real interview still ran against an invented
company. The spec never assigned the wiring to a story; that omission was mine.

Three consequences worth having written down:

- **An interview costs one fewer LLM call.** World-building is now zero tokens and deterministic.
- **`suits_categories` is non-empty at runtime for the first time**, so 3.5.3's category scoping
  actually engages. Before today `select_category` always fell back to the full category list.
- **The generative Case Architect is kept, not deleted.** Its 7 golden cases and 47 assertion tests
  still run against it, and PHASE-3.5-SPEC §1 wants them pointed at the hand-written worlds as a
  positive control on the assertions themselves.

**Smoked against reality, which had never been done.** 3.5.3's PASS used the *fixture* world
"Ferngrove Media". Two `fast` Planner calls against two real sheets:

```
PM   Figma      → "How would you launch Figma Make for marketing teams?"        6 ladder entries
GPM  Anthropic  → "What is Anthropic's biggest threat over the next three years?" 5 ladder entries
```

No retry on either. That second one is Karthik's own example register, against a real company, out
of the machine.

**🔴 The live graph re-run is OWED and deliberately deferred.** The named trap says a `build.py`
change means re-running every live test file that builds a graph — `test_confirm_level.py`,
`test_conduct_loop.py`, `test_transcript.py`, 18 live tests, roughly 40 `fast` calls. The probe edge
reopens the same file inside the same story, so paying that twice buys nothing. **It is owed before
the 3.5 phase gate, not skipped.** The offline node coverage that stands in for it meanwhile is
three new tests in `test_curated_worlds.py`, **watched failing** against a generative-shaped world
(non-curated company name, empty `suits_categories`) rather than assumed.

**Two `test_confirm_level.py` monkeypatches had to move**, and one of them is the interesting kind
of hazard: they patched `app.graph.build._generate_case_world`, a name that no longer exists after
this change. Left alone they would have patched nothing and kept passing — the stub silently
stops being a stub. The single-call test now leaves the selector **real**, since deterministic
Python cannot log an LLM call, so its `== 1` still means exactly what it meant in story 1.4.

**🔴🔴 2026-08-06 (session 12) · KARTHIK'S EXAMPLES LANDED, AND THEY REVERSE THREE DECISIONS. PHASE
3.5 IS WRITTEN. GENERATED FICTIONAL WORLDS, THE REFUSAL BRANCH, AND MULTI-QUESTION INTERVIEWS ARE
ALL GOING.**

The examples session 11 deferred the prompt fix for:

> "Product interviews generally test Product strategy or product design aspects. Lets keep it to
> product strategy which can have sample questions like 'what is reddit's biggest threat', should
> samsung enter gaming, 'should apple make modular phones'. Some sub categories within product
> strategy are Got to market questions … or Pricing questions … or growth question … As you can see
> the questions are much more open ended"

**The diagnosis changed once they arrived, and the change is the point of having waited.** Session
11 read the defect as a Planner *prompt* problem. It is not. Every example is (a) about a **real
company**, (b) **short**, and (c) has **no statistic in it**. The decorative stat in 2 of 3 served
questions traces directly to [planner.py:80-82](../backend/app/agents/planner.py#L80-L82) — "cite a
competitor or a figure from metrics or market as well" — which exists only to satisfy the
genericness assertion in AGENT-PLANNER-SPEC §5. **The prompt was doing what it was told.** A prompt
edit would have fought the assertion behind it.

**Three reversals, all Karthik's, all deliberate.** Full detail in
[PHASE-3.5-SPEC.md](specs/PHASE-3.5-SPEC.md).

| Reversal | Cost | Why anyway |
|---|---|---|
| **8 curated REAL-company worlds replace generation** (Reddit, Duolingo, YouTube, Airbnb, Figma, Cursor, OpenAI, Anthropic) | The Case Architect drops to a selector | Candidate intuition is the actual complaint. Zero hallucinated facts, zero tokens per interview. Its 47 assertions now run against hand-written worlds, which AGENT-PLANNER-SPEC §5 already calls the better direction — a **positive control on the assertions themselves** |
| **The Interviewer MAY invent facts.** "The response need not be accurate or up to date" | **Deletes the strongest single result in the project** — the 2026-08-05 correct refusal, the only observation of ARCHITECTURE §9's undetectable failure mode not happening | A refusal reads as a broken interviewer. Real interviewers say "assume DAU is 50 million" |
| **ONE question, probed live.** `_QUESTIONS_THIS_PHASE` 3 → 1 | Reopens the graph; `decide_next` asserts `followup_count == 0` today ([build.py:652](../backend/app/graph/build.py#L652)) | 2-3 pre-written `probe_angles` cannot fill 45 minutes. Closes AGENT-PLANNER-SPEC §8's open question against the current design |

**🔴 The second reversal is implemented as INVENT-AND-RECORD, not invent-freely, and that distinction
is mine, not his.** The damage in improvisation is not invention, it is **self-contradiction**: 50M
at minute 8 and 20M at minute 30, which a candidate catches and which ends the illusion. So a new
append-only `improvised_facts` state field carries every invented fact into every later probe and
clarification. **`case_world` stays immutable and write-once** — the new list is a separate channel,
so ARCHITECTURE §2 survives intact. **The assertion that replaces the refusal assertion: an
improvised fact, asked for twice, returns the same value.** Mechanically checkable, and now the
property that matters. `ungrounded_figures` is retargeted at `case_world ∪ improvised_facts`, not
deleted.

**🔴 The structural fix, and why this is a bank rather than a better prompt.** Twelve question
shapes across four categories (strategy / gtm / pricing / growth) checked in as data. **No shape has
a slot for a market size or a growth rate**, so the decorative statistic becomes unsayable rather
than banned. **A prompted ban is not a ban** — the em-dash rule failed twice as prompt text and was
only fixed deterministically by `stripDashes` on 2026-08-05. Same lesson, applied ahead of the
failure this time instead of after it.

**🔴 Correction to this file: the `transcript_turns` defect is NOT schema-shaped.** It has been
recorded since session 10 as "a schema-shaped problem, not a prompt one." Wrong.
[0001_initial_schema.sql:46-54](../backend/migrations/0001_initial_schema.sql#L46-L54) already
declares `role` as `interviewer | candidate | system` and `kind` as
`question | followup | answer | clarify | meta`. **The DDL has always supported candidate turns.**
It is a missing write at [build.py:428](../backend/app/graph/build.py#L428), so it needs **no
migration** and carries no deploy-ordering risk. That makes it story 3.5.1 and cheap, where it had
been carried for two sessions as the expensive thing blocking Phase 4.

**🔴 The budget profile changes more than anything else in this phase.** A whole interview costs
roughly **one** `fast` call today (the transition is deterministic, the question is copied byte for
byte). After 3.5 it costs **one call per probe**, 6-10 of them, each carrying `case_world` plus a
transcript that grows every turn. Both ceilings have to be computed **before** the loop is built:
does the probe call still fit under **8,000 TPM at probe 10**, and at N tokens per interview **how
many interviews exist in a 200,000-token day?** If a full interview costs 30,000 `fast` tokens that
is six, and iterating on this phase competes with sitting it.

**🟢🔴 2026-08-06 (session 12) · STORY 3.5.3 DONE. THE PLANNER NO LONGER WRITES QUESTIONS, AND IT NO
LONGER NEEDS `deep`.**

The model now returns only **slot fills**, `grounded_in`, a **probe ladder**, and `intent`. **The
question string is built in Python** by `shape.template.format(**slots)`. That is the whole fix: a
model cannot staple a statistic onto a template that has no slot for one, however much it wants to.
Observed on the smoke:

```
QUESTION  What is Ferngrove Media's biggest threat over the next three years?
LADDER    6 entries, all five rubric dimensions covered
role      fast, PASS, retry_fired=False
offline   326 passed, 101 deselected
```

**🟢 The Planner runs on `fast` now, measured.** DEV-STATE has carried "the Planner needs `deep`"
since 2026-08-04. That was true of `QuestionPlan` — 5-7 objects of 7 fields, which `fast` failed
Groq's strict schema on twice. **It was never a fact about this agent's difficulty, only about its
output size**, and the output is now a fraction of what it was. Worth remembering as a general
lesson: a model requirement recorded against an agent may really be a requirement against a schema.

**🔴 Rubric coverage moved from questions to the probe ladder**, and `suits_categories` on each
curated world makes category choice **data rather than a model guess** — nothing can ask a pricing
question about Reddit's AI-licensing tension.

**🔴 TWO GAPS THIS STORY SURFACED THAT NO STORY OWNED. Both are now boxes on 3.5.4.**

1. **The curated worlds are NOT wired into the graph.** `generate_case_world` still calls the
   generative Case Architect, so all eight fact sheets and `select_case_world` are **dead code in
   production** and `suits_categories` is always empty at runtime. **The eight real companies are
   not live.** My spec never assigned the wiring to a story; that was my omission, not a subagent's.
2. **`_QUESTIONS_THIS_PHASE = 3` against a one-question plan is an `IndexError` waiting to fire.**
   Nothing catches it because **every graph-level test injects a static `question_plan` fixture**
   rather than driving the real Planner through the compiled graph. That hole in the tests is worth
   closing on its own merits.

**🔴 A THIRD DEFECT, IN SHARED INFRA, FOUND WHILE VERIFYING AND NOT YET FIXED.** A subagent reported
one dash variant slipping past `no_dash_variants`. Measured, it is **four of six**:

```
em U+2014  caught      non-breaking hyphen U+2011  PASSES
en U+2013  caught      figure dash U+2012          PASSES
                       horizontal bar U+2015       PASSES
                       minus U+2212                PASSES
```

**The frontend `stripDashes` has the identical hole** (`/[—–]/` only), so a U+2011 or U+2015 from a
model reaches a candidate through the interview surface. The assertion is **duplicated** in
`tests/golden/planner/assertions.py:141` and `tests/golden/interviewer/assertions.py:176`
(resume_analyst has no copy). This enforces a CLAUDE.md non-negotiable and is **open**; see
§ Next session for the treatment, which is not "replace them all with a comma" — U+2011 and U+2212
are hyphen-like and want ASCII normalisation, not an aside comma.

**🟢 STORIES 3.5.1 AND 3.5.2 ARE DONE, same day, at ZERO token cost.** See PHASE-3.5-SPEC.md for the
acceptance boxes and observed output. Three findings worth carrying:

**🔴 1. My own brief for 3.5.1 was wrong, and the subagent caught it.** The brief said to write the
candidate's answer in `ask_question`. `route_input`'s `answer` branch routes to **`decide_next`**, and
on the final question `decide_next` returns `exit` straight to `END`, so `ask_question` never runs
again — **the last answer of every interview would have had no row.** The exact gap the story exists
to close, reintroduced by its own fix. The write lives in `_decide_next_node` instead. **Asking a
subagent for contradictions is not a formality; this is the second time it has returned the most
valuable thing in the report.**

**🔴 2. Two brand-new assertions shipped green and near-useless.** Measured against variants written
after the fact:

```
is_recitation_shaped   1 of 6   fired only on the literal verb "support" next to "given"
decorative_statistic   2 of 6   missed customer counts, comma-grouped integers, bare ARR, churn %
```

All four misses are fields the curated worlds carry, so both checks would have reported green on the
same defect wearing a different figure. **The lesson is narrower than "verify subagents": a NEW
assertion needs its own counter-examples, written by someone other than its author, before it counts
as a gate.** Rewritten on the property rather than the phrasing — recitation is now "an explanatory
frame, no second person, no decision verb" — and both are 6 of 6.

**🔴 3. An allowlist disarmed a shared assertion, which is this project's signature failure.** Three
genuinely round real figures (`$100M`, `$10B`, `$3B`) were exempted **inside**
`is_round_dollar_amount`, so a **generated** world claiming `$100M` ARR passed the check whose entire
job is catching that. The Case Architect still generates and its golden suite still runs. Moved to a
per-field exemption map at the curated-worlds call site that asserts the violation was raised before
waiving it, plus a standing guard that fails if it leaks back.

**And the control that paid immediately.** Filling all thirteen bank shapes and running them through
their own three gates found one shape that could never be emitted without failing them
(`"...How does that change Duolingo's launch?"` reads as recitation). **The rule was right and the
shape was wrong.** It is now a checked-in test parametrized off `SHAPE_BANK`, so a shape added later
is covered without anyone remembering.

**🔴 The `as_of` dates are July to September 2025 and today is 2026-08-06** — the briefs are roughly
a year stale, worst for OpenAI, Anthropic and Cursor. Deliberately not backdated to look current;
`as_of` is shown to the candidate, so it is disclosed rather than hidden. **Rendering that line is
owed by story 3.5.5.** Karthik has the fact sheets for review and **3.5.3 must not read them until
he has signed off** — a wrong number here becomes a wrong number in an interview question.

**🟢🔴 2026-08-05 (session 11) · PHASE 3 GATE #4 IS CLOSED. THE FLOW WORKS. THE QUESTIONS ARE THE
PROBLEM, AND THAT IS A PLANNER ISSUE, NOT AN INTERVIEWER ISSUE.**

Karthik sat a real interview in the browser against the deployed stack and reported **the whole
flow working smoothly with no bugs.** That closes the gate this phase existed to reach.

**Scope of the pass, stated precisely: BOTH paths were exercised.** Three questions were served and
advanced through, **and Karthik asked clarifying questions** — including one whose answer was not in
`case_world`, **which the agent correctly refused rather than inventing.**

**🟢 That last observation is the most valuable single result of the session.** ARCHITECTURE §9
lists "the Interviewer improvises a fact `case_world` does not contain" as a failure mode with **no
runtime detection** — no assertion, no log line, nothing catches it in production. A human asking an
adversarial clarifying question is the *only* thing that ever could, and it was done, and **the
refusal branch fired.** That matches golden fixture `senior_pm_platform_world`, the one that smoked
PASS on `fast` with `retry_fired=True` on 2026-08-05.

**One observation is not a measurement.** This is a single sample of a generative branch on a
non-deterministic model, so it retires the risk far enough for a portfolio artifact and no further.
The three golden fixtures that have never run are still the cheap way to strengthen it if it ever
matters more.

**The real finding is question QUALITY.** The Interviewer is doing its job correctly — `ask_question`
copies `question_plan` byte for byte by design, so **every observation below is about the Planner's
prompt, `AGENT-PLANNER-SPEC.md`, not the Interviewer's.**

The three questions actually served, verbatim, as the evidence base:

```
Q1  At Nimbus Capital, how does the AI Risk Suite's current module mix support the company's
    revenue model given the $12.3B market size and the 31.4% ARR growth last year?

Q2  Considering Nimbus Capital's position in a market worth $12.3B, how does the competitive
    landscape with LendWise Analytics influence your go-to-market strategy for the AI Risk Suite?

Q3  Given Nimbus Capital's constraints, would you prioritize building the BehavioralRisk AI
    module, improve existing modules, or target SME lending, and why?
```

Two defects, one strength:

| Observation | Count | Detail |
|---|---|---|
| **Decorative statistic stapled to the front** | 2 of 3 | "given the $12.3B market size", "in a market worth $12.3B". The number does **no work** in the question and can be deleted without changing what is asked. Reads as the prompt reaching for `case_world` facts to make a question *feel* grounded |
| **Recitation-shaped, not judgment-shaped** | 1 of 3 | Q1's "how does X support Y given Z" can be answered by summarizing the case back. A candidate can sound fine without exercising product judgment, which makes it **weak signal for the Evaluator in Phase 4** |
| **Quality IMPROVES through the plan** | — | Q1 recitation + stat · Q2 judgment + stat · Q3 clean forced trade-off, no stat. The opener is the weakest slot, which suggests the later slots are better conditioned than the first |

Q3 is the shape to generalize from: a **forced trade-off between materially different kinds of bet**
(product expansion / quality / market expansion), impossible to answer by summarizing. Its one
weakness is "given Nimbus Capital's constraints" without naming them, so the candidate must invent
the constraint.

**Deliberately NOT fixed on 2026-08-05.** Karthik is bringing his own specific examples of what good
looks like before the prompt is touched, which is the right order: a prompt change driven by three
observations is a guess, and **the Planner runs on `deep`** so iterating on it is the expensive kind.
See § Next session.

**🔴 2026-08-05 (session 11) · THE EM-DASH BAN ON MODEL OUTPUT IS NOW DETERMINISTIC, NOT PROMPTED.
`stripDashes` runs at the frontend render boundary.**

Story 3.3's fifth acceptance box covers "anything rendered from model output", which **no static
check can ever see** — `test_user_facing_copy.py` walks the AST of `app/`, and a dash the Planner
or the Interviewer writes at runtime is not in any source file. The two prior attempts at this rule
were prompt lines, and **both failed**: the Planner still ships em-dashes into candidate-facing
questions (recorded as an open defect on 2026-08-04 and still open).

**A prompted ban is not a ban.** So the fix is `frontend/src/lib/copy.ts`'s `stripDashes`, applied
in `InterviewSurface.tsx` to every string that came from a model — the question text and the
clarification answer — and to nothing else. Rules, in order:

| Input | Output | Why |
|---|---|---|
| `2016–2019` | `2016 to 2019` | en-dash between digit runs is a range; a comma would be wrong |
| `scope — the surface you owned` | `scope, the surface you owned` | an aside; a comma is the nearest single character |
| `scope —.` | `scope.` | the inserted comma collapses into following punctuation |
| no dashes at all | byte-identical | asserted, so the guard cannot quietly rewrite clean text |

**It is deliberately NOT applied to this project's own source strings.** Those are covered by
review and by `test_user_facing_copy.py`; running a sanitizer over them would hide a rule violation
instead of surfacing it.

**This also closes session 9's open defect #1 from the candidate's side** — the Planner still
generates the dash, but it no longer reaches a candidate through the interview surface. **The
generation-side defect stays open**: a dash still lands in `question_plan` and in
`transcript_turns`, so anything Phase 4 renders from those rows needs the same treatment. Widening
the fix to the generation side is the cleaner end state and was not done here because story 3.3 is
frontend-only.

**Falsified, not inspected.** Removing `stripDashes` from the question render turns
`InterviewSurface.test.tsx`'s dash test red, observed.

**🔴 2026-08-05 (session 11) · THE CLARIFICATION BRANCH IS THE ONE PLACE THIS UI CAN SILENTLY LOSE
THE CANDIDATE'S PLACE, AND IT IS ASSERTED ON BOTH SIDES.**

`answer_clarification_node` does not advance `current_q_idx` and does not replace the question: the
candidate **still owes an answer to the original question**. A UI that swaps the question out for
the clarification answer therefore loses the question, and **state still looks entirely correct** —
the same shape as story 3.2's looping-interrupt bug, which also read fine from state.

So `useInterview` carries `question` forward unchanged on `next.kind === 'clarification'` and only
sets `clarification`; a `question` response does the opposite and **clears the stale clarification**,
which belonged to the question just left behind. Both directions are asserted, and both were
**falsified by deliberate mutation** (making the clarification branch replace the question turns 2
tests red, observed) rather than inspected.

**🔴🔴 2026-08-05 (session 10) · STORY 3.2 SHIPPED THREE LIVE TESTS THAT COULD NEVER PASS, AND THE
OFFLINE SUITE WAS GREEN THE ENTIRE TIME. The falsification was half-proven until they ran.**

The agent reported `14 passed, 3 deselected` on `test_conduct_loop.py` and treated the story as
verified. The 3 deselected were the `live` ones — **the only tests that observe the property the
whole phase exists to prove.** Run independently, all three died immediately:

```
KeyError: 'resume_text'
During task with name 'level_candidate'
3 failed, 14 deselected in 13.82s
```

**Not a rate limit** — classified first, per CLAUDE.md: no `tokens per day`, no `tokens per minute`
in the output. A genuine defect. The tests seeded `case_world` and `question_plan` straight into
`ainvoke`, but `build_graph`'s entry point is `level_candidate`, so every one of them started the
Resume Analyst and died on the missing `resume_text`.

**Why this mattered more than a normal broken test.** `falsify_looping_interrupt.py` only ever runs
the WRONG graph. Its "a correct 2-question loop would log exactly 2" is **reasoned, not observed** —
and the observation of the correct side lived entirely in these three dead tests. **So the phase's
central proof was half-complete and looked finished.** Fixed by seeding the checkpoint
`as_node="plan_interview"`, which resumes from the real `plan_interview -> ask_question` edge and
leaves the loop's own wiring under test. Both sides are now measured:

```
correct graph (live)   q1 = 0 calls, q2 = 1, q3 = 2, clarification = 3,
                       and STILL 3 after the real answer resumes   <- 3 passed in 30.20s
wrong graph (script)   1 -> 3 -> 4 where a correct loop logs 2     <- exit 0, FAILS as it must
```

**The standing lesson, third time in three sessions:** a subagent's green offline run says nothing
about the tests it did not execute. **Deselected is not passed.**

**2026-08-05 (session 10) · `fast` DOES hold `ClarificationAnswer`, closing spec §8's open question
with evidence.** `apm_consumer_world` passed with `retry_fired=False`;
`senior_pm_platform_world` (the refusal branch) passed with `retry_fired=True`, so the validate-retry
path is exercised and works. **Unlike the Planner, this agent needs no `deep`** — three fields is far
smaller than `QuestionPlan`, which is the distinction that mattered.

**2026-08-05 (session 10) · The chain is proven over REAL HTTP, and two script bugs were mine, not
the product's.** `backend/scripts/prove_interview_over_http.py` starts a real uvicorn subprocess and
speaks HTTP over a socket, per story 0.7's rule that a rebuilt `TestClient` shares the parent's
memory and therefore proves nothing. Observed:

```
POST /session -> /resume -> /level (Senior PM) -> /level/confirm (question 1, 282 chars)
  clarification consumed NO question slot
  3 questions asked, each over its own request
  done, interview over
```

Two failures on the way were the script's, and both are worth recording because neither was a
product defect: uvicorn dies at startup on Windows with `ProactorEventLoop` (psycopg refuses it;
Render is Linux and unaffected), and the reply route nests its payload under `next` with a `done`
flag rather than at the top level — reading the top level made the script over-post and 404. **The
route's shape is right; I read it wrong.**

**🟢🔴 2026-08-05 (session 10) · PHASE 1 GATE #4 IS CLOSED, AND ITS PREMISE WAS WRONG. THE LEVEL IS
THE CANDIDATE'S TO PICK; THE AGENT'S GUESS IS A DEFAULT, NOT A VERDICT.**

Gate #4 asked for "a real resume producing a level Karthik agrees with." **He declined the question
as posed, and the reasoning supersedes the gate:**

> "The level of seniority changes from company to company. In a service based company this level
> might be treated as more than senior level whereas in a product company it might be treated as PM
> or SPM, so let the user select the level on UI."

**That is correct and it makes the gate unsatisfiable as written.** No rubric can be right about a
title whose meaning is company-relative, so "did the agent get it right" is not a well-formed
question. The right property is **"can the candidate correct it, and does the correction drive the
interview."**

**The selector already exists** — story 1.6b built it. `ConfirmationScreen.tsx` renders all four
levels as a `radiogroup`, any of them is clickable, and the button switches to "Confirm corrected
level". No UI work was needed.

**🔴 But the half that actually matters was never asserted.** Three tests covered the correction and
none of them watched what the downstream agents were CALLED with:

```
test_command_resume_carries_the_candidates_level_into_state   -> reaches STATE
test_confirm_route_persists_a_correction_to_sessions_level    -> reaches sessions.level
build.py's node docstrings                                    -> a COMMENT, not an assertion
```

`test_a_corrected_level_reaches_the_case_architect_and_the_planner` now closes it, stubbing both
agents to capture the level they are handed. **Falsified, not assumed:**

```
broken (node passes a stale level):
  AssertionError: the Case Architect built a world for '__STALE_LEVEL__', but the
  candidate corrected their level to 'APM' (assessed was 'PM') -- the correction was discarded
```

**A note for whoever falsifies this next: the first attempt PASSED against a broken graph and that
was a coincidence, not vacuity.** The break hardcoded `"APM"` and `_a_different_level` happened to
choose `APM` that run. Use a sentinel that cannot collide with a real level.

**The years field IS wrong, and is recorded rather than chased.** Karthik: *"the CV clearly shows
that Product management experience starts from 2016, so it's 10 years."* The agent reported **8.0**
against a true **10**. Smaller than the 3.5-vs-15 error the prompt diet fixed on 2026-08-04, and it
no longer gates anything now that the level is candidate-selected, but **`years_pm_experience` is
still shown to the candidate and still feeds `level_rationale`.** Reference value for any future
re-gate: **10, PM from 2016.**

**🔴🔴 2026-08-05 (session 10) · STORY 3.2 BROKE THE MOST IMPORTANT TEST IN
`test_confirm_level.py` AND I COMMITTED IT BROKEN IN `08d8dba`.**

`test_resume_analyst_llm_call_fires_exactly_once_across_the_confirm_cycle` — the test that file's own
docstring calls THE load-bearing one — asserted `len(calls_after_resume) == 1`. Story 3.2 extended
the graph past `confirm_level` into `generate_case_world -> plan_interview`, so a resume now
legitimately logs three calls:

```
assert 3 == 1
  role=fast  (Resume Analyst)  role=fast  (Case Architect)  role=deep  (Planner)
```

**Undetected because this file's live tests were never re-run after story 3.2.** The subagent fixed
one stale assertion in this same file and missed this one; I verified its fix and did not think to
run the rest of the file. **That is "deselected is not passed" a second time, one commit later, and
this time it was mine.**

Fixed by stubbing the two downstream agents so the Resume Analyst is again the only thing in the
graph that can log a call, restoring `== 1` to meaning exactly what it meant in story 1.4.
**Loosening it to `== 3` would have been worse than useless** — it would pass just as happily if
`level_candidate` re-ran and the Planner did not.

**2026-08-05 (session 10) · `test_confirm_level.py` now paces for TPM, which it never did.** The
file went 2-failed/7-passed with both failures reading `tokens per minute (TPM): Limit 8000` —
classified as quota before being believed. Every live test here drives the Resume Analyst at ~3,800
tokens (read off the 429 body itself), so two inside one minute is 7,600 of 8,000. **The file was
always one test away from this and simply had fewer tests.** 35s autouse fixture, sized to a
measured refill of 133 tokens/sec, matching the three golden suites' precedent of pacing rather than
retrying.

**🔴🔴 2026-08-05 (session 10) · THE BRIDGE WAS AN LLM CALL THAT PRODUCED A CONSTANT. DELETED, on
Karthik's decision, and replaced with deterministic source strings.**

The live interview showed it repeating itself (*"Understood, thanks for sharing that approach. Let's
continue."* then *"Understood, thanks for sharing that. Let's continue."*). **The right question
turned out not to be "is this prose good" but "does this output vary with its input at all."** Six
materially different candidate answers, one `fast` call each:

```
strong+specific  -> "Got it, thanks for sharing that. Let's move on."
weak/vague       -> "Got it, let's move on."
refuses/stuck    -> "Thanks for sharing that. Let's continue."
disagrees        -> "Understood. Let's move on to the next topic."
very short       -> "Thanks for sharing that. Let's continue."
rambling         -> "Got it, thanks for sharing that. Let's continue."
```

**The same sentence six times with the words shuffled.** The candidate who said "I don't know, I've
never worked on a churn problem" got "Thanks for sharing that." The one who **challenged the
premise** — the single place a real interviewer visibly reacts — got a generic move-on.

Replaced by `_TRANSITIONS`, a rotating 4-tuple, and `transition_for(q_idx)`. **Three wins, and the
third is the one that matters:**

1. Zero tokens, zero added latency, on the one surface where a candidate watches a cursor.
   `ask_question` is now **fully deterministic** and the loop's cost is **flat in question count**.
2. Consecutive turns cannot repeat, because it rotates. Mechanically guaranteed, where prompting
   was not.
3. **The em-dash ban on this surface is now STATICALLY ENFORCED**, by
   `test_user_facing_copy.py::test_no_dashes_in_interview_transitions` — and the guard is
   **falsified, not assumed**: injecting an em-dash makes it go red, verified. Prompting had already
   failed twice on that exact rule, so this converts a prompt into a gate.

**Consequence worth carrying: `answer_clarification` is now the ONLY LLM call in the entire conduct
loop.** That is what the call-count assertions rest on, and it makes them sharper rather than
weaker — there is no longer any legitimate second call for a duplicate to hide behind. Expected
across a whole 3-question interview with one clarification: **exactly 1**.
`falsify_looping_interrupt.py` was rebuilt around `answer_clarification` for the same reason.

**The general rule this earns:** before spending an LLM call on a generative surface, run one varied
sample set and look at whether the output moves. If it does not, it is a constant, and CLAUDE.md
§ Style says write the constant.

**🔴 2026-08-05 (session 10) · ONE DEFECT RECORDED AND NOT CHASED: no candidate turn is written to
`transcript_turns`.** Only the Interviewer's own utterances get a row, so a completed interview
stores 3 questions and 1 clarification and **zero answers.** Phase 4's `answer_evaluations.turn_idx`
references `transcript_turns.idx`, so **Phase 4 cannot attach a score to an answer that has no row.**
A Phase 4 blocker found in Phase 3, which is the cheapest place to find it. **Decide it before Phase
4 starts, not during.**

**2026-08-05 (session 10) · A Pydantic `UserWarning` on every structured-output call is LIBRARY-LEVEL
and affects nothing this product persists.** `Expected 'none' but got 'BridgeLine'` traces to
`langchain_openai.chat_models.base._create_chat_result` calling `model_dump()` on the OpenAI SDK's
parsed response object. It therefore applies to **every** `with_structured_output` call in the
product, not just this agent, and was simply never scrutinised before. Nothing we checkpoint is a
model instance — the nodes extract `.bridge` and `.answer` as plain strings. Recorded, not chased.

**🔴 2026-08-05 (session 10) · THE INTERVIEWER DOES NOT REGENERATE THE PLANNED QUESTION. Python
emits it verbatim; the model only writes a bridge line. This diverges from ARCHITECTURE §3, which
draws `ask_question` as an Interviewer LLM call.**

The reason is not budget, though it saves budget. **The Planner's `question` string is the
most-tested string in the product** — it passed `missing_grounding`, `is_generic_question`,
`no_dash_variants`, `contains_fake_round_number` and `contains_banned_register_name` before it
reached state. **Regenerating it at runtime would void all five, on a surface no static test can
see.** A rewrite moves the question from the best-guarded string in the codebase to the worst.

So `ask_question` composes `[bridge] + [the Planner's string, byte for byte]`. The bridge is one or
two sentences, exists only to answer the Phase 3 gate's "form or interview?" question, and is
**starved of input on purpose: it receives the candidate's previous answer and nothing else.** No
`case_world`, no plan. It has no facts available to improvise with, which is cheaper than trusting
it not to. **Question 1 has nothing to acknowledge, so the first thing a candidate sees costs ZERO
LLM calls.**

Follows CLAUDE.md § Style directly ("prefer deterministic Python where the decision can be made from
state") and is the same instinct as open defect 1 in session 9's handoff, where prompting had
already failed twice to enforce a mechanical rule.

**Probing is explicitly NOT in Phase 3, and the reason is falsifiability.** PRD §7's criterion for
probes is "two runs with deliberately different answer quality produce visibly different probes" —
and answer quality is a **score**, which Phase 4 produces. A probe built now would fire on no signal
and its adaptivity would be unfalsifiable. `followup_count` stays `0` for all of Phase 3, and the
Planner's `probe_angles` go unused. **Expected, not a defect.**

**🔴 2026-08-05 (session 10) · `ungrounded_figures` WAS WRITTEN AS A SUBSTRING SEARCH AND WAS BLIND
TO EXACTLY THE FIGURES A MODEL INVENTS. Found by independent re-verification, before the agent that
would have been graded by it exists.**

The new figure check — this suite's teeth, and the one assertion the Planner has no equivalent of —
originally normalised the whole flattened `case_world` and substring-matched each figure from the
answer against it. Measured:

```
'about 62,000 subscribers'                    ungrounded=['62,000']   <- caught
'churn is 9.9%'                               ungrounded=['9.9%']     <- caught
'roughly 7 designers'                         ungrounded=[]           <- 🔴 PASSED
'we have 8 teams'                             ungrounded=[]           <- 🔴 PASSED
```

**A single digit is a substring of almost any world** (187 employees, $2.8B, 76.5%). So the check
was strongest against large distinctive figures, which a model has little reason to invent, and
blind to small integers, which it invents constantly. **That is backwards, and the hole sat directly
on top of fixture 3's premise** — that fixture asks a headcount question, which is precisely where
"about 7 designers" appears.

Fixed by extracting the world's figures with the same regex and comparing **whole tokens** rather
than substrings. Verified in both directions, which is the part that matters: `7` now fails, while
`187 employees` and `within 8 seconds` still pass against a world that states them, and `41,000`
written with a comma still matches a stored `41000`. Pinned by three new offline tests.

**Residual, accepted and recorded:** a coincidental collision still passes (an invented `8` against
a world that happens to say "8 seconds"). Same class of mechanical imprecision the Planner's
`is_generic_question` accepts, for the same stated reason.

**2026-08-05 (session 10) · A DEFENSIVE `getattr` WAS REMOVED FOR BEING WORSE THAN THE GAP IT HID.**

Spec §5's table originally read "no em-dash in `bridge` or `answer`" as though one call produced
both; §3 puts `bridge` on a separate schema from a separate call. The harness bridged the mismatch
with `getattr(result, "bridge", None)` and a truthiness guard — which **can only ever no-op**, since
`ClarificationAnswer` has no `bridge`. It reads as coverage while asserting nothing: story 1.3a's
bug wearing a different hat, in a suite written specifically to prevent it. Removed, the spec
corrected, and **the gap recorded instead: the bridge is a candidate-facing generative surface with
no dash guard until story 3.2 builds one.**

**🔴🔴 2026-08-04 (session 9) · THE UPLOAD SILENTLY NEVER STARTED THE RESUME ANALYST IN PRODUCTION.
A stale closure, in the seam between three individually-tested components.**

Karthik uploaded his CV to the fixed deployment. The upload succeeded, the new three-agent column
rendered, and **the Resume Analyst sat on "Waiting to start" forever.** No error in the browser, none
in the backend, because nothing failed. The handoff simply never happened:

```
1  candidate picks a file while `sessionId` is still null
2  UploadSurface's async handler captures onUploadComplete from THAT render,
   and App's `beginAssessment` useCallback([sessionId]) closed over null too
3  the upload creates the session and succeeds
4  it calls the CAPTURED callback -> `if (!sessionId) return`  <- silent
5  state stays `idle` -> App re-renders UploadSurface, showing "Resume received"
```

**The silent `return` is the actual defect**, not the closure. A no-op is indistinguishable from a
hang to the candidate, and it converted a race into an invisible dead end.

**Fixed by passing the id the resume was actually uploaded against** —
`onUploadComplete(sessionId)` -> `beginAssessment(uploadedSessionId)`. That removes the race rather
than narrowing it: the upload already knows its session, so nothing waits on a React state update.
The no-session path now sets an error state instead of returning.

**🔴 An existing test had encoded the defect AS INTENDED BEHAVIOUR** —
`levelAssessment.test.ts`'s *"starts idle and does nothing when there is no session yet"* asserted
`{kind: 'idle'}`. That is how this survived review, and it is the most useful thing in this entry:
a green suite was actively certifying the hang. Rewritten to assert the error state.

**Why nothing caught it: the defect lived in the SEAM.** `UploadSurface`, `useCandidateSession` and
`useLevelAssessment` were each correct and each individually tested. Only mounting them together,
starting from a null session, shows it. **`frontend/src/App.test.tsx` is new and exists for exactly
this**, and it is falsified, not assumed:

```
fix reverted   2 failed | 1 passed    "expected vi.fn() to be called at least once"
fix restored   84 passed (was 80)
```

**2026-08-04 (session 9) · `case_world` write-once is ENFORCED and FALSIFIED, closing 2.3's last box.**

It was previously enforced by nothing at all — `0001_initial_schema.sql` said as much in its own
words ("Nothing enforces that in the database; it is a graph-level invariant"), with no state guard
and no test either. `0003_case_world_write_once.sql` adds `unique (session_id)`, following the
precedent set by `transcript_turns` two tables up in the same file, for the same stated reason: a
re-running node must produce a conflict rather than a silent duplicate. These are generative agents,
so a second write would not duplicate the first, it would DISAGREE with it.

```
applying 0003_case_world_write_once.sql ... ok
case_worlds_session_id_key   CREATE UNIQUE INDEX ... ON public.case_worlds USING btree (session_id)
tests/test_case_world.py     3 passed
```

The rejection is watched, not inferred: the second insert raises `UniqueViolation` and the original
world is still the one in the table. Guarded against vacuity by a positive control (the first write
succeeds) and a per-session control (two sessions each get their own world, so a constraint on the
wrong column cannot pass).

**🔴🔴 2026-08-04 (session 9) · THE DEPLOYED PRODUCT HAS BEEN BROKEN SINCE 2026-07-31, AND THE FREE
TIER CANNOT LEVEL A REAL RESUME. Two separate defects, found by Karthik uploading his own CV.**

**Defect 1 — the deployed backend is four days stale, and a stale `.env.example` is why.** The
Netlify app returned `Not Found` on every upload. Measured directly against production:

```
curl .../openapi.json  ->  GET /health, POST /skeleton/start, POST /skeleton/resume
```

**Only Phase 0's routes.** No `/session`, so the frontend's first call 404s and the upload card
renders FastAPI's `Not Found` verbatim. `/health` still returns 200 because **Render keeps serving
the last healthy build when a deploy fails.** `origin/main` has had `/session` since 2026-07-31, so
that deploy fired and died at startup — almost certainly `ConfigError` on the GROQ_* vars, because
the Groq migration (`3644971`, 2026-07-31 18:34) renamed every model variable and **the Render
dashboard was never updated.** Exactly CLAUDE.md's named trap: *"Rename an env var → ... Render
dashboard"*.

`backend/.env.example` still led with a full `NVIDIA_*` block, four days after `config.py` stopped
naming any NVIDIA var. It was documentation for variables no code reads, and it is the most likely
reason the dashboard holds the wrong set. **Deleted 2026-08-04**, model ids filled in, and the
production `ALLOWED_ORIGINS` value noted inline. `git log -S` confirms `.env.example` was the only
non-archive file still defining them.

**Also: 28 commits were unpushed.** GitHub is behind local as well as Render being behind GitHub.

**✅ RESOLVED THE SAME DAY, and the three-layer picture is confirmed at every step:**

```
GitHub    was at af5e7b0 (31 Jul), 28 commits behind local
Netlify   BUILT af5e7b0 successfully  -> the stale UI Karthik screenshotted
Render    TRIED af5e7b0 and FAILED    -> kept serving a Phase 0 build
result    stale frontend called POST /session; Phase 0 backend had no such
          route -> FastAPI's "Not Found" rendered in the upload card
```

The last link is proven, not inferred: the exact string in the screenshot, `"Agent activity will
appear here once your resume is uploaded."`, exists in `af5e7b0`'s `OrchestrationColumn.tsx` and
nowhere in current `main`.

**Karthik fixed the Render env vars and redeployed. That redeploy is itself the proof the vars were
the cause** — Render only serves a build whose startup succeeded, and `POST /session` (absent from
the old build) appeared. `config.py`'s `REQUIRED_VARS` check passed in production, which is exactly
what had been failing for four days. Then 30 commits were pushed:

```
deploy live after ~80s
  GET  /health
  POST /session
  POST /session/{session_id}/level
  POST /session/{session_id}/level/confirm
  POST /session/{session_id}/resume
CORS   access-control-allow-origin: https://pmaiinterviewpanel.netlify.app
Netlify bundle contains "Interview Planner", "Case Architect", "Waiting to start";
        "Agent activity will appear" is GONE
```

**⬜ NOT VERIFIED: nobody has driven the actual repro.** The fix was confirmed at the API and bundle
level only. **A browser upload of a real PDF is still unexercised**, and the deployed path runs PDF
text extraction, which the local CV run bypassed by using pasted text. If extraction yields
materially different text the level may differ from the locally measured `Senior PM` / `8.0`.

**Standing lesson: `make test` and the golden suites cannot see any of this.** Every defect in this
entry lived between the repo and production, or in an input no fixture resembles. **A deploy check
belongs in the loop** — `curl .../openapi.json` costs nothing and would have caught it on 31 July.

**🔴 Defect 2, the worse one — A REAL RESUME DOES NOT FIT IN THE 8,000 TPM CEILING.**

```
Requested 8339, Limit 8000     Karthik's 3-page CV, max_tokens=4096
```

A 413, raised **before the model reads a word**. Groq computes
`Requested = prompt + input + max_tokens`, and solving from two observed 413s gives a **fixed cost
of ~3,015 tokens** — the 12,204-character system prompt PLUS the `ResumeAnalysis` JSON schema, which
strict structured output also sends. With `max_tokens=4096` that leaves **~890 tokens, about 3,000
characters, for the candidate's resume.**

**Lowering `max_tokens` does NOT work, and this is the non-obvious part: gpt-oss models emit
reasoning tokens that count against it before the JSON starts.** Measured in order on the same CV:
1,600 → `json_validate_failed` twice ("Failed to validate JSON"); 2,600 → again ("Failed to
**generate** JSON", the truncation wording); 4,096 → completes. **The reply reservation has a floor
far above the schema's own size**, so the only lever is the input.

Fixed by capping the resume at 3,000 characters at a line boundary (`_fit_to_budget`), which is
strictly better than the alternative — the 413 fails the request completely, whereas truncation
keeps the top of a reverse-chronological CV, where the level actually lives.

**🔴 IT RUNS NOW, AND THE RESULT IS STILL WRONG. Do not read this as fixed.** On Karthik's real CV:

```
assessed_level      Senior PM
years_pm_experience 3.5          <- he has 15 years; low_confidence flagged it
domains             insurance, fintech, healthcare      <- correct
company_contexts    large enterprise                    <- correct
```

**3.5 years is the truncation talking** — it is the Sun Life tenure, which is all that survives in
3,000 characters. A 15-year career is being levelled on its most recent role, and `Senior PM` is
arguably a level too low for the candidate. **Phase 1 gate #4 was never satisfiable**, and this is
why.

**🟢 THE PROMPT DIET WAS THEN DONE, on Karthik's call, and it worked.** ~3,015 of 8,000 tokens was
**38% of the per-request budget spent on our own instructions before the candidate was heard.**

```
prompt          12,204 -> 5,863 chars      52% cut
resume budget    3,000 -> 7,500 chars      a full 3-page CV, not a third of one
```

The bloat was diagnosable: **~40% of it was hedging inside `low_confidence_fields`**, plus a worked
example in the verbatim rules, all added to settle individual golden cases. **It was not buying
reliability** — three of eight cases flapped anyway. Every mechanically-checked constraint was kept:
verbatim quoting, the 8-word rationale citation, the dash ban, the protected-characteristic ban, the
no-rounding rule, and all five `low_confidence_fields` triggers.

**Same CV, before and after the diet:**

```
                      before        after
years_pm_experience   3.5           8.0
domains               3, generic    + HR-tech, previously truncated away
company_contexts      1             3 distinct
scope_evidence        Sun Life only Sun Life + AuthBridge + Aviva
assessed_level        Senior PM     Senior PM   (unchanged, and now defensible:
                                                 title "Senior AI Product Manager"
                                                 AGREES, so no flag is correct)
```

**Re-gated on the four STABLE golden cases, deliberately not the three flappers** — a failure on a
flapper cannot be distinguished from variance, so it carries no signal:

```
03_senior_pm_product_line, 04_gpm_portfolio, 07_duties_no_outcomes, 08_engineer_transition
4 passed, 4 warnings in 260.49s
```

**The compressed triggers still fire correctly**, which was the diet's real risk: case 08 flagged
`years_pm_experience`, case 07 flagged `assessed_level`, case 03 flagged nothing. **Cases 01, 02 and
05 were not re-run** and their flap status is unchanged and unmeasured against this prompt.

**Two quality defects also visible in the live output, recorded and NOT chased:**

- **The Planner shipped em-dashes into candidate-facing questions** (`"...startup—how would you"`),
  which its own prompt bans and its own golden `no_dash_variants` assertion would catch. The golden
  suite would have caught this; one smoked case did not.
- **The Case Architect produced round dollar figures** (`arr_usd "$150M"`, `"$50M AI innovation
  budget"`, `customer_count 500000`), which `is_round_dollar_amount` would flag. Same shape: real
  output violating a rule the suite already encodes.

Both argue the same thing: **one smoked golden case per agent is genuinely thinner than it looked.**
That is an accepted cost of the portfolio calibration, not a surprise, but these are the first
concrete examples of what it lets through.

**🔴 2026-08-04 (session 9) · `app/llm.py` NOW RETRIES GROQ'S 400 `json_validate_failed`. It never
did, and the docstring said it did.**

Groq validates structured output **server-side**, so a model emitting well-formed JSON of the wrong
shape never reaches pydantic — the SDK raises `openai.BadRequestError`, which hit the wrapper's
`except Exception` transport branch and was re-raised untouched. **The single class of failure this
wrapper exists to absorb was bypassing it**, on every agent, since Phase 0.

Detection is on the error body's `code`, with a substring fallback, deliberately **not** by catching
an openai-specific class — the same failure from a different client library would go unretried
again. Proven by the live before/after (`outcome=error` + raise, then `outcome=invalid` ->
`outcome=ok`), not by inspection. Three offline tests pin it, one of which is the boundary: **a 429
must still not be retried here.** Broadening the retry to swallow rate limits would be worse than
the original bug, since ARCHITECTURE §9 puts backoff at a different layer.

**🔴 2026-08-04 (session 9) · THE PLANNER RUNS ON `deep`. The portfolio calibration's "agents
default to `fast`" does NOT apply to this one agent, and this is correctness, not quality.**

Measured: `fast` (gpt-oss-20b) failed strict schema validation on `QuestionPlan` **twice in a row**
and raised `StructuredOutputError`; the retry ran correctly and both attempts still failed. One
observed failure mode was folding `grounded_in` into the preceding `probe_angles` array. `deep`
(gpt-oss-120b) produced a valid plan first try on all four subsequent runs, no retry.

`QuestionPlan` is the largest generation in the product — 5-7 objects of 7 fields, two of them
string arrays. **AGENT-PLANNER-SPEC §6 explicitly asked for this evidence**, noting the Planner was
a plausible `fast` candidate; it is not. `build.py`'s `planner_role` default is `deep`; the Case
Architect stays `fast` and passes there.

**Budget consequence:** the Planner costs ~6,000 `deep` tokens per run against a 200,000 daily cap,
so roughly 33 planning runs a day, shared with `level_candidate`.

**2026-08-04 (session 9) · The blind ACV check was conditioned on market, not relaxed.**

Spec §5 requires implied ACV to be plausible "for the stated stage **and market**"; the blind
implementation dropped the market half and used a flat $50 B2B floor. It rejected two consumer
worlds that were correct ($30.75 ARPU over 400,000 users; $3.91 over 3,200,000). `CaseWorld` has no
b2b/consumer field, so `customer_count` is the proxy — nobody sells to 3.2 million enterprise
accounts.

**Two bands, not one lowered floor**, and the distinction matters: ratcheting the single floor down
until the run goes green is precisely the "an over-strict check gets relaxed rather than fixed"
failure spec §5 names, and it would have destroyed the check for B2B where $50 is real signal. Both
original positive controls still fire. The prompt was updated to match, so the model and the check
now agree on what plausible means.

**2026-08-04 (session 9) · The Planner's genericness flap is ACCEPTED, on story 1.3's precedent.**

Across five `deep` runs the generic-question count went 5 -> 3 -> 1 -> 0 -> 1 as the prompt
tightened and the check stopped under-measuring. It settles at **6 of 7 questions compliant, a
different one slipping each run.** Two real fixes landed on the way (the check now accepts the
company's short form; the prompt now requires the company name in every question), so what remains
is generative variance, not a missing rule.

**Not chased further, deliberately** — a question that omits the company name still reads correctly
to a candidate and does not visibly break a demo, which is the portfolio calibration's stated bar.
**Reopens if:** it exceeds 2 of 7, or a Phase 3 interview visibly reads as generic.

**🔴 2026-08-02 (session 8) · THIS IS A PORTFOLIO ARTIFACT, NOT A PRODUCTION SYSTEM. VERIFICATION
DROPS TO SANITY LEVEL, AGENTS DEFAULT TO `fast`, AND THE BUILD TARGETS A THIN END-TO-END SLICE.
KARTHIK'S CALL, AND IT SUPERSEDES EVERY PHASE GATE AND ARCHITECTURE §4.**

The product exists to demonstrate multi-agent orchestration in a portfolio. It is not for daily
use. The verification regime built through sessions 1-8 was calibrated for production and is the
reason a single `make test` cost 108,000 tokens and the daily cap kept driving the schedule.

**The new standard, per phase:**

| Dropped | Kept |
|---|---|
| Full live suite as a gate (~120-130k) | **Offline suite** — ~150 tests, 4s, free |
| All 8 golden cases per agent (~32-60k) | **One golden case as a smoke** (~7k) |
| Alternating A/B to validate a prompt (~60k) | Read the output. Change it if it looks wrong |
| Flap attribution, Fisher's exact, control arms | Nothing. Variance is acceptable in a demo |
| Every acceptance box blocking the gate | **Gate = it runs end to end and looks right** |

Roughly 150k tokens per phase down to ~15k.

**The golden suites STAY. They are a portfolio asset, not overhead** — blind fixtures with positive
controls, and the story of an assertion that passed vacuously on all eight cases, is exactly the
evals discipline worth showing. They are written, committed, and free to run offline. **They simply
stop being a gate that blocks progress.**

**The tradeoff, stated once: a prompt change can now silently regress and surface during a demo.**
Accepted, because the walkthrough is scripted and the suites remain available when something looks
wrong.

**Two consequences that change the code, not just the process:**

1. **Agents default to `fast` (`openai/gpt-oss-20b`), not `deep`.** ARCHITECTURE §4's assignment is
   superseded. The buckets are independent so this roughly doubles usable budget, and `fast`
   measured 10/10 on structured output where `deep` was 7-9/10. Move an individual agent to `deep`
   only if its output visibly reads thin — the Case Architect's world and the Coach's report are
   the two a viewer actually reads, so they are the likeliest exceptions.
2. **The build targets a THIN END-TO-END SLICE.** Simplest working version of every remaining
   agent — a case world, 2-3 questions rather than a full 45-minute plan, a scorecard, a short
   coach note — so the whole pipeline is demoable. Deepen whichever part looks weakest afterwards.
   **Phase 2's remaining stories are re-cut accordingly; it no longer runs to its original gate.**

**What this does NOT relax:** never claim a pass that was not run, and classify a 429 before
calling it a defect. Those cost nothing and are why the numbers in this file can be trusted.

**2026-08-02 (session 8) · STORY 1.3 IS TICKED WITH THREE FLAPPING GOLDEN CASES CONSCIOUSLY
ACCEPTED. THE GOLDEN SUITE IS NOT A CLEAN GATE, AND THAT IS A DECISION.**

Karthik's call, taken with the full table in front of him. Cases 01, 02 and 05 flap on `deep`
against byte-identical input, in three unrelated modes. The alternatives considered and rejected
were: tiering the suite into strict and known-variable halves, redefining a pass as k-of-n
sampling, and continuing to chase each flap with 6-8 pair A/Bs.

**Why accepting is defensible rather than a shrug:**

- The three modes are unrelated, so there is no single edit to find, and case 01's fix already
  revealed a second mode behind the first.
- **Every flap is a variance failure, not a correctness failure a candidate would see.**
  `assessed_level` is schema-constrained and has never been violated in any measured run on either
  model. No quote has ever been fabricated except as a typography artefact. The uncertainty flag is
  over-eager, never silent — the safe direction for a confirmation UI, since the candidate is asked
  to check something that was already right.
- One validated prompt change costs 60,000-100,000 tokens against a 200,000/day/model ceiling, and
  the most recent such spend returned p ≈ 0.44.
- **Phase 2's Case Architect is the first independent signal on whether `deep` is the right model**,
  which is a more likely root cause than prompt prose. ARCHITECTURE §4's model assignment has been
  formally open since 2026-07-30 and neither model has been stable across days.

**THE COST, which is real: every future prompt change to this agent is unfalsifiable by a single
golden run.** A green run may be the flap and a red run may be the flap. Prompt changes to the
Resume Analyst must go through the alternating A/B at **6-8 pairs**, never through the suite alone.
**This does not relax CLAUDE.md's rule that golden cases pass before a prompt change is committed —
it changes what "pass" is measured by for this one agent.**

**WHAT REOPENS IT:** a flap moving `assessed_level` by more than one level · any fabricated quote
that is not a typography artefact · a case going red *consistently* rather than intermittently ·
Phase 2's Case Architect showing the same variance, which would make it a model problem.

**2026-08-02 (session 8) · `app/graph/skeleton.py` AND THE `/skeleton/*` ROUTES ARE PERMANENT TEST
INFRASTRUCTURE, NOT SCAFFOLDING. PHASE-1-SPEC § 1.7's DELETE LIST IS STRUCK IN PART.**

The spec assumed story 1.4's tests replace story 0.6/0.7's. They do not. `test_api.py` spawns **two
separate uvicorn OS processes** and proves a checkpoint written by the first is resumed by the
second; `test_confirm_level.py` runs its whole file against **one module-scoped `TestClient`**, and
`test_api.py`'s own docstring already explains why a rebuilt `TestClient` in the same process is
not a substitute — the interpreter never dies, so nothing is proven about state that must survive
one dying.

That property is the entire reason this project uses a Postgres checkpointer and forbids
`MemorySaver`. **Deleting the skeleton would have deleted the only evidence for it, and left a
fully green suite behind.** Karthik's call: keep it.

Consequences, so nobody re-litigates this:
- `skeleton.py`, `/skeleton/start`, `/skeleton/resume`, and the 7 surviving Phase 0 tests join
  `config.py`'s validation, the lifespan checkpointer, the CORS setup and `conftest.py` on the
  **do-not-delete** list.
- The 5 Phase 0 tests whose property 1.4 genuinely does assert were deleted, so the redundancy is
  gone without the proof going with it.
- **The debt is real and is deferred, not cancelled:** the cross-process proof covers the *skeleton*
  graph, not the real one. A later phase could change how the real graph checkpoints and this proof
  would not notice. Porting it onto 1.4's `/session/{id}/level` routes is the honest fix.

**The general lesson, which is the reusable part: a story that deletes tests must produce a
coverage map first — old test → the new test asserting the same property, or `UNREPLACED` — and
must stop rather than delete anything marked `UNREPLACED`.** The delete list in a spec was written
before the replacement existed and is a hypothesis about it, not a record of it. This was caught
only because the brief named it as a trap in advance.

**2026-08-02 (session 8) · AN ALTERNATING A/B AT 4 PAIRS IS UNDERPOWERED FOR A CASE THAT FLAPS
BELOW ~50%. SIZE THE PROBE TO THE FLAP RATE, NOT TO THE BUDGET.**

The case-05 attribution cost ~60,000 `deep` tokens — a third of the model's day — and returned
2 fail / 5 versus 0 fail / 4, which is Fisher's exact p ≈ 0.44. It answered the narrow question it
was aimed at (the `assessed_level` trigger still fires, 9 of 9) but could not attribute the level
flap either way.

Case 01's validation reached p ≈ 0.05 on the same 4 pairs **only because its control failed twice**,
which it could do because that case flaps ~50/50. Case 05 flaps less often, so the same spend buys
less power. **Budget 6-8 pairs for the next attribution on a sub-50% flap, or accept that the run
will be inconclusive and do not spend at all.** An inconclusive A/B is not a cheap result; it is a
third of a day.

Also recorded: **running the A/B with the arms inverted works but its exit line lies.** To test
whether a *committed* change caused a regression, the pre-fix prompt goes in the working tree, so
the script's `FIX` column is the OLD prompt and `CONTROL` is the committed one. The table stays
valid; `VALIDATED`/`NOT VALIDATED` must be ignored. Restore with
`git checkout -- backend/app/agents/resume_analyst.py` before doing anything else.

**2026-08-01 (session 7) · A PROMPT CHANGE AIMED AT A FLAPPING CASE IS VALIDATED BY AN
*ALTERNATING* A/B, NOT BY N CONSECUTIVE GREEN RUNS. This is now the method for this project.**

Session 6's plan, written into § Next session, was "run case 01 four times, then commit." That is
not enough, and the reason is the same one that produced this project's third false pass: **four
passes on a case that flaps ~50/50 is p = 0.06 by chance, and a green run says nothing unless the
same measurement was capable of coming out red.** Sequential arms cannot separate "the fix works"
from "the flap is not happening today."

**The method, as used and as it should be reused:**
1. Load the control prompt **byte-exact from `git show HEAD:<file>`**, never by reconstructing the
   pre-edit string by hand. String surgery measures your reconstruction, not the committed prompt.
2. **Alternate** control and fix, one call each, through the whole run, so serving drift over the
   hour hits both arms equally.
3. Run the **real per-case check** from `cases.py`, not just the one field you expect to move, or a
   regression elsewhere in the case passes unnoticed.
4. **Require the control to fail.** If it does not, the run measured nothing and the fix is
   unvalidated regardless of how clean the fix arm looks.

Result on case 01: FIX 6/6, CONTROL 2 pass / 2 fail, p ≈ 0.05. Committed as `27bb749`.

**The method is implemented as `backend/scripts/ab_prompt_control.py`** (session 7), which takes no
required arguments and **enforces rule 4 rather than leaving it to the reader: it returns exit 4
and prints INCONCLUSIVE if the control never failed**, instead of reporting a clean fix arm as a
pass. That is the exact shape of this project's two false passes.

```
backend/.venv/Scripts/python.exe backend/scripts/ab_prompt_control.py [case] [pairs] [role]
defaults: 01_apm_rotational 4 deep    = 8 calls, ~60k tokens, a third of a model's day
aborts if the working tree prompt is identical to HEAD (nothing to A/B)
```

**2026-08-01 (session 7) · KARTHIK'S CALL: A VALIDATED PROMPT FIX MAY BE COMMITTED WHILE THE GOLDEN
SUITE IS RED FOR AN UNRELATED REASON. Narrow exception, stated so it is not read as a general one.**

CLAUDE.md says golden cases must pass before a prompt change is committed. On this day the suite
**could not** be completed at all: `deep` hit 199,325/200,000 tokens with six cases unrun, and the
single genuine failure (case 02) is a pre-existing flap that `deep` passed on 2026-07-31 and that
`fast` passed 3/3 the same hour.

**The reasoning, which is what generalises.** The rule exists so prompt edits are not
unfalsifiable. This edit was falsified properly, against a control that could fail and did, which
is a *higher* bar than "the suite was green once". Meanwhile "anything you verified but did not
record is lost" is the project's other named failure mode, and the fix had already survived one
session uncommitted.

**The limits of the exception, and they are the point.** Story 1.3 was NOT ticked. The commit
message carries the full A/B table and names all three reasons it is insufficient. **This does not
license committing a prompt change whose own case is red, or one validated without a control.**

**2026-08-01 (session 7) · THE FLAP IS NOT ONE BUG IN ONE CASE. At least two of the eight golden
cases are unreliable on `deep`, and each has a distinct failure mode.** This supersedes session 6's
narrower framing of case 01 as the problem.

```
case 01   over-flags 'assessed_level'        -> FIXED and validated (27bb749)
case 01   over-flags 'years_pm_experience'   -> OPEN, untouched by that fix
case 02   lowercases a sentence-initial "C"  -> OPEN, flaps: FAIL on deep, 3/3 PASS on fast
```

**Why this matters more than either individual case:** the golden suite's job is to make prompt
changes falsifiable, and every flapping case removes one case's worth of that. The alternating-A/B
method above is the workaround, but it costs ~8 calls (~60k tokens, a third of a model's day) per
prompt change validated. **Budget prompt work accordingly, and expect to fix flaps before Phase 2
rather than carrying them.**

**2026-08-01 · KARTHIK'S CALL: FREE-TIER MODEL UNRELIABILITY IS AN OPERATING CONDITION, NOT A
BLOCKER TO SOLVE. Story 1.3 stays open, and work proceeds to 1.6b OUT OF THE PLANNED ORDER.**

His framing, and it is the right read: every session that touches the model side throws up a new
unexpected blocker, and the pattern is now established rather than newly discovered. Three sessions
running have each surfaced a different one — NVIDIA's structured-output ceiling, then the 200k/day
cap that is in no header, then run-to-run variance at `temperature=0`. Waiting for a clean model
day is not a plan.

**What this changes:** story 1.3 is NOT abandoned and NOT ticked. The prompt fix stays uncommitted
with its validation command in § Next session. It gets picked up on a fresh daily budget, when four
consecutive clean runs of case 01 on `deep` can actually be afforded.

**Why 1.6b rather than 1.4, which is the next story in the planned order.** 1.4 runs the Resume
Analyst inside `level_candidate`, so **its acceptance tests need model budget that does not exist
today** — including the one box that matters most, that the analyst's call fires exactly once
across the confirm cycle. Building it now would mean writing code that cannot be verified today,
which this project does not do. **1.6b needs zero model budget and is fully verifiable now**, and
it carries the riskiest unproven thing left in the phase (Realtime under the new RLS policies).

**The dependency this creates, stated so it is not discovered later.** 1.6b's confirmation screen
renders data that story 1.4 will produce. It is built against a TypeScript interface mirroring
`ResumeAnalysis` in `app/agents/resume_analyst.py` and driven by fixtures, with the submit path
left as a commented seam. **1.4 must wire that seam and is not free to change the shape casually.**
1.6b deliberately builds no backend route and no graph node.

**The measured budget position when this call was made**, so the next session does not re-derive it:

```
deep  Used 196,251 / 200,000   3,749 free, 7,565 needed per golden call
      "try again in 27m28s"  -> ROLLING window, not a midnight reset
      practical rate: about one golden call every ~28 minutes
```

**A probe that reported both models "AVAILABLE" was wrong and is worth not repeating.** It asked
for `max_tokens=4096` with a ten-token prompt, which fit the remaining headroom; a real golden call
requests ~7,565 and did not. **Size a budget probe to the request you actually intend to make**, or
it measures nothing.

**2026-08-01 · 🔴 PHASE-AFFECTING: `temperature=0` DOES NOT MAKE THESE MODELS DETERMINISTIC. THE
2026-07-31 ENTRY BELOW CLAIMING IT FIXED RUN-TO-RUN VARIANCE IS FALSIFIED. The golden suite is not
yet a regression gate, and every claim resting on "the suite passed" needs re-reading.**

`llm.py` sets `temperature=0` with this comment: "case 02 passed one run and failed the next on
identical input (observed 2026-07-31), which makes every future prompt change unfalsifiable." The
diagnosis was right and the fix does not achieve it. Golden case 01 on `deep`, identical input:
PASS, FAIL, PASS, FAIL across four observations, the failures carrying
`low_confidence_fields=['assessed_level']` on a resume where title and scope agree.

**Why, and it is structural rather than a Groq bug.** `gpt-oss-*` are mixture-of-experts models.
Temperature governs *sampling* from the output distribution; it does nothing about the
nondeterminism in the forward pass itself, where batched inference varies expert routing and
floating-point reduction order with whatever else is in the batch. A near-tie between two logits
resolves differently run to run. `temperature=0` narrows the problem to genuine boundary cases —
which is why 6 of 8 cases are stable — and cannot remove it.

**The consequence is the one that matters: a flapping case makes the suite unable to do its job.**
CLAUDE.md's rule is "golden cases must pass before any agent prompt change is committed." If a case
is a coin flip, a red result cannot be distinguished from a bad sample, and the rule degrades into
re-rolling until green. **This blocks ticking story 1.3**, and it is not specific to the Resume
Analyst — the Evaluator in Phase 4 scores against a rubric and will sit on the same boundaries.

**Karthik's call 2026-08-01: fix the prompt boundary rather than mask the variance.** Options
declined, with reasons, so this is not re-litigated: adding `seed=` freezes the coin flip without
fixing the borderline and hides a signal the suite was built to surface; accepting a known-flaky
case corrodes the gate; re-measuring on `fast` was already the cheap comparison and is recorded
above. **The flap is a real weakness at a decision boundary and the suite is correctly catching
it.** The fix is written and unvalidated; see § Next session.

**What is NOT yet decided, and should be decided with data, not now:** whether a residual flap
needs a best-of-N gate, and whether `seed=` is worth adding *in addition to* a prompt fix. Revisit
once the prompt fix has been measured on `deep`.

**2026-08-01 · The golden suite's pacing was recording rate limits as prompt failures, and the two
harness defects this session share a shape worth naming.**

`_PACE_SECONDS` was 30 against an 8000 TPM bucket while a single case grew to request ~7500 tokens,
needing ~56s of refill. Cases landing late in a run 429'd and were reported as failures. Separately,
`missing_verbatim_quotes` called a 42-word exact quote a fabrication over two typographic hyphens.

**Both defects made the harness lie in the same direction: they manufactured failures.** That is
the less-discussed half of test reliability in this project's history — 1.1 and 1.3a both found
assertions that passed vacuously, and the instinct built from those is to distrust green. These two
are the mirror image, and they are just as expensive: a red suite nobody can trust gets tuned
against, and the first thing tuned is usually the assertion rather than the code. **Read the failure
message before believing the label** is the operational rule; both were found that way and neither
was visible from the pass/fail counts.

**2026-07-31 · 🔴 PHASE-AFFECTING: `with_structured_output()` RETURNS `None` ONCE THE SYSTEM PROMPT
PASSES ROUGHLY 1500-2800 CHARACTERS. All three models. The schema is innocent. This invalidates the
"long detailed prompt + structured output" shape that ALL SIX agents are specified around.**

Story 1.3b's agent was correct and its golden run still failed every case with
`StructuredOutputError: ... failed schema validation twice: the response was empty`. Diagnosed by
isolating one variable at a time rather than by tuning the prompt:

```
CONTROL   Simple 2-field schema  + short prompt          -> OK      endpoint is healthy
          ResumeAnalysis (11 fields, nested) + short     -> OK      SCHEMA IS INNOCENT
          Simple 2-field schema  + full 5671-char prompt -> None    TRIVIAL schema still fails
          ResumeAnalysis + full prompt as ONE STRING     -> None    not the message format
          ResumeAnalysis + short system (repeat)         -> OK      stable, not a coin flip
```

**The bisect, which is the number to design against:**

```
system prompt @ 1500 chars -> OK
system prompt @ 2800 chars -> None
system prompt @ 4000 chars -> None
system prompt @ 5671 chars -> None      <- the real prompt
```

**Not model-specific.** `deep` and `fast` both fail, and `fast` measured **10/10** on structured
output in story 0.2 with a short prompt. The `backup` model (`openai/gpt-oss-20b`) fails too, twice,
on the full prompt. So this is the tool-calling path degrading as the instruction block grows, not a
Nemotron quality problem. It is consistent with this file's existing finding that nano leaks
reasoning preamble into `content`: a long instruction block appears to push the model into prose
instead of a tool call, and no tool call means LangChain returns `None`.

**The tension, stated plainly, because it is the actual problem:** the instruction budget this agent
needs in order to behave correctly is LARGER than the instruction budget structured output tolerates.
Shortening the prompt makes the call succeed and the output worthless. Measured on fixture 01, which
has one correct answer, with a 312-char prompt and every constraint moved into
`Field(description=...)`:

```
run 1  level=APM         scope_evidence PARAPHRASED, not verbatim
run 2  level=Senior PM   rationale is word salad: "the senior/responsibilities_resume and
                         autonomy_resume signals indicate..."
run 3  level=Senior PM   low_confidence_fields = ['leveling : 5', 'seniority : 4',
                         'promotion potential : high']    <- not schema field names at all
```

**Same input, three runs, two different levels.** For a levelling tool whose output shapes the whole
interview, that instability is disqualifying on its own, separately from the constraint violations.

Moving constraints into `Field(description=...)` **does** restore the call (the description travels
in the tool definition, not the instruction block) but did not restore adherence. It is a necessary
part of any fix, not a sufficient one.

**Consequence beyond story 1.3.** ARCHITECTURE §4 specifies the Case Architect, the Planner and the
Evaluator the same way: a long, rule-dense prompt returning a validated schema. **Every one of them
will hit this.** Whatever is chosen here should be chosen as the project's agent-call pattern, not
as a patch for the Resume Analyst. See Blockers for the open decision.

**2026-07-31 · STORY 1.3 SPLIT IN TWO so the golden suite cannot be tuned to the prompt. 1.3a
writes the fixtures and assertions blind; 1.3b must make them pass without editing either.**

The hazard is specific, not theoretical: an agent writing both the fixtures and the prompt in one
pass can adjust a fixture whenever the prompt misses, and the golden suite stops being falsifiable
at the exact moment it is supposed to start gating. Since these eight cases gate **every future
prompt change to this agent**, a suite tuned to the first prompt is worse than no suite.

So 1.3a delivered a suite that is **red on purpose** — it imports `app.agents.resume_analyst`,
which does not exist — and 1.3b's brief forbids editing a fixture or an assertion. If 1.3b believes
one is wrong it must stop and report, not weaken it. Same reasoning as holding story 1.1 until
anonymous sign-in was enabled: an agent facing a failing assertion tends to weaken it until green.

Cost of the split is one extra agent. It bought the vacuity finding above, which a single combined
agent would have had every incentive not to look for.

**2026-07-31 · STORY 1.6a: a new session row is created on EVERY upload attempt. Real defect,
deliberately deferred to 1.6b rather than patched here.**

`UploadSurface.handleFile` calls `createSession()` each time a file is chosen. A candidate who
uploads a resume the backend rejects (a scanned PDF, the most likely real rejection) and then
retries leaves an orphan `sessions` row behind, with no resume and no graph thread. Repeat retries,
repeat rows.

**Deferred, not ignored, because the fix belongs where the session lifecycle is actually decided.**
Story 1.4 gives a session a graph thread and 1.6b builds the confirmation screen on top of one
session id, so hoisting session creation now would be guessing at an interface that lands two
stories from now. Written into the 1.6b brief explicitly.

**Worth taking seriously despite being small**, because this project already has a recorded case of
orphan rows nobody collects: story 1.1 found 8 orphan checkpoint threads in production from story
0.8's manual curl probes, and the lesson there was that **test teardown cleans what tests create,
and nothing cleans what real usage leaves behind.** This is that same shape, reachable by a
candidate rather than by a developer.

**2026-07-31 · STORY 1.6a struck one of story 1.7's punch-list items early, and this is correct.**

1.7 lists "the Vite starter content in `App.tsx`" for deletion. Mounting the real shell is
incompatible with leaving the starter JSX in place, so 1.6a replaced it. The agent flagged this
rather than doing it silently. **`HealthCheck.tsx` is still mounted and still must not be deleted
until 1.6 is verified** — that is the item 1.7's ordering rule actually protects, since it is the
working reference for backend connectivity.

**2026-07-31 · LLM PORTABILITY, assessed against the code rather than assumed. A model swap is an
env var; a provider swap is about six lines in one file. Do NOT build a provider abstraction.**

Karthik asked how hard it would be to leave Nemotron later. Measured by grep, not estimated:

```
files importing ChatNVIDIA under backend/app :  1   (app/llm.py, line 20)
files referencing "nvidia" under backend/app  :  2   (app/llm.py, app/config.py)
agents importing a client directly            :  0
```

**The load-bearing design decision is that agents ask for a ROLE, not a model.** `get_llm("deep")`
resolves through `_MODEL_BY_ROLE`, which reads settings. Three tiers of switch follow:

| Switch | Cost |
|---|---|
| Different model, same NVIDIA endpoint | **Change an env var.** Zero code. Re-run golden cases |
| OpenAI-compatible provider (Groq, Together, Fireworks, OpenRouter, local vLLM) | Replace the `ChatNVIDIA(...)` constructor at `llm.py:239-243` with `ChatOpenAI(base_url=...)`. One file. Plus the env-var rename, which triggers the `backend/scripts/` grep rule |
| Anthropic / Gemini | Same single constructor swap — they are all LangChain `BaseChatModel`s with the same `invoke` / `with_structured_output` surface |

Roles resolve independently, so **mixed providers per role is already possible** with no change.

**What is not free, stated honestly.** Golden cases are the real switching cost and that is the
point — ~48 fixtures once all six agents exist, and re-running them is what makes a switch
falsifiable instead of "seems fine". The retry wrapper's justification is Nemotron-specific (it
exists because `deep` returns `None` rather than raising), so a provider with native strict schema
would make it near-dead code and every claim resting on the 7-9/10 figure would need re-measuring.
Prompts tuned around Nemotron's reasoning-preamble leak may not transfer. `reasoning_effort` is a
Nemotron-specific enum, currently used nowhere — keep it that way as long as possible. And two
constraints are provider-shaped rather than code-shaped: the 40 RPM ceiling, and free-tier-only.

**Decision: change nothing now.** There is no second caller for a provider abstraction, and the role
indirection already buys the flexibility. **The one rule to enforce in every future agent brief:
agents call `get_llm(role)` and never import a client or hardcode a model name.** That single rule
is the entire difference between a six-line switch and a six-file one. Cosmetic only:
`LoggingChatNVIDIA` and `llm.py`'s docstring are vendor-named, rename at swap time.

**2026-07-31 · STORY 1.2 DEVIATES FROM ARCHITECTURE §1: the resume is uploaded THROUGH Render, not
direct to Storage via a signed URL. Deliberate, and I think §1 is wrong here.**

ARCHITECTURE §1 says "Direct upload via signed URL. The file never touches Render — routing
multi-MB PDFs through a 512MB process is wasted compute." My story-1.2 brief specified a
backend-proxied `POST /session/{id}/resume` without noticing the conflict; the agent caught it and
flagged it, correctly.

**Kept, because §1's reasoning does not survive the no-text-layer requirement.** Acceptance for
this story is that a scanned PDF is *rejected*, and that decision needs `pypdf`, which runs on the
backend. With a direct browser upload the file lands in Storage first, Render must then download it
to extract text, and a rejected scan leaves an orphan object to clean up. **The bytes cross Render
either way — direct upload just adds a round trip and an orphan.** It would also require storage
write policies for the browser, which is new attack surface on a bucket that currently has none.

The compute argument is also small at real sizes: ARCHITECTURE's own estimate is ~200KB per resume
against Render's 512MB. The 5MB cap chosen here (no number was specified anywhere) is headroom, not
a real ceiling.

**Revisit only if resumes get large or uploads get frequent.** Neither is true at single-candidate
scale. ARCHITECTURE.md deliberately not edited, per the rule that decisions supersede it.

**2026-07-31 · STORY 1.2 SHIPPED THREE EM-DASHES INTO CANDIDATE-FACING COPY. Now fixed, and the
rule is a test instead of a hope.**

Found by grepping user-facing strings during re-verification, not by any test. All three were in
`resume.py`'s upload errors, including the scanned-PDF message a real candidate is most likely to
see:

```
"This PDF has no extractable text — it looks like a scanned or image-only document."
"Unable to read this PDF — the file may be corrupted."          (x2)
```

**The instructive part: the function's own docstring says "the message is written for the candidate
reading it, not a developer."** The author knew the strings were candidate-facing, and the em-dash
ban still did not survive contact. A rule that is stated in three documents and violated anyway is
a rule that needs a test.

`backend/tests/test_user_facing_copy.py` now AST-walks `backend/app/` and fails on an em-dash or
en-dash inside any `HTTPException(...)` or `*Error(...)` message. **Deliberately narrow** — it skips
docstrings and comments, which the rule exempts, and skips developer-facing exceptions
(`NotImplementedError`, `ConfigError`, `StructuredOutputError`) by name. It carries a
`test_the_check_finds_real_user_facing_strings` guard so an AST walk that silently matches nothing
cannot make the whole file vacuously green, and it was falsified by reintroducing an em-dash and
watching it fail.

**2026-07-31 · Full live suite duration swings between ~6 minutes and ~63 minutes. Same tests, same
code. Plan story 1.3 around this.**

Three measurements of the same suite today:

```
67 tests   382.61s  (0:06:22)     my run, story 1.1
85 tests  3765.07s  (1:02:45)     agent's run, story 1.2      <- 10x
tests/test_llm.py alone: 481.98s (0:08:01) vs a 335.27s baseline recorded 2026-07-30
```

The story-1.2 tests account for ~40s of that hour. **This is NVIDIA free-tier contention**, and it
is consistent with DEV-STATE's earlier finding that `deep`'s median moved between 9.2s and 20.4s
inside ninety minutes. Nothing is wrong with the code.

**Consequence for story 1.3, which is the next story and the heaviest LLM consumer in the phase:**
eight golden cases across two models is at minimum sixteen structured calls per full run, and
"run it enough times to observe a retry" multiplies that. At the bad end of this range that is
hours, not minutes. Budget for it, run golden cases as their own target rather than inside the
full suite, and **do not read a slow run as a broken agent.**

**2026-07-31 · STORY 1.1: an unauthorised UPDATE or DELETE through PostgREST returns HTTP 200, not
403. Assert on the DATABASE, never on the status code.** This is the CORS trap of 2026-07-30
wearing different clothes, and it will silently encode a false pass in Phase 3 if forgotten.

With no UPDATE/DELETE policy, RLS makes the `USING` clause match zero rows, so the statement
succeeds against nothing. PostgREST reports that as success. Observed, with ground truth read back
through the service role after each call:

```
A PATCH  Bs session   -> status 200, body=[]
  GROUND TRUTH -> session=ORIGINAL  turns=1
A DELETE Bs turns     -> status 200, body=[]
  GROUND TRUTH -> session=ORIGINAL  turns=1
A DELETE Bs session   -> status 200, body=[]
  GROUND TRUTH -> session=ORIGINAL  turns=1
```

**B survived completely unchanged.** The empty `body=[]` is the real signal, since `Prefer:
return=representation` returns the affected rows and there were none. A test asserting
`status != 200` on these would fail against correct code and invite someone to "fix" working
security. Two calls DO return 403 and are worth knowing as the contrast: inserting into a table
with no INSERT policy, and creating a session owned by another uid (`42501`, the `with check`
firing).

**2026-07-31 · STORY 1.1: 8 orphan checkpoint threads / 32 rows found in production. NOT a test
regression — they are story 0.8's manual curl probes, and nothing was ever going to clean them.**

Found while checking residue after the full suite. Story 0.7 recorded `(0, 0)` before and after a
full run, so this looked like a regression at first. It is not: **two of the eight thread_ids
appear verbatim in this file's own story 0.8 output** — `23caf429-...` was the phase-gate curl and
`83a73411-...` was the full-chain probe, both driven by hand against the deployed Render URL. The
0.7 measurement predates them.

**The gap is structural, not a bug: test teardown cleans what tests create, and manual production
probes are not tests.** Cleared (32 checkpoints, 32 blobs, 80 writes), `checkpoint_migrations` left
intact as always. Worth remembering before any demo — hand-driving the deployed service leaves
state that nothing collects.

**2026-07-31 · STORY 1.5: `strokeWidth 1.5` is NOT implementable in Phosphor. It has no such prop.
CLAUDE.md and ARCHITECTURE §8 both specify something the mandated library cannot do.**

The agent contradicted its brief here and was right. Verified independently rather than taken on
its word:

```
grep -rl 'strokeWidth' node_modules/@phosphor-icons/react/dist/   ->  no matches, anywhere
IconContext accepted props                                       ->  color?  size?  weight?  mirrored?
icon geometry                                                    ->  filled <path d="..."/>, viewBox "0 0 256 256"
```

Phosphor icons are **filled path geometry, not stroked paths** — the weight is drawn into the
outline, so there is nothing for a stroke width to apply to. `strokeWidth` is `lucide-react`'s API,
and lucide is the library three separate skills tell us not to use. The instruction was written by
analogy to the library we deliberately rejected.

**Resolved as `weight: "regular"` set globally through `IconContext`**, in
`frontend/src/lib/icons.tsx`. Phosphor documents `regular` as its 1.5px-stroke-at-24px-viewBox
weight, which is consistent with the 256 viewBox (16/256 × 24 = 1.5) and is the faithful reading of
the intent. **CLAUDE.md § Design updated**; ARCHITECTURE §8 deliberately left alone, per the rule
that decisions supersede it rather than rewriting its history.

**2026-07-31 · STORY 1.5: `ease-standard` is a working utility and `duration-standard` is not.
Tailwind v4 has no `--duration-*` theme namespace, and the failure is silent.**

Found by re-verification, not by the agent. `--ease-*` is a real v4 theme namespace so
`ease-standard` emits; the duration utility takes a bare number (`duration-150`), so a token named
`--duration-standard` generates **no class at all**. An element written `duration-standard` gets no
transition duration and no error — it just does not animate.

The tokens are emitted as custom properties and are usable, through a different syntax:

```
--duration-fast:.15s   --duration-standard:.18s              <- present in the built CSS
.duration-\(--duration-standard\){transition-duration:var(--duration-standard)}   <- works
.duration-standard                                            <- never generated
```

**Use `duration-(--duration-standard)`, never the bare form.** Documented in `index.css` at the
token, and guarded by a test that greps all of `frontend/src` — it will fail story 1.6 if anyone
writes the bare form.

**That guard was falsified in three directions before being trusted**, per the story 0.6 precedent:
it passes clean at 25, fails with `['__bad.tsx']` against a planted bare `duration-standard`, and
stays green against the correct `duration-(--duration-standard)` form. Its first two drafts were
both wrong in the same way the agent's own tests had been — `\bduration-fast\b` matches inside the
declaration `--duration-fast`, and a comment explaining the ban tripped the ban. **A regex needs a
`(?<!-)` lookbehind here, and comments must be stripped before matching.** Third time was correct.

**2026-07-31 · Phase 1 delegation shape, and three calls made before any code was written.**

Wave plan: **1.1 + 1.5 in parallel** (disjoint: backend SQL and tests vs frontend CSS and fonts),
then **1.2 + 1.3**, then **1.4**, then **1.6**, then **1.7 inline**. Two constraints shaped it.
`frontend/package.json` is a collision point — 1.1 would want `@supabase/supabase-js` while 1.5
wants Geist and Phosphor, so **the browser Supabase client was moved into story 1.6** and 1.1 is
backend-and-SQL only. And **no two agents run live LLM tests concurrently**: the 40 RPM ceiling is
shared, and 1.3's golden cases are the heaviest consumer in the phase.

**Karthik's call: `DESIGN.md` is generated via the `stitch-design-taste` skill**, not hand-written,
and lives at the repo root rather than in `docs/`. Every later phase's UI is built against it.
Where the skill's output conflicts with ARCHITECTURE §8, **§8 wins** and the conflict gets recorded.

**Karthik's call: the interviewer persona name is deferred to Phase 3, so story 1.6 ships NO
persona header.** "Maya Chen" sits in the register v1 §7 bans and the architecture wireframes are
riddled with it, so the constraint is written into the 1.6 brief explicitly rather than left to be
noticed. Deferring costs nothing here — Phase 1 has no interviewer.

**Orchestration call, not in the spec: vitest is installed in story 1.5, not 1.6.** The spec's test
table says only "this phase installs it" without assigning a story. Putting it in the foundation
means `make test` stops failing on its `test-web` leg a story earlier, and 1.6 gets a working
runner instead of having to build one. Its first test is a real guard rather than a smoke test: it
reads `index.css` and asserts every §8 token value, no serif family, and no `lucide-react`.

**2026-07-30 · STORY 0.7: the Windows event-loop guard in `app/main.py` does NOT do what the
2026-07-30 entry below implies. `--reload` is what makes `make dev-api` work.**

The earlier entry says the swap is "needed anywhere `AsyncPostgresSaver` is used locally" and that
stories 0.6 and 0.7 would hit it "when the graph is wired into FastAPI". Both true. What was
wrong was the implied fix: a guarded swap at the top of `app/main.py` does not rescue
`uvicorn app.main:app`. Reproduced directly:

```
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8011
  psycopg.InterfaceError: Psycopg cannot use the 'ProactorEventLoop' to run in async mode.
  ERROR:    Application startup failed. Exiting.

make dev-api  (uvicorn app.main:app --reload)
  POST /skeleton/start HTTP/1.1" 200 OK
```

**Why:** uvicorn's `Server.run()` calls `asyncio.run()`, which creates the loop under whatever
policy is active **before `app.main` is imported**. The guard therefore executes inside a
coroutine on a loop that already exists — too late. `--reload` works by a different mechanism
entirely: it spawns a child process and runs uvicorn's own `asyncio_setup()` there, before the
child's `asyncio.run()`. Nothing in `app/main.py` participates.

**The guard is kept** because `app.main` is also imported directly, outside uvicorn's CLI, where
it runs before any loop exists — and it is harmless otherwise. **It is not load-bearing, and the
comment above it now says so.** `tests/test_api.py` launches its subprocesses as
`python -c "<set policy>; import uvicorn; uvicorn.run(...)"` for the same reason.

**Production is unaffected:** Render is Linux, where the selector loop is already the default, so
a plain `uvicorn app.main:app` start command in story 0.8 is fine. The trap is local only, and it
is the *developer* who hits it.

**2026-07-30 · STORY 0.6: the interrupt rule is real, but the reason written in the spec was
wrong. Breaking it duplicates SIDE EFFECTS, not state — so no state assertion can detect it.**

The idempotency test was falsified before being trusted. A deliberately wrong graph, with the LLM
call and the increment above `interrupt()` in one node, was driven through a full pause-and-resume
against the same `app.llm` call log:

```
llm calls at pause      : 1
llm calls after resume  : 2      <- the rule is load-bearing, confirmed
turn_count after resume : 1      <- NOT 2, which is the surprise
```

Two calls, so the assertion in `test_interrupt.py` genuinely discriminates rather than passing
because everything passes. **But `turn_count` stayed at 1.** LangGraph discards the state writes
of a node that interrupted and applies them only on the run that completes, so the double
execution is invisible in state.

**This changes what to guard against.** The cost of breaking the rule is not a corrupted counter,
which is what PHASE-0-SPEC implied and what I would have asserted on. It is duplicated *side
effects*: a burned LLM call against the 40 RPM ceiling, a doubled row in `transcript_turns`, a
doubled `agent_events` emission driving the UI's realtime rail, a doubled Supabase write. Those
all escape the graph, so nothing rolls them back.

**Consequence for Phase 3 and anything writing outside graph state:** a test that checks state
after a resume proves nothing about this. Assert on the call log or on row counts in the table
being written. The one-assertion version is what `test_interrupt.py` does.

**2026-07-30 · Story 0.5 broke two of story 0.4's tests, and only running the FULL suite caught
it. Worth changing how phases are handed over.**

`test_schema.py` asserted set equality on `pg_tables where schemaname='public'` against the six
app tables. Correct in 0.4. Then 0.5 ran `init_db.py`, LangGraph created four tables **in the
same schema**, and both assertions failed.

**Why it nearly shipped:** each agent verified only the file it wrote. The checkpointer work ran
`test_checkpointer.py` and `-m "not live"`, both green, and never ran `test_schema.py`. The
regression sat in a file nobody had reason to re-run.

**Rule, now in CLAUDE.md § What to update:** a story that creates database objects, or changes
anything shared, must run the **entire** live suite before handover, not just its own file. The
offline suite is not sufficient — it stayed green at 21 passed throughout.

The fix made the RLS test **stronger** rather than merely accommodating: it now asserts RLS on
every table in `public`, including tables we did not create, so a future LangGraph version adding
an unprotected table fails the suite. The table-set test still rejects unexpected tables; it just
permits the `checkpoint%` family.

**2026-07-30 · Checkpoint cost measured. One earlier claim of mine confirmed, one refuted, and
the headline latency number is NOT the production one.**

Earlier this session I argued against keeping interview state in Render's memory, and made two
claims from reasoning rather than measurement. Both are now tested, with a 20-turn graph carrying
an ~8KB immutable `case_world` plus a transcript that grows every turn.

**Confirmed — LangGraph versions blobs per channel; unchanged channels are not rewritten:**

```
channel                 rows       bytes
messages                  40     535,908
__start__                 20      14,761
case_world                 1       8,273     <- written ONCE across 20 turns
```

So withdrawing the proposed `case_world_id`-in-state optimisation was correct: it would have
added indirection for nothing. **`messages` is the real cost driver** — 40 rows and 536KB from
roughly 26KB of actual content, because the whole accumulated list is re-serialised each turn.
Quadratic in turn count, as predicted.

**Total 0.58 MB per 20-turn interview → about 869 interviews before Supabase's 500MB free cap.**
Comfortable, but not unlimited, and it is the checkpoints that fill it rather than the app tables.

**Refuted, and I want this stated plainly: my "~1% of turn latency" estimate was unverified and
the measurement does not support it.** Observed **~298ms per checkpoint**, roughly 60x the ~5ms
I asserted for an intra-region round trip.

**But that number is not the production path either.** It was measured from a Windows dev machine
in India to Supabase in Singapore, so it is dominated by home-internet latency. Render in
Singapore to Supabase in Singapore is the real path and remains **unmeasured**. Do not quote
either 298ms or 1% as fact. **Story 0.8 must re-measure from the deployed service** — that is the
first time the real number is obtainable.

**2026-07-30 · STORY 0.5 SECURITY: LangGraph creates its checkpoint tables WITHOUT RLS. Fixed
in `init_db.py`. This was the worst exposure found so far.**

`.setup()` created `checkpoints`, `checkpoint_writes`, `checkpoint_blobs`, and
`checkpoint_migrations` in `public` with `rowsecurity = false`. Supabase exposes `public` through
the Data API and grants `anon`/`authenticated` full DML there by default. Measured before the
fix — `set role anon; select count(*) from checkpoints` **succeeded**, and anon also held
`INSERT`, `UPDATE`, `DELETE`, and `TRUNCATE`.

**Checkpoints contain the entire interview state**: resume text, full transcript, every
evaluation. So this was simultaneously a complete read exposure and a route to truncating the
table and destroying every in-progress interview.

Note the spec says three checkpoint tables. **There are four** — `checkpoint_migrations` is
LangGraph's internal version tracking. Never delete its rows; that would make `.setup()` replay
its migrations.

Secured inside `init_db.py` immediately after `.setup()`, not as a migration, because ordering
would otherwise be a trap: `migrate.py` can run before these tables exist, silently no-op, and
leave them unprotected forever. The statement pattern-matches `checkpoint%` rather than
hardcoding names, so a table added by a future LangGraph version is covered instead of quietly
missed. Verified after the fix — service role sees 3 rows, anon and authenticated see 0, and the
graph still runs because the pooler role has `rolbypassrls = true`.

**2026-07-30 · The transaction pooler fails ONLY under concurrency, which makes it far more
dangerous than "it errors".**

Story 0.5 asks for the `DuplicatePreparedStatement` text on record. Getting it took three
attempts, and the failures are the finding:

```
sequential, 1 connection, prepare_threshold=1, 60 round trips on 6543
  -> no error at all

12 concurrent connections x 25 prepared round trips on 6543
  -> ok=11/12
  -> psycopg.errors.DuplicatePreparedStatement: prepared statement "_pg3_0" already exists

AsyncPostgresSaver driving a real graph on 6543
  -> psycopg.errors.DuplicatePreparedStatement: prepared statement "_pg3_0" already exists
```

**A developer testing locally on 6543 would see it work perfectly.** One connection doing
sequential transactions never collides, and even under concurrency only 1 of 12 workers failed.
It breaks in production, intermittently, under load — the worst possible failure shape. The
port-5432 rule is not superstition inherited from old pgbouncer advice; it is measured here.

`config.py` rejects 6543 before connecting, so reproducing this requires building the URL
directly rather than going through `settings`.

**2026-07-30 · Windows dev machines need a non-default asyncio event loop. Local only.**
psycopg's async mode refuses Windows' default ProactorEventLoop:

```
psycopg.InterfaceError: Psycopg cannot use the 'ProactorEventLoop' to run in async mode.
```

Fix, guarded by platform, needed anywhere `AsyncPostgresSaver` is used locally:

```python
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

**Render runs Linux, where the selector loop is already the default, so this is invisible in
production.** It is in `init_db.py` and the checkpointer tests. **Stories 0.6 and 0.7 will hit it
again** when the graph is wired into FastAPI — uvicorn on Windows selects the proactor loop
unless told otherwise.

**2026-07-30 · STORY 0.4 RLS: the spec's own acceptance box was self-contradictory. Resolved by
adopting Supabase anonymous sign-in in Phase 1; Phase 0 ships zero policies.**

PHASE-0-SPEC asked for "RLS enabled on every table with permissive `session_id`-scoped
policies." **Those two halves cannot both be true.** Scoping rows by `session_id` requires the
database to know which session the caller owns, which comes from an auth token. V1 has no login,
`sessions.user_id` is nullable, so there is no claim to scope by. The only literal reading is
`using (true)` for `anon` — and the publishable key ships inside the browser bundle by design,
so that makes **every candidate's transcript and scores readable by anyone who opens devtools**.
Not obscurity: no UUID guessing needed, the whole table is selectable.

**Karthik's call: Supabase anonymous sign-in, wired in Phase 1.** The browser silently obtains a
real identity token, no signup screen, the candidate notices nothing, and `auth.uid()` then makes
genuinely scoped policies possible. `sessions.user_id` already exists and is nullable, so the
schema needs no change to support it.

**Phase 0 therefore ships RLS enabled with ZERO policies, deliberately.** RLS with no policies
denies every role that does not bypass it. The backend uses the service key and is unaffected;
browsers get nothing. Correct posture while the frontend is still a Vite placeholder.

**A trap worth recording, because reasoning about it gives the wrong answer.** `anon` and
`authenticated` **do** hold table-level `SELECT`/`INSERT`/`UPDATE`/`DELETE` grants on all six
tables — Supabase adds those by default in `public`. Grants control whether the table is
*reachable*; RLS controls which *rows* come back. I initially recorded "browsers can reach
nothing" from the grant query, which was wrong. Verified empirically instead:

```
as service role : 1 row(s) visible
as anon         : 0 row(s) visible   <- RLS denies despite the SELECT grant
as authenticated: 0 row(s) visible
```

The consequence for Phase 1: adding a policy is what opens the door, and the grants are already
open behind it. A single over-broad policy exposes everything immediately. `test_schema.py`
asserts the empirical denial rather than merely that `rowsecurity = true`, so an accidentally
permissive policy fails the suite.

**2026-07-30 · STORY 0.2 DECISION GATE: structured output is 7/10 on `deep`. Validate-retry is
now mandatory, and it is enforced in the wrapper rather than left to each agent.**

Measured through `ChatNVIDIA`, N=10 per cell, same schema and prompt throughout:

| Model | `with_structured_output` | `bind(response_format=json_schema)` |
|---|---|---|
| `nemotron-3-nano` (fast) | **10/10** · median 7.4s · p90 14.2s | 9/10 · median 5.6s · p90 7.5s |
| `nemotron-3-super` (deep) | **7/10** · median 20.4s · max 41.6s | **4/10** · median 9.1s |

**Four runs of `with_structured_output`, all on 2026-07-30 within about ninety minutes.**
Recorded in full because the spread matters more than any single row:

| Run | `fast` | `deep` |
|---|---|---|
| probe 1 | 9/10 · median 12.8s | 8/10 · median 19.7s |
| head-to-head | 10/10 · median 9.5s | 8/10 · median 12.6s |
| clean rerun | 10/10 · median 7.4s | 7/10 · median 20.4s |
| live test suite | 10/10 · median 7.2s | 9/10 · median 9.2s |

`fast` 9–10/10. `deep` 7–9/10, **never 10/10**, with its median moving between 9.2s and 20.4s
inside an hour. The decision below rests on the aggregate, not on the worst run.

**Chosen: `with_structured_output()`.** More reliable than `bind` on both models, and it keeps
automatic Pydantic parsing. It is slower, and that was accepted deliberately.

**The reliability problem is the model, not the method.** `nano` is near-perfect at structured
output; `super` fails 3–6 times in 10 whichever way it is called. Its `with_structured_output`
failures return **`None`** rather than raising, which is why `llm.py` now logs `outcome=empty` —
otherwise the failure is completely silent.

**Karthik's call (2026-07-30): retry now, revisit the model assignment in Phase 2.** The
alternative was moving the Case Architect, Planner, and Evaluator from `super` to `nano`
immediately, which buys 10/10 and cuts the median from 20.4s to 7.4s. Rejected for now because
`super` was chosen for reasoning quality and **no quality comparison has been measured** —
reassigning would trade an unmeasured property for a measured one. Phase 2's golden cases are
the first real quality signal. Revisit there, with data.

**This is worth flagging for whoever picks up Phase 2:** ARCHITECTURE.md §4 assigns `deep` to
three of the four structured-output agents and `fast` only to the Interviewer. On reliability
grounds that assignment is backwards. It is deliberately left alone for now, not overlooked.

**No deviation from ARCHITECTURE.md.** Its §4 already specifies "schema validation failure
re-prompts once with the validation error appended, then fails the node." The implementation
matches exactly. What changed is status, not design: that behaviour was written as defence in
depth and the measurement makes it load-bearing.

Two things retry deliberately does **not** do. It does not retry transport failures — a 429,
503, or timeout needs backoff per ARCHITECTURE §9, and an immediate second call would double
load exactly when the endpoint is refusing it. And it does not swallow a double failure into
`None`; it raises `StructuredOutputError`, because an unparseable value entering graph state
surfaces as a confusing error several nodes downstream.

**Correction to an earlier hypothesis in this file, recorded so it is not repeated.** The 2–4s
structured-output figure from 2026-07-29 came from raw HTTP with a simpler schema. I predicted
LangChain's tool-calling path was the slow one and the raw `json_schema` path the fast one. The
first head-to-head showed the opposite. It also scored raw `json_schema` at 6/10 on `deep`, but
**three of those four failures were a bug in my probe**: the Pydantic model declared
`confidence` with `ge=0.0, le=1.0` while the hand-written JSON Schema said only
`{"type": "number"}`, so the model returned a percentage and Pydantic rejected a response the
endpoint was never told to bound. Corrected in the clean rerun above. Run-to-run noise on the
same model and method was 9/10 vs 10/10, comparable to the gap between methods — **treat any
single N=10 run here as one sample.**

**2026-07-30 · `reasoning_effort` enum resolved — the last LLM-side unknown is closed.**
Nemotron accepts it (unlike `thinking`, which it rejects with HTTP 400). Sending a deliberately
invalid value made the validator enumerate the whole set:

```
reasoning_effort=xyzzy -> HTTP 400
  unknown variant `xyzzy`, expected one of
  `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`
```

`low`, `medium`, `high`, `max`, and `none` each returned HTTP 200 on `nemotron-3-super`.
**`high` exists, so ARCHITECTURE.md's assumption for the Evaluator holds** and needs no change.

Two notes for whoever uses this. Latency showed no clear ordering across levels at n=1 (0.4–0.7s,
except `none` at 5.8s, which is almost certainly contention rather than signal) — **do not treat
the level as a latency lever without measuring it properly.** And the technique generalises:
when an enum is undocumented, send a junk value and read it off the validator rather than
guessing one at a time.

**2026-07-30 · Streaming through `ChatNVIDIA` confirmed working.** 128 chunks, first at 0.50s,
3.4s total for a 212-character answer. Worth holding next to the structured-output numbers:
first token in half a second means the models are not slow. Structured output specifically is.

**2026-07-30 · `with_structured_output()` bypassed the logging wrapper — real bug, fixed.**
The scaffold returned `self._client.with_structured_output(...)`, a runnable wired straight to
the underlying client. Every structured call skipped `LoggingChatNVIDIA` entirely. Since agents
use structured output almost exclusively, **nearly the whole application would have been
invisible to the rate-limit log while appearing to work** — against CLAUDE.md's "every LLM call
is logged with a timestamp", and the free tier's 40 RPM ceiling is the first thing that breaks
under a demo. `tests/test_llm.py::test_structured_calls_are_logged_too` is the regression guard.

**2026-07-30 · `openai==1.59.0` was never published. Pin corrected to `1.59.2`.**
PyPI's release train goes `1.58.1 → 1.59.2`; there is no `1.59.0`. `pip install -r
requirements.txt` failed outright on that line. Two things confirmed while fixing it:
`langchain-nvidia-ai-endpoints==1.4.3` declares `Requires-Dist: aiohttp, langchain-core,
requests` and **does not depend on `openai` at all** — it imports and runs fine with openai
absent. So this was a plain bad pin, not the dependency conflict it looked like. Kept the
package because story 0.2's decision gate allows dropping to the raw client for structured
output, and the probe scripts already use it. `pip check` now clean.

**2026-07-30 · GNU Make 4.4.1 installed via winget (`ezwinports.make`).** It was absent, which
blocked two 0.1 acceptance boxes written around `make`. Chosen over rewriting the command
interface because CLAUDE.md, PHASE-0-SPEC, and every future phase gate name `make` targets;
installing costs one command, rewriting costs doc churn in perpetuity. **Make has no deployment
impact** — Render runs `uvicorn` directly and Netlify runs `npm run build`; neither sees a
Makefile. Note for future sessions: winget modifies PATH but the change needs a new shell, so
`make` may appear missing until the terminal restarts. Binary is at
`%LOCALAPPDATA%\Microsoft\WinGet\Packages\ezwinports.make_*\bin\make.exe`.

All six targets verified on Windows. No `SHELL` override was needed — cmd.exe resolves the
forward-slash `.venv/Scripts/python.exe` path fine, which was the anticipated failure.

**2026-07-30 · `check_env.py` had drifted from the decisions in this file, and would have failed
every run.** It still required a single `NVIDIA_MODEL` var (replaced by the three-model split on
2026-07-29) and still probed `thinking: {"type": "disabled"}` (which Nemotron rejects with
`HTTP 400 Unsupported parameter(s)`, also recorded 2026-07-29). Both decisions were written down
correctly and the tooling was never updated to match. Now checks all three models, times each,
and flags any above 10s as contention rather than an env failure.

**The general lesson, worth more than the fix:** DEV-STATE was right and the script was wrong.
Scripts encode decisions too, and they drift silently because nothing re-reads them. When a
decision changes a variable name or an API parameter, grep `backend/scripts/` in the same commit.

**2026-07-30 · CORS "rejects an unlisted origin" needs the right assertion, or `test_api.py`
will encode a false pass.** A simple `GET` with a disallowed `Origin` returns **HTTP 200** with
the `access-control-allow-origin` header *absent* — the browser is what blocks it. Only a
**preflight `OPTIONS`** returns `400 Disallowed CORS origin`. Both observed:

```
GET     Origin: http://evil.example.com   -> 200, no access-control-allow-origin
OPTIONS Origin: http://evil.example.com   -> 400 Bad Request
OPTIONS Origin: http://localhost:5173     -> 200, access-control-allow-origin echoed
```

So the phase-spec test must assert on **preflight status** or on **header absence**, never on a
simple request returning non-200. Asserting the latter would fail against correct code and
invite someone to "fix" working CORS.

**2026-07-30 · Pre-commit hook lives in tracked `.githooks/`, not `.git/hooks/`.**
`core.hooksPath` is set to it, so the hook survives a clone. `.git/hooks/` is not version
controlled, which would have made the guard a matter of whoever set up the machine — the
opposite of the "structural rather than a matter of care" intent in story 0.3.

The hook matches each prefix **followed by 20+ characters of key material**, not the bare
prefix, because DEV-STATE.md, `check_env.py`, and `.env.example` all name `nvapi-` and
`sb_secret_` deliberately and must stay committable. It also filters placeholder forms:
`.env.example` ships `nvapi-xxxxxxxx...`, which is shape-identical to a real key. **Known
trade-off: a real key containing eight consecutive `x` characters would slip through.**

**2026-07-29 · Design skill: v1 governs this product, not v2.** All 13 skills from
`github.com/Leonxlnx/taste-skill` are installed. Note the plan's `--skill "taste-skill"` name
does not exist — skill names differ from directory names in that repo. Installing without
`--skill` takes all 13, which is what we did.

The important finding: **`design-taste-frontend` (v2) explicitly scopes itself out of this
product** in its own §13 — "Dashboards / dense product UI / admin panels… Multi-step forms /
wizards" — and instructs the agent to say so rather than apply it wholesale. But
**`design-taste-frontend-v1` still carries dedicated software-UI rules that v2 dropped** when
it was rewritten toward landing pages: serif banned on dashboards with two named sans pairings,
dashboard card-container hardening gated on density, a mandatory icon library, and mono for all
numbers.

**v1 is therefore the governing skill.** v2 contributes its expanded AI-tells list and the
em-dash ban. Reasoning and dial settings in `ARCHITECTURE.md` §8.

Also checked and rejected: `high-end-visual-design` is Awwwards/agency-tier and prescribes
`py-24`–`py-40` macro-whitespace, floating glass-pill navigation, and eyebrow tags — correct
for a marketing page, absurd for a three-column assessment tool. `minimalist-ui` and
`gpt-taste` are likewise landing-page oriented. `industrial-brutalist-ui` is the only other
one that names dashboards, but its aesthetic contradicts the brief. **`full-output-enforcement`
is not a design skill and is worth applying generally** — it bans `// ...` and "rest of code"
placeholder patterns in generated output.

**2026-07-29 · Dials set: VARIANCE 3 · MOTION 4 · DENSITY 6.** Motion deliberately below 5
to avoid v1's perpetual-micro-interaction mandate, which would fight the anti-jitter
requirement from UI research; the active-agent pulse is the one exception since it carries
real semantic state. Density at 6 keeps card containers legitimate — v1 bans them above 7,
which would contradict the brief. Cards are used for the three column surfaces and chat
messages; agent rows and score rows inside the rails are grouped with hairlines, not nested
cards.

**2026-07-29 · Icon library resolved: Phosphor, not Lucide.** Open question closed. v1 §2
mandates `@phosphor-icons/react` or `@radix-ui/react-icons`; v2 §3.C discourages Lucide;
`high-end-visual-design` §2 bans "standard thick-stroked Lucide" outright. Three independent
agreements. shadcn's Lucide default is swapped at scaffold time in Phase 1 —
`strokeWidth 1.5` standardized globally.

**2026-07-29 · Progress-bar question closed, no change needed.** v2's pre-flight bans
"scoring/progress bars with filled background tracks," but its own §9.F frames this as a
landing-page rule and calls the pattern "dashboard-UI clutter *on a landing page*." We are the
dashboard. The right panel's bars are correct as specified.

**2026-07-29 · Accent colour desaturated.** The plan's accent `#2C5FF6` is roughly 92%
saturation; the skills cap accents at 80%. Changed to `#3A63D0` light / `#6E92E8` dark.

**2026-07-29 · Serif dropped entirely; mono changed to Geist Mono.** An earlier draft paired
Geist with Fraunces for display headings. v2 §4.1 bans Fraunces and Instrument Serif by name
as the two LLM-favourite display serifs, and v1 §7 bans serif on dashboards outright. Mono
switched from JetBrains to **Geist Mono** to match v1's named pairing exactly.

**2026-07-29 · Two design rules constrain agent prompts, not just CSS.** v1 §7 bans
fake-round numbers (`99.99%`, `50%`, `$1M`) and generic names ("John Doe", "Sarah Chan"
register). These reach into the **Case Architect's spec**: generated financials must be
organic (`31.4%` market share, `$4.7M` ARR) and generated company, competitor, and persona
names must not sit in the banned register. The placeholder interviewer name "Maya Chen" used
in the architecture wireframes is itself in that register and must be replaced before Phase 3
ships.

**2026-07-29 · Transcript summarizer dropped from V1.** Interview research recommended one for
context management. GLM 5.2's 1M-token context makes it unnecessary at single-round scale.
Revisit only if multi-round sessions are added.

---

**2026-07-29 · NVIDIA account model resolved: pure rate limit, no credits.** Confirmed from the
account dashboard — **up to 40 RPM**, no credit balance anywhere. The credit-trial model
described in older forum sources is gone. This closes the blocker and, importantly, means
**there is no budget that can be exhausted mid-build**. The only constraint is concurrency,
which the architecture already handles. Story 0.3 can be marked complete without further work.

**2026-07-29 · MODEL CHANGED: GLM 5.2 → Nemotron 3 family. Latency, measured.**

GLM 5.2 is capable and its capability panel is accurate. It is also **unusable on the free
tier**: a trivial 3-token prompt took **~230 seconds**, of which ~228s was queueing and ~2s was
generation. Streaming proved it — HTTP 200 arrived at 229.9s, first token at 231.9s, complete at
232.1s. The model works; you just cannot get to it.

A discriminating test showed this is **per-model demand, not an account throttle**:

| Model | Latency (trivial prompt) |
|---|---|
| `z-ai/glm-5.2` | ~230s queued |
| `meta/llama-3.3-70b-instruct` | >75s queued |
| `openai/gpt-oss-120b` | >45s queued |
| `nvidia/nemotron-3-nano-30b-a3b` | **0.3s** |
| `nvidia/nemotron-3-super-120b-a12b` | **0.4s** |
| `openai/gpt-oss-20b` | **0.3s** |

Structured output, 3 trials per model per mode, `max_tokens 3000`, `temperature 0`:

| Model | `response_format: json_schema` | prompt-only | latency |
|---|---|---|---|
| `nemotron-3-nano-30b-a3b` | **3/3 strict** | 3/3 strict | 2.3–4.2s |
| `nemotron-3-super-120b-a12b` | **3/3 strict** | 3/3 strict | 1.7–4.3s |
| `openai/gpt-oss-20b` | 3/3 strict | 3/3 strict | ~4.0s |
| `llama-3.3-nemotron-super-49b-v1.5` | 3/3 strict | 3/3 strict | 23–46s (too slow) |

**Decision: `nemotron-3-nano-30b-a3b` for the Interviewer, `nemotron-3-super-120b-a12b` for
everything else, `openai/gpt-oss-20b` as fallback.** Structured output is no longer a risk —
strict `json_schema` was 3/3 on every fast candidate. Prompt-validate-retry stays as defence in
depth but is not load-bearing.

**Worth naming plainly: this is what the original tech research recommended, and I overrode it.**
The researcher proposed the Nemotron 3 family; I switched to GLM 5.2 on the strength of its
documented 1M context and explicit structured-output support. That reasoning was sound on
capability and wrong on the dimension neither of us had data for — how heavily contended a
popular third-party model is on NVIDIA's free tier. Capability was documented; provisioning had
to be measured.

**2026-07-29 · The `thinking` parameter is GLM-specific, not portable.** Nemotron 3 rejects it
with `HTTP 400 Validation: Unsupported parameter(s): 'thinking'`. The latency-vs-quality lever
designed into the architecture therefore no longer exists as a parameter. Replaced by **model
choice** — nano for latency-critical turns, super for quality-critical ones. Arguably cleaner,
since it is one dimension instead of two.

**2026-07-29 · `/v1/models` lists models the account cannot use.** 102 returned, but
`nvidia/llama-3.1-nemotron-70b-instruct` and `moonshotai/kimi-k2.6` return `404 Function not
found`, and `deepseek-ai/deepseek-v4-flash` / `nemotron-3-ultra-550b-a55b` return
`503 ResourceExhausted`. Never treat catalog presence as availability — issue a real completion.

**2026-07-29 · GLM 5.2 capabilities confirmed from the official model page.**
[build.nvidia.com/z-ai/glm-5.2](https://build.nvidia.com/z-ai/glm-5.2) Specifications and
Capabilities panels state: Provider Z.ai · Context Length **1M** · Parameters **753B** ·
Function Calling **Supported** · Structured Output **Supported** · Reasoning **Supported** ·
Text in, text out.

**Structured Output being explicitly listed is the significant one.** It was the single
unresolved risk in the tech research — my researcher could not confirm whether `guided_json`
worked on the free hosted endpoint or only on self-hosted NIM containers. It is now confirmed
from the vendor's own capability panel. The prompt-validate-retry fallback stays in the
architecture as defence in depth, but it is no longer a load-bearing assumption. Story 0.2
still measures the actual pass rate, since "supported" and "reliable ten times out of ten"
are different claims.

**2026-07-29 · NVIDIA key exposed; keeping it — deliberate decision, do not re-flag.**
The key was captured in a screenshot and remains in use. Karthik has decided not to rotate it.
Risk is bounded: the free tier is rate-limited at 40 RPM with no credit balance, so worst case
is contention, not cost. `backend/.env` is gitignored. **Future sessions: this is settled, do
not raise it again.**

Still worth doing in Phase 0 story 0.1: a pre-commit hook blocking the `nvapi-` and `sb_secret_`
prefixes. That guards the commit path regardless of this particular key's status.

**2026-07-29 · Supabase project recreated in Singapore; Render must deploy to Singapore.**
The first project (`naiwpcveuouubperqtet`) was created in **Sydney, `ap-southeast-2`** — determined
not from the dashboard but from the project's own IPv6 allocation: `db.<ref>.supabase.co`
resolves to `2406:da1c:10e4:...`, and AWS's published `ip-ranges.json` assigns `2406:da1c::/35`
to `ap-southeast-2`.

Render's free tier does not offer Sydney (Oregon, Ohio, Virginia, Frankfurt, Singapore only), so
backend and database would have sat on different continents. That interacts badly with this
architecture specifically: **LangGraph checkpoints after every node**, so one candidate turn is
roughly four checkpoint writes plus app-table writes — call it eight round trips. At ~100ms
Singapore↔Sydney that is close to a second of added latency per turn, permanently.

The decisive argument was asymmetry of cost, not raw milliseconds: the schema did not exist yet,
so recreating was free. After story 0.4 creates six tables plus LangGraph's checkpoint tables, a
region change becomes a real migration.

**Consequence for Phase 0 story 0.8: Render service region must be Singapore.** Not the default.

**New project: `tnqfqsocoqythakwybsw`, Singapore, verified.** Region confirmed the same way rather
than trusting the dropdown: `db.tnqfqsocoqythakwybsw.supabase.co` → `2406:da18:1691:a201:...`, and
AWS assigns `2406:da18::/35` to `ap-southeast-1`. Both `aws-0-` and `aws-1-` Singapore pooler hosts
resolve and accept TCP on 5432. Old Sydney project retained until the new one is proven, then
deleted (free tier allows two).

**2026-07-29 · Direct connection IPv6-only — now verified, not assumed.**
`db.naiwpcveuouubperqtet.supabase.co` returned an AAAA record and **no A record at all**. The
architecture's claim that Render's IPv4-only free tier cannot reach Supabase's direct connection
is measured fact. Session pooler remains mandatory. Both `aws-0-` and `aws-1-` pooler hosts
resolve and accept TCP on 5432; which one a project uses is not predictable from the ref, so if
auth fails on `aws-0-`, try `aws-1-` before assuming the password is wrong.

**2026-07-29 · Second credential exposure — database password.** The first database password was
posted in plaintext in chat. Reset as part of the project recreation. Separately it contained an
`@`, which breaks Postgres URL parsing and would have needed percent-encoding. Standing rule:
database passwords are letters and digits only.

**2026-07-29 · Supabase official agent skills installed.** `npx skills add supabase/agent-skills`
→ `supabase` and `supabase-postgres-best-practices`. Note the `supabase` skill scores **Medium**
on Snyk (the Postgres one is Low); skills run with full agent permissions, so worth knowing.

**2026-07-29 · Testing convention added, three tiers.** The phase spec originally carried only
acceptance criteria, with no test layer defined for non-agent work. Now: (1) automated tests in
`backend/tests/` and `frontend/src/**/*.test.ts`, named in the phase spec, with assertions in
code; (2) golden cases as fixtures, defined in agent specs, gating every prompt change; (3) a
**Handoff** section ending each phase spec, splitting "verified by me, with evidence" from
"needs your eyes." Rule recorded in `CLAUDE.md`: a phase is handed over with observed output
pasted into this file, or it is not handed over. "Compiles" and "tests should pass" are not
evidence.

---

## Blockers & open questions

**2026-07-31 · GROQ MIGRATION GATE PASSED, AND THE GOLDEN SUITE IS GREEN-ISH FOR THE FIRST TIME.
0/8 on NVIDIA became 4/8 on Groq, with the failures now being real quality signals instead of the
whole suite dying at the call.**

The gate was the exact case that killed 1.3b: full 5671-char prompt, real schema, fixture 01.

```
openai/gpt-oss-20b    OK  2.7s  level=APM  correct  verbatim  low_confidence_fields empty
openai/gpt-oss-120b   OK  4.4s  level=APM  correct  verbatim  lcf=['company_contexts','product_types']
```

**The finding that settles the diagnosis beyond argument: `openai/gpt-oss-20b` is the SAME MODEL as
NVIDIA's `backup`, which fails there.** Same model id, same prompt, same schema, opposite result.
This was never model quality. It is the serving stack.

**Only `openai/gpt-oss-*` accept strict `json_schema` on Groq.** Measured against the live catalog:
`llama-3.3-70b-versatile`, `llama-3.1-8b-instant`, `qwen/qwen3.6-27b` and `groq/compound` all return
`400 This model does not support response format`. That is what pins `fast` and `deep` to the two
gpt-oss models, and it is why the Interviewer gets `llama-3.3-70b` instead: it needs prose, not a
schema, and it is the product's biggest token consumer.

**Rate limits, read from `x-ratelimit-*` headers rather than documentation. CORRECTED 2026-07-31
after probing the whole catalog: the limits are NOT uniform, and my earlier "1000/day per model"
generalisation was wrong. It happens to be true for the models we chose and false in general:**

```
model                      requests   tokens/min
allam-2-7b                     7000         6000
groq/compound                   250        70000
groq/compound-mini              250        70000
llama-3.1-8b-instant          14400         6000
llama-3.3-70b-versatile        1000        12000     <- backup / Interviewer
openai/gpt-oss-120b            1000         8000     <- deep
openai/gpt-oss-20b             1000         8000     <- fast
qwen/qwen3.6-27b               1000         8000
```

Requests are per DAY, derived rather than assumed: 2 requests consumed showed `2m52.8s` to
replenish, and 172.8 / 2 = 86.4s, which is exactly 86400 / 1000. **Each model has its own bucket**,
so spreading roles across models multiplies the daily budget. **Tokens per minute is the binding
constraint, not requests** — a Resume Analyst call is roughly 2500 tokens, so ~3 fit in a minute.

**🔴 THE ACTUAL BINDING LIMIT IS 200,000 TOKENS PER DAY, PER MODEL. It is NOT in the headers and is
invisible until you hit it.** Found by story 1.3b's agent exhausting it during prompt iteration, then
reproduced independently on both models:

```
Rate limit reached for model `openai/gpt-oss-20b` ... on tokens per day (TPD):
  Limit 200000, Used 198971, Requested 7441. Please try again in 46m9.984s.
```

**Header check, deliberate: `x-ratelimit-*` exposes only the per-MINUTE token limit and the daily
REQUEST count. There is no daily-token header at all** — verified by dumping every header on a live
response. So the one limit that actually stops work cannot be monitored, only discovered.

**Budget arithmetic, which changes how this project must be worked:**

```
system prompt now 11,600 chars  ~2,900 tokens
+ resume + output               ~4,000 tokens per Resume Analyst call
golden run (8 cases)           ~32,000 tokens  = 16% of one model's DAILY budget
                                -> about 6 golden runs per model per day
```

**Plan prompt iteration around this.** Story 1.3b spent ~27 calls tuning and exhausted `fast`
entirely; my two independent verification runs then exhausted `deep`. Iterate on ONE case
(`pytest "...::test_golden_case[06_founder_no_pm_title]"`), not the full set, and save full runs for
confirmation.

**Unquantified but serious for Phase 3 and beyond:** a full 45-minute interview is roughly 45 calls
across Case Architect, Planner, ~20 Interviewer turns, ~20 Evaluator calls and the Coach, and the
Interviewer and Evaluator both carry a transcript that grows every turn. That plausibly costs more
than one model's entire daily budget for a SINGLE interview. Roles sit on different models with
separate buckets, which helps, but **this needs measuring before Phase 3 commits to a turn count.**
Do not assume the free tier supports repeated end-to-end runs in one day.

**The spread is worth noting for Phase 3.** `llama-3.1-8b-instant` has 14400 requests/day, more than
14x our chosen models, and `groq/compound` has 70000 TPM against our 8000. Neither supports strict
schemas, so neither can run a structured agent — but the Interviewer needs prose, and if its token
budget ever binds, those are the escape hatches.

**Raw `response_format` needs two things Pydantic does not emit, and `langchain-openai` does them
for us.** Found by watching `probe_groq.py` return false negatives against the exact models the app
runs on:

```
nested Pydantic model -> $defs/$ref -> 400 invalid JSON schema for response_format
missing additionalProperties: false -> 400 invalid JSON schema
```

`with_structured_output` resolves refs and sets `additionalProperties` before sending, which is why
the app's nested `ResumeAnalysis` works while a hand-rolled probe of the same shape does not.
**Anything that bypasses `get_llm()` and calls `response_format` directly must do both itself.**
One more reason the "agents call `get_llm(role)`" rule is load-bearing rather than stylistic.

Requests are per DAY, derived rather than assumed: 2 requests consumed showed `2m52.8s` to
replenish, and 172.8 / 2 = 86.4s, which is exactly 86400 / 1000. **Each model has its own bucket**,
so spreading roles across three models triples the daily budget. **Tokens per minute is the binding
constraint, not requests** — a Resume Analyst call is roughly 2500 tokens, so ~3 fit in a minute.

**Three infrastructure fixes the migration forced, each found by a failing case, not by reading:**

| Fix | Why | Symptom if missing |
|---|---|---|
| `max_tokens=4096` | Default truncates mid-JSON on nested schemas | Groq 400 `json_validate_failed`, "max completion tokens reached", which reads like a prompt bug and is not one |
| **`temperature=0`** | Golden cases are a REGRESSION suite | **Case 02 passed one run and failed the next on identical input.** A red case could not be distinguished from a bad sample, making every future prompt change unfalsifiable. **⚠️ SUPERSEDED 2026-08-01 — this narrows the variance and does NOT remove it. Case 01 still flaps. See Decisions 2026-08-01** |
| ~~30s~~ **60s** pacing between golden cases | 8000 TPM | 429 partway through the suite. Changes no assertion; a busy endpoint must not be recorded as a wrong prompt. **⚠️ 30s was arithmetically impossible and was recording 429s as prompt failures — one case requests ~7500 against a bucket refilling at 133/sec, needing ~56s. Raised to 60s on 2026-08-01. Raise it in step with the prompt** |

**GOLDEN RESULTS AFTER THE 1.3b PROMPT WORK — 2026-07-31, re-run independently by me, not taken
from the agent's paste:**

```
deep  (gpt-oss-120b)   6 measured, 6 PASSED   01 02 03 04 05 06     07 08 blocked by TPD
fast  (gpt-oss-20b)    0 measured             all 8 blocked by TPD
offline assertions    23 passed throughout
retries fired          0
```

**Every case that could run, passed.** But `fast` is entirely unverified against the final prompt and
`deep` is missing two cases, so **story 1.3 is NOT done and must not be ticked.** The honest state is
6/8 observed green, 10/16 model-case combinations unmeasured, blocked on a daily quota that resets
overnight. The agent flagged the same gap on `fast` rather than claiming 8/8, which was the right
call and matches what I measured.

**Finish this first next session, before anything else** — it is two commands and it is cheap once
the quota resets. See § Next session.

**Prompt changes that did the work** (agent's account, not independently attributed): binding each
uncertainty trigger to a NAMED field rather than a generic list fixed 05, 06b and 08 together; a
PM-vs-Senior-PM boundary paragraph fixed 02; and verbatim-quoting hardening around capitalisation,
trailing punctuation and verb tense fixed 06a's fabrication plus a second fabrication class it
exposed on 05 and 08. **A judgment call is on record and worth a human read:** the agent concluded
that fixture 05's designed answer implicitly weighs sustained multi-year surface ownership ABOVE the
rubric's "who set the direction" discriminator, and encoded that as an explicit tie-break rather than
silently rewriting the rule. Read AGENT-RESUME-ANALYST-SPEC §3 against the prompt before accepting it.

**EARLIER GOLDEN RESULTS, before the 1.3b prompt work, temperature 0, same eight cases:**

```
deep  (gpt-oss-120b)  4/8   4m41s   PASS 01 03 04 07   FAIL 02 05 06 08   retries fired: 0
fast  (gpt-oss-20b)   4/8   5m03s   PASS 01 02 03 07   FAIL 05 06         + 04 08 lost to 429
```

**On the model question ARCHITECTURE §4 left open: `fast` is at least as good as `deep` here, and
cheaper and quicker.** It passed 02, which `deep` failed, and its only two genuine failures (05, 06)
are also `deep`'s failures. Two of its cases were lost to rate limiting and are unmeasured, so this
is **not yet a verdict** — but nothing so far supports paying `deep`'s latency for this agent.

**Retries fired ZERO times across a full run.** That is the claim nobody in this project has been
able to make, and it closes the spec's "observe a retry, do not assume it" box with a real
observation. **It also means the retry wrapper is now near-dead code**: it exists because Nemotron
returned `None` instead of raising, and Groq's strict schema does not do that. Do not delete it yet
(one run is one sample), but its justification no longer holds and should be revisited in Phase 2.

**The remaining four failures are genuine prompt work, and one is exactly what the suite is for:**

```
02  got "Senior PM", expected "PM"                              (deep only)
05  flagged company_contexts / years_pm_experience, not assessed_level
06  FABRICATED a scope_evidence quote: 'started a direct-t...'  <- not in the resume
08  flagged company_contexts, expected years_pm_experience
```

**Case 06 caught a real fabrication on real output.** That is the assertion the agent spec calls the
single most important one in the file, and the vacuity floor added earlier today is what stops an
agent dodging it by quoting nothing. The suite is doing its job.

**2026-07-31 · KARTHIK'S CALL: MOVE TO GROQ. The structured-output ceiling is being treated as
evidence the NVIDIA free tier cannot support this product's core pattern, not as something to work
around.** His initial exploration indicates Groq resolves both the latency and the structured-output
problems. Options A, B and D below were all declined in favour of this.

**The right moment for it.** One agent exists, its golden suite is written and independent of any
provider, and the portability finding measured the swap at one constructor in one file because every
agent calls `get_llm(role)`. That cost only goes up as five more agents land.

**The gate before migrating, and it is this project's own standard rather than doubt about Groq:**
reproduce the exact failing case first. Same 5671-char system prompt, same `ResumeAnalysis` schema,
fixture 01. A valid parse is the evidence; "seems to indicate" is not. **Needs `GROQ_API_KEY`, which
is a credential only Karthik can supply** — nothing in the repo can proceed past this point without it.

**What the swap triggers, per CLAUDE.md's triggered-updates table**, none of it optional:
`llm.py`'s constructor · **grep `backend/scripts/`** (the row that bites: `check_env.py` has drifted
twice already) · `config.py` `REQUIRED_VARS` · both `.env.example` · `backend/.env` · the Render
dashboard · `CLAUDE.md`'s header and Commands table · `requirements.txt`.

**What must be RE-MEASURED rather than carried over.** Every one of these is a recorded NVIDIA
measurement that does not transfer, and quoting any of them post-swap would be stating a number for
a system that no longer exists:
- story 0.2's structured-output pass rates (`fast` 10/10, `deep` 7-9/10) and every latency median
- **the retry wrapper's entire justification** — it exists because `deep` returns `None` instead of
  raising. A provider with working strict schema could make it near-dead code
- the **40 RPM** ceiling and the "no credits, nothing exhaustible" account model
- the nano reasoning-preamble leak, and the ~1500-2800 char prompt ceiling itself
- the 6-to-63-minute contention swing

**🔴 2026-07-31 · SUPERSEDED BY THE GROQ DECISION ABOVE, kept because it is the evidence for it.
BLOCKED STORY 1.3b, AND THE ANSWER BECOMES THE PROJECT'S AGENT-CALL PATTERN.
Structured output dies above a ~1500-2800 character system prompt, on all three models. Needs
Karthik's call.** Full evidence under § Decisions, same date. Four options, with what each costs:

| Option | What it is | Cost / risk |
|---|---|---|
| **A. Two-step call** *(recommended)* | Call 1: full rubric prompt, **free-form prose** analysis, no schema. Call 2: short prompt, `Field`-described schema, "extract this into the schema". | **2 calls per resume** (16 per golden run) against 40 RPM. Each call does one job, so the rubric survives in full. Golden cases need no change |
| B. One call, constraints in `Field(description=...)` | Everything moves out of the prompt into the schema | Cheapest, and **measured unstable**: APM / Senior PM / Senior PM on one fixture, paraphrased quotes, junk in `low_confidence_fields` |
| ~~C. Raw `json_schema` via `bind()`~~ | ~~Different code path entirely~~ | **RULED OUT 2026-07-31 by probe.** Both models: `JSONDecodeError: Expecting value: line 1 column 1 (char 0)`. Non-JSON from the first character, on the full prompt |
| D. Split the rubric across several small structured calls | One call per decision (level, then evidence, then confidence) | Most calls, most latency, but each prompt stays small. Closest to how the panel already works |

**Recommendation: A.** It keeps the rubric that makes levelling correct, keeps the retry wrapper,
keeps the golden cases unchanged, and the extra call is affordable at single-candidate scale. B is
already measured and fails on the property the product depends on most.

**Option C was probed and is dead**, which also confirms the mechanism rather than merely inferring
it. `JSONDecodeError` at **character 0** means the response is not truncated or malformed JSON, it
is not JSON at all from the very first character. The model is answering in prose. That is the same
behaviour as the recorded nano reasoning-preamble leak, and it explains every `None` above: the
tool-calling path returns `None` for exactly the same reason the raw path returns prose. **No tool
call is ever emitted, so there is nothing for LangChain to parse.**

This is why shortening the prompt fixes the *call*: it is not a token budget being exceeded, it is
the model deciding to deliberate instead of answering. **Which is also why A is the right shape** —
it stops fighting that tendency and gives the deliberation its own call, where prose is the intended
output rather than a failure.



~~**2026-07-31 · BLOCKS STORY 1.1: anonymous sign-in is disabled.**~~ — **RESOLVED 2026-07-31.**
Karthik enabled it (Authentication → Sign In / Providers → Allow anonymous sign-ins). Verified
against the live endpoint rather than trusting the toggle, and two distinct identities were minted
end to end:

```
identity A: status 200 | is_anonymous=True | role=authenticated | id=4cfedd11-...
identity B: status 200 | is_anonymous=True | role=authenticated | id=28b2d874-...
two DISTINCT identities: True
A token claims -> role: authenticated | sub: 4cfedd11-... | is_anonymous: True
```

**THE FINDING THAT CHANGES STORY 1.1: anonymous users carry the `authenticated` role, not `anon`.**
Supabase's own dashboard warns about this in an amber callout. So every policy must be written
`to authenticated` — and `authenticated` is exactly the role that already holds default table-level
grants on all six tables. A policy written `to anon` does nothing at all, and a test that probes
the `anon` role passes while the real browser path stays open. Both mistakes are silent.

Probe users deleted immediately afterwards with the admin API; `auth.users` confirmed back to
**0 rows**. Anonymous users are never garbage-collected by Supabase, so anything that mints them
must delete them.

**Deferred, deliberately, to Phase 7:** Supabase recommends CAPTCHA on anonymous sign-ins, since
the endpoint creates a database row without authentication and can be abused to bloat MAU. Correct
call for a project with no public traffic, but it is a real hole and it is recorded here rather
than left unnoticed.

The original blocking evidence, kept because it explains why the story was held:

```
status 422
{"code":422,"error_code":"anonymous_provider_disabled","msg":"Anonymous sign-ins are disabled"}
```

It is a dashboard toggle — Authentication → Sign In / Providers → **Anonymous Sign-Ins** — and no
migration or script can flip it. **This blocks more of 1.1 than it appears to.**
`sessions.user_id references auth.users`, so the cross-session denial test cannot insert its two
fixture sessions at all without two genuine `auth.users` rows, which is exactly what anonymous
sign-in mints. The story was held rather than started, deliberately: an agent facing failing auth
calls tends to weaken the assertion until it goes green, and this is the one story in the phase
where a weakened assertion is silent and serious.

Re-probe with the snippet above before starting 1.1. Expect `200` and
`is_anonymous = True`.

~~`reasoning_effort` enum unknown~~ — **RESOLVED 2026-07-30. See Decisions.** Full set is
`none · minimal · low · medium · high · xhigh · max`. `high` exists, so the architecture's
assumption for the Evaluator holds. **No LLM-side unknowns remain.**

~~NVIDIA account model~~ — resolved 2026-07-29 from the account dashboard. See Decisions.

~~Structured-output latency 11–14s vs 2–4s~~ — **RESOLVED 2026-07-30.** Explained by two things:
the 2–4s figure came from a simpler schema over raw HTTP, and free-tier contention swings widely
(the same model and method moved between 9.2s and 20.4s median inside one hour). Four N=10 runs
are tabled under Decisions.

**Still open, and it is a product question rather than a bug: is 7–9s acceptable per
Interviewer turn?** `fast` is 10/10 at a ~7.2s median, which is what the Interviewer uses, so
the reliability side is fine. But a candidate waits on every one of those calls, and the p90 was
14.2s. Plain streaming is 0.5s to first token, so **streaming the Interviewer's question is the
obvious mitigation** and is worth deciding in Phase 3 rather than at the end.

**`nemotron-3-nano` leaked reasoning preamble into `content` — observed once, in story 0.7's
live `/skeleton/start` response. Worth closing before Phase 3, because nano is the Interviewer.**

Prompt was "Ask a product manager one short opening interview question. Reply with the question
only, in one sentence." What came back, verbatim:

```
"We are to ask a short opening interview question for a product manager, and reply with only
 the question in one sentence.\n The question should be concise and serve as an opening...\n
 Example: \"Can you walk me through a product you've launched that you're most"
```

Deliberation in the content field, then truncated mid-sentence by the skeleton's
`max_tokens=120`. **A candidate would have seen all of it.**

**Update after two more samples from the deployed service: it is INTERMITTENT, which is worse
than consistent.** Same prompt, same model, three observations — two leaked preamble, one came
back clean (`"What's one product decision you made that surprised"`). A failure that happens
sometimes will survive casual testing and appear in front of a candidate. Caveat still stands
that the skeleton prompt is deliberately minimal, with no system message and no few-shot.

**But do not assume prompt engineering alone fixes it.** The Interviewer's question is the most
user-visible string in the product, and the streaming mitigation under discussion for the 7-9s
latency would stream this preamble token by token. Options if it persists: a system message
constraining the output shape, structured output for the question (already mandatory-retry, and
nano is 10/10 there), or `reasoning_effort` — the enum is known, and `none`/`minimal` exist. Test
in Phase 3 before choosing.

~~Production checkpoint latency is unmeasured.~~ — **RESOLVED 2026-07-30 by the deploy.**
A full resume step (one checkpoint read plus the node's writes) costs **~27ms** from
Render-Singapore to Supabase-Singapore; a single read is not distinguishable from noise. The
298ms figure was a dev-machine artefact. Output under § 0.8. **Quote 27ms, not 298ms.**

**`make test-web` has nothing to run.** The frontend has no `test` script and vitest is not
installed — correct for Phase 0, which has no frontend tests, but `make test` will fail on the
`test-web` leg until Phase 1 adds vitest. Do not read that failure as a broken scaffold.

**Interviewer persona name needs replacing.** "Maya Chen" appears throughout the architecture
wireframes as a placeholder and sits in the exact register v1 §7 bans ("John Doe", "Sarah
Chan"). Needs a real choice before Phase 3 ships.

~~Icon library conflict~~ — resolved 2026-07-29, Phosphor. See Decisions.
~~Progress-bar tension~~ — resolved 2026-07-29, no change needed. See Decisions.

---

## Environment notes

Populated during Phase 0 as things are actually verified.

**PRODUCTION — live since 2026-07-30, all free tier, all Singapore.**

| | |
|---|---|
| Frontend | `https://pmaiinterviewpanel.netlify.app` — Netlify project `pmaiinterviewpanel` |
| Backend | `https://pm-interview-panel.onrender.com` — Render service `PM-interview-panel` |
| Database | Supabase `tnqfqsocoqythakwybsw` |
| Repo | `https://github.com/karthikr0208/PM-interview-panel` |

**Render:** root dir `backend` · build `pip install -r requirements.txt` · start
`uvicorn app.main:app --host 0.0.0.0 --port $PORT` · region **Singapore** · `PYTHON_VERSION`
3.12.10, matching the committed `backend/.python-version`. All 11 `REQUIRED_VARS` set in the
dashboard, never committed. `ALLOWED_ORIGINS` is the Netlify origin **only** — adding anything
wider fails story 0.8's acceptance.

**Netlify:** base dir `frontend` · build `npm run build` · publish `frontend/dist` ·
`NODE_VERSION=22` · `VITE_API_URL` set to the Render URL, plus `VITE_SUPABASE_URL` and
`VITE_SUPABASE_ANON_KEY` (**publishable key only — never `sb_secret_`, it bypasses RLS and every
`VITE_` variable ships readable in the browser bundle**).

**Both redeploy automatically on push to `main`**, and each only rebuilds when its own directory
changes, so a docs-only commit deploys nothing.

**Measured in production, 2026-07-30:** checkpoint step **~27ms** · cold start **32.33s** after
~18 min idle, warm 0.13s.

**Test counts, observed 2026-08-01:** backend offline **60 passed, 67 deselected** (~4s) ·
frontend **66 passed** across 8 files (~9s) · backend live **85 passed** (last full run
2026-07-31, ~63 min, costs real rate budget).

**Groq rate limits — the daily cap is a ROLLING window, not a midnight reset.** Confirmed
2026-08-01: at 196,251/200,000 used, the 429 said "try again in 27m28s", not hours. Budget trickles
back continuously at roughly 138 tokens/min, so practically **one golden call every ~28 minutes**
once the ceiling is hit. **There is no daily-token header** — verified by dumping every header on a
live response — so it is invisible until you hit it. `x-ratelimit-*` exposes only the per-minute
token limit and the daily request count.

**Size any budget probe to the request you actually intend to make.** A probe asking for
`max_tokens=4096` with a ten-token prompt reported both models "AVAILABLE" while a real golden call
requesting ~7,565 was still refused. It measured nothing.

**Realtime under RLS: PROVEN 2026-08-01**, with two real anonymous identities plus a service-role
control. Re-run `node frontend/scripts/probe_realtime.mjs` after any change to RLS policies or the
realtime publication. One residual startup race is documented at the top of
`frontend/src/lib/agentEvents.ts`.

**Toolchain, observed 2026-07-30:** Python 3.12.10 · Node 26.1.0 · npm 11.13.0 · git 2.54.0 ·
GNU Make 4.4.1 (installed this session, see Decisions).

**Backend venv at `backend/.venv`** — Python 3.12.10. The global interpreter has different
versions of fastapi/pydantic/openai and **no langgraph at all**; always use the venv or a `make`
target. Installed and `pip check` clean:

```
fastapi 0.135.1 · pydantic 2.10.4 · langgraph 1.2.9
langgraph-checkpoint-postgres 3.1.0 · langchain-nvidia-ai-endpoints 1.4.3
psycopg 3.2.3 · psycopg-pool 3.3.1 · openai 1.59.2
pytest 8.3.4 · pytest-asyncio 0.25.0
```

**Frontend:** Vite 8.1.5 · React 19.2.7 · **Tailwind v4.3.3 via the `@tailwindcss/vite` plugin**
— v4 style, so there is no `tailwind.config.js` and no `@tailwind` directives; `src/index.css`
opens with `@import "tailwindcss";`. Do not add v3-style config, the two do not mix. Tailwind was
proven to actually compile, not merely install, by grepping the built CSS for emitted rules. No
`lucide-react` anywhere, per the Phosphor decision.

**Added in story 1.2 (2026-07-31):** `python-multipart==0.0.20` — **FastAPI cannot accept an
`UploadFile` without it**, so this was a hard blocker, not a nicety. `httpx==0.28.1` moved from the
`# Dev` block to `# Core`: it is now a runtime dependency, since `app/supabase_client.py` talks to
Supabase Auth, PostgREST and Storage over raw HTTP. **No Supabase Python client was added** — that
would have pulled five transitive packages in for one upload call. **No new environment variables**;
everything needed was already in `REQUIRED_VARS`.

**Added in story 1.6a (2026-07-31):** `@supabase/supabase-js` 2.111.0 (dependency) ·
`@testing-library/react` 16.3.2 and `jsdom` 30.0.1 (devDependencies). `vite.config.ts`'s test
`environment` moved **`node` → `jsdom`**, which component tests need; story 1.5's 25 tests were
re-run under the new environment and all still pass. **No new environment variables** —
`VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` already existed in both `.env` files and are now
read by code for the first time, which is what gets them inlined into the bundle.

There is no global vitest setup file, so `@testing-library/react` does not auto-clean the DOM
between tests; the test files call `afterEach(cleanup)` themselves. Worth knowing before adding a
third test file that assumes otherwise.

**Added in story 1.5 (2026-07-31):** `@phosphor-icons/react` 2.1.10 (dependency) · `vitest` 4.1.10
(devDependency) · Geist + Geist Mono variable `woff2` vendored into `frontend/src/assets/fonts/`
from the `geist` npm package, OFL licence kept beside them. `test: "vitest run"` added to
`package.json`, and a `test` block to `vite.config.ts` (`environment: 'node'`). Test files are
excluded from `tsconfig.app.json` and typed by a separate `tsconfig.vitest.json` — `src/` is typed
browser-only, so a test importing `node:fs` breaks `tsc -b` without that split.

**`make test-web` works from 2026-07-31 and `make test` no longer fails on its second leg.**
The design tokens live in `frontend/src/index.css` and are guarded by `src/index.css.test.ts`,
which asserts every ARCHITECTURE §8 hex value. **`DESIGN.md` at the repo root is the design
authority for every later phase**, generated via `stitch-design-taste` and reconciled against §8;
its § 8 lists every skill directive that was overridden and why.

**Supabase connection: session pooler, port 5432 — verified working 2026-07-30.**
`aws-0-ap-southeast-1.pooler.supabase.com:5432`, PostgreSQL 17.6. `check_db.py` connects clean.
**Six app tables now live** (story 0.4). `check_db.py` reports "public tables: 0" only before
that migration — after it, expect 6.

**Schema is managed by `backend/migrations/*.sql` + `scripts/migrate.py`. Never the dashboard.**
Story 0.8 deploys to Render, and a schema that exists only as dashboard clicks cannot be
recreated. Migrations are written idempotent so re-running is safe. Two separate concerns:
`migrate.py` owns the six app tables, `init_db.py` owns LangGraph's checkpoint tables.

- `checkpointer.setup()` runs via `scripts/init_db.py`, once, never on app startup. It also
  enables RLS on the checkpoint tables, which LangGraph does not do.
- **Transaction-pooler error text, observed 2026-07-30:**
  `psycopg.errors.DuplicatePreparedStatement: prepared statement "_pg3_0" already exists`.
  Reproduces only under concurrency — see Decisions.
- **Windows dev only:** `asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())`
  is required before any async psycopg use. Not needed on Render.
  **But it does NOT rescue `uvicorn app.main:app`** — that path creates its loop before importing
  the module, so the guard runs too late and startup fails. `make dev-api` works only because
  `--reload` makes uvicorn fix the policy itself. Corrected 2026-07-30, see Decisions; do not read
  the guard in `app/main.py` as protecting you.
- **10 public tables:** six app tables + `checkpoints`, `checkpoint_writes`, `checkpoint_blobs`,
  `checkpoint_migrations`. All ten have RLS enabled, none have policies.
- **Checkpoint volume:** ~0.58 MB per 20-turn interview, roughly 869 interviews to the 500MB
  free cap. `messages` dominates; `case_world` is stored once.
- All 13 skills installed at `.agents/skills/` (symlinked for Claude Code).
  **Governing skill for this product: `design-taste-frontend-v1`.** See Decisions.
- `stitch-design-taste` independently corroborates the v1 dashboard rules — "Serif is always
  BANNED in dashboards or software UIs" and "Dashboard Constraint: use Sans-Serif pairings
  exclusively (`Geist` + `Geist Mono` or `Satoshi` + `JetBrains Mono`)". It also generates a
  semantic `DESIGN.md` for agents to follow. **Worth considering in Phase 1** as the artifact
  that encodes our tokens, rather than hand-writing one.
