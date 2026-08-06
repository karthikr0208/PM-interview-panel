# Agent spec — Interviewer

> **🔴 REWRITTEN IN PART BY STORY 3.5.4, 2026-08-06. Read this box before anything below it.**
>
> Sections below are **superseded** and left in place for the audit trail, per CLAUDE.md's rule
> against rewriting history. This agent changed more than any other in Phase 3.5: it gained a second
> LLM call, and it lost the constraint that was its strongest result.
>
> | Section | What actually holds now |
> |---|---|
> | **§2b, refusal** | 🔴 **The refusal branch is DELETED.** `answer_clarification` now **invents** a plausible fact when `case_world` is silent, states it as given, and returns it in a new `improvised_fact` field. Karthik's call, 2026-08-06: a refusal reads as a broken interviewer, and real interviewers say "assume DAU is 50 million" all the time |
> | **§2b, inputs** | It reads `case_world` **plus `improvised_facts`**, the append-only state list of everything it has already invented this interview. Still no resume, no profile, no level |
> | **§2c, probing** | 🔴 **Reversed. Probing IS in the product**, as `generate_probe`, added by story 3.5.4. `followup_count` is no longer 0; it is the conduct loop's **primary driver**. The interview is now ONE question probed up to 8 times |
> | **§3 output schema** | Adds `Probe(probe, angle_used)` and `ClarificationAnswer.improvised_fact`. 🔴 `Probe` deliberately has **no `primary_dimension`** — that is resolved in Python by `resolve_primary_dimension`, never asked of the model |
> | **§6 the budget** | Recomputed 2026-08-06 with `tiktoken`, against the real curated worlds rather than a chars/token estimate. The finding is unchanged in kind and larger in size: **the naive design still does not fit.** See the new numbers below |
>
> **What replaced the refusal assertion.** The 2026-08-05 correct refusal was the only observation of
> ARCHITECTURE §9's undetectable failure mode *not* happening, and giving it up was deliberate. The
> property with teeth now is **consistency**: an improvised fact, once recorded, must repeat exactly
> when asked again. Measured 2026-08-06 — *"Claude.ai has 5 million weekly active users"* came back
> identical on the second ask. `ungrounded_figures` was **retargeted**, not deleted: it now checks
> against `case_world ∪ improvised_facts`.
>
> 🔴 **`improvised_fact` being non-empty is the ONLY safe signal to append on.** On a repeat ask the
> model returns `can_answer=True` with an empty `improvised_fact`, because the fact is by then
> established. A node keyed off `can_answer` would double-record on every repeat.
>
> **§6, recomputed.** `tiktoken` `o200k_base`, largest curated world (`openai.json`) = **1,392
> tokens**, at probe 10 where the transcript is longest:
>
> | | typical 250-word answers | verbose 500-word answers |
> |---|---|---|
> | full transcript | 7,074 | **10,274 — over the 8,000 ceiling** |
> | first answer + last 4 turns | 5,154 | **6,754 — fits** |
>
> The window is the candidate's **first answer plus the last 4 turns**. The first answer is kept
> because it is their thesis and every later probe pushes on it. **~47,000 `fast` tokens per
> interview, so about four a day.**
>
> 🔴 **`max_tokens` is a reasoning budget, not an output budget, and this agent is where that bit.**
> `generate_probe` shipped at 1024, reasoned from output size: `Probe` is two short strings, smaller
> than `ClarificationAnswer`'s three fields. But gpt-oss emits reasoning tokens against `max_tokens`
> **before the JSON starts**, and reasoning scales with the **input** — which for a probe grows every
> turn. The one call in the product whose input grows monotonically had the smallest ceiling, and it
> failed with `json_validate_failed` at probe 3. Raised to 2048. **That fix is not yet verified.**
>
> **`write_bridge` is gone** (2026-08-05, a constant function wearing an LLM call), and the same test
> was applied to its replacement: four materially different answers produced **4 of 4 distinct**
> probes, each quoting the candidate.

**Written 2026-08-05, before the prompt exists**, per the story 1.3 split that Phase 2 repeated
deliberately and that produced four defects there. The golden fixtures in story 3.1 are written
against this document and blind to the prompt.

**Status:** contract only. `app/agents/interviewer.py` does not exist yet (story 3.2).

**This agent has one hard requirement and it is not the one you would guess.** It is not "ask a good
question" — the Planner already did that, and its questions passed a grounding check, a genericness
check and a dash check before they reached here. **It is: never say anything `case_world` does not
contain.** ARCHITECTURE §9 lists "Interviewer contradicts the case world" as a failure mode whose
only detection is *manual* — five adversarial clarifying questions at the Phase 3 gate. **This spec
exists to make it mechanical instead, at the one surface where the agent generates free prose.**

---

## 1. Contract

| | |
|---|---|
| **Reads from state** | `question_plan: list[dict]` · `case_world: dict` · `messages` · `current_q_idx` · `followup_count` · `dimension_coverage` |
| **Writes to state** | `messages` (via `add_messages`) · `current_q_idx` · `dimension_coverage` |
| **Side effects** | One `agent_events` row per node on start and completion · one `transcript_turns` row per utterance |
| **Immediately preceded by** | `plan_interview`, then itself, in a loop |
| **Immediately followed by** | `await_candidate` → `route_input` |
| **Model** | `fast`, per ARCHITECTURE §4. Names come from `app/config.py` |

**Pure functions, node owns side effects.** Held for all three agents so far, and golden cases run
with no database because of it. No function in `app/agents/interviewer.py` takes a session, opens a
connection, or writes a row.

**🔴 `case_world` is READ ONLY, and this agent is where that rule finally earns its keep.** The
Planner was its first test by a downstream agent; the Interviewer is the first agent that generates
prose a candidate reads *about* the world, live, with no human in the loop. If it improvises a fact
here, the world stops being a single source of truth and the interview contradicts itself forty
minutes in.

---

## 2. The two behaviours, and why only ONE of them is an LLM call

Phase 3's spec names two behaviours: **asking a planned question**, and **answering a clarifying
question from `case_world` alone.** They are not symmetric, and the asymmetry is the main design
decision in this document.

**🔴 Updated 2026-08-05, on measurement: asking a question is now FULLY deterministic — zero LLM
calls, always.** It briefly had one, for a bridge line. That call was measured to be a constant
function and was deleted. **`answer_clarification` is therefore the only LLM call anywhere in the
conduct loop**, which is what every call-count assertion in `tests/test_conduct_loop.py` rests on.

### 2a. Asking a planned question — fully deterministic

**🔴 The planned question is emitted VERBATIM by Python. The model does not rewrite it, ever.**

PRD §8 requires questions be asked verbatim and revealed whole. CLAUDE.md § Style requires
deterministic Python wherever the decision can be made from state — and the question text *is* in
state, written by the Planner. But the load-bearing reason is narrower and worth stating on its own:

**The Planner's question string already passed `missing_grounding`, `is_generic_question`,
`no_dash_variants`, `contains_fake_round_number` and `contains_banned_register_name`.** Regenerating
it here would void all five checks at runtime, on a surface no static test can see. **A rewrite
would move the question from the most-tested string in the product to the least-tested one.**

So `ask_question` composes its utterance as:

```
[transition]  one fixed line from `_TRANSITIONS`, rotating, ONLY from question 2 onward
[question]    the Planner's `question` string, copied byte for byte
```

A question fired with no acknowledgement of the answer just given reads as a form, which is what the
Phase 3 handoff question asks about. **Question 1 has nothing to acknowledge, so it opens cold.**

**🔴 The transition was an LLM call until 2026-08-05, and it was deleted on evidence, not taste. It
was a CONSTANT FUNCTION.** Six materially different candidate answers produced the same sentence
with the words shuffled:

```
strong+specific  -> "Got it, thanks for sharing that. Let's move on."
weak/vague       -> "Got it, let's move on."
refuses/stuck    -> "Thanks for sharing that. Let's continue."
disagrees        -> "Understood. Let's move on to the next topic."
very short       -> "Thanks for sharing that. Let's continue."
rambling         -> "Got it, thanks for sharing that. Let's continue."
```

The candidate who said *"I don't know, I've never worked on a churn problem"* got "Thanks for
sharing that." The one who **challenged the premise** — the single place a real interviewer visibly
reacts — got a generic move-on. It was buying nothing, and costing a `fast` call per question,
latency while a candidate watches a cursor, and a candidate-facing generative surface no static
check could see.

**Three things improved by replacing it with source strings**, and the third is the one that
matters most:

1. Zero tokens and zero added latency, on the one surface where a candidate is watching.
2. Consecutive turns can no longer repeat, because the set rotates. The old pair read *"Understood,
   thanks for sharing that approach. Let's continue."* / *"Understood, thanks for sharing that.
   Let's continue."*
3. **The em-dash ban on this surface is now STATICALLY ENFORCED** by
   `tests/test_user_facing_copy.py::test_no_dashes_in_interview_transitions`, not merely prompted.
   Prompting had already failed twice on that exact rule. The guard is falsified, not assumed: an
   injected em-dash makes it go red.

**The general lesson, worth carrying to any future agent:** before spending an LLM call on a
generative surface, check whether its output actually varies with its input. If it does not, it is a
constant and CLAUDE.md § Style says write the constant.

### 2b. Answering a clarifying question — LLM, `case_world` only

The real work, and the whole risk. The candidate asks something like *"how big is the design team?"*
and the agent must answer from the world or say the world does not specify it.

**It reads `case_world` and the current question, and nothing else.** No resume, no profile, no
level. Anything it cannot support from the world is not available to it.

### 2c. Probing is NOT in this phase, and the reason is falsifiability

ARCHITECTURE §3's `conduct_round` routes `decide_next` → `probe` → `ask_question`. **Phase 3 does
not build that edge**, because PRD §7's success criterion for probes is *"two runs with deliberately
different answer quality produce visibly different probes"* — and **answer quality is a score, which
Phase 4 produces.** A probe built now would fire on no signal and its adaptivity would be
unfalsifiable, which is the exact shape this project keeps getting burned by. `followup_count` stays
`0` for the whole of Phase 3.

The Planner's `probe_angles` are therefore unused in this phase. **That is expected, not a defect,**
and it is the answer to AGENT-PLANNER-SPEC §8's open question only once Phase 4 has run.

---

## 3. Output schema

Sketch. Story 3.2 implements it; story 3.1 writes assertions against it.

```python
# `_TRANSITIONS: tuple[str, ...]` and `transition_for(q_idx) -> str | None`
# replace what was a `BridgeLine` schema and an LLM call. No model, no
# schema, no call. See §2a.

class ClarificationAnswer(BaseModel):
    can_answer: bool                   # False => the world does not specify this
    answer: str                        # candidate-facing prose
    grounded_in: list[str]             # case_world facts this answer rests on
```

**`grounded_in` is inherited from the Planner deliberately, and for the same reason it exists
there:** it converts "did this answer invent something?" from a judgment call into a
**set-membership check** against `case_world`. Story 2.5's `missing_grounding` and `world_haystack`
already implement exactly this; story 3.1 reuses the shape, not the module.

**🔴 `can_answer` exists to close a hole the Planner's schema does not have, and this is the one
schema decision worth arguing about.** The honest answer to *"how big is the design team?"* when the
world is silent is **"the brief does not specify that."** But a refusal is a short, factless string,
and a short factless string passes every content assertion by having nothing to object to — story
1.3a's exact bug, third recurrence. Making the refusal **structured** rather than prose means the
suite can hold it to a different, stricter standard (§5) instead of waving it through.

**`grounded_in` must be non-empty even when `can_answer` is `False`.** A refusal still rests on
something: the agent grounds it in the nearest thing the world *does* say. This is what stops
`can_answer: False` from becoming a legal way to opt out of every assertion in the suite.

---

## 4. Constraints on the prompt

- **Never state a number, company, product, person or date that is not in `case_world`.** The single
  rule this agent exists to obey.
- **When the world is silent, say so.** Do not extrapolate, do not offer a "reasonable assumption",
  do not answer a slightly different question that the world *can* support.
- **No em-dashes or en-dashes.** 🔴 **This surface is new.** `tests/test_user_facing_copy.py` checks
  source strings and every `_*_SUMMARY` constant; **it cannot see prose generated at runtime.** The
  ban must live in the prompt AND be asserted in the golden cases, exactly as the Planner's is — and
  note that **prompting has already failed twice to enforce this mechanical rule** (DEV-STATE
  § Next session, open defect 1). Assume it will fail a third time and assert accordingly.
- **No fake-round numbers, no banned-register names**, same set as the Case Architect and Planner.
- **Do not evaluate, hint, or coach.** The candidate must not learn how they are doing from the
  Interviewer. Scoring is Phase 4 and is deliberately invisible here.
- **Do not restate the question in the bridge.** The question follows verbatim on the next line;
  a bridge that paraphrases it is where an ungrounded rewrite sneaks back in.
- **No persona header, no interviewer name.** Binding since 2026-07-31: "Maya Chen" sits in the
  register design v1 §7 bans. The agent is an interviewer, not a character.

---

## 5. Golden cases

**Written blind in story 3.1.** Input is `(case_world, planned_question, clarifying_question)`.

**Fixtures reuse Phase 2's five hand-written case worlds** at
`tests/golden/planner/fixtures/*.json`, per PHASE-3-SPEC § 3.1. **This coupling is deliberate and is
the opposite of the choice `planner/assertions.py` made** (which stayed self-contained on purpose):
a `CaseWorld` schema change must break every downstream suite loudly and at once, rather than
leaving the Interviewer's fixtures quietly describing a world shape that no longer exists.

| # | Fixture | Clarifying question | Asserts |
|---|---|---|---|
| 1 | `apm_consumer_world` | A fact the world states plainly | Answers it, grounded, `can_answer=True` |
| 2 | `pm_b2b_world` | A fact reachable only by combining two `supporting_facts` | Grounded synthesis, not a single-fact lookup |
| 3 | `senior_pm_platform_world` | **A fact the world does not contain** | `can_answer=False`, no invented figure, still grounded |
| 4 | `gpm_portfolio_world` | A leading question that presupposes a false fact | Does not accept the premise |
| 5 | `sparse_world` | A fact a thin world is silent on | Degrades to `can_answer=False`, not to invention |

**Fixture 4 is the adversarial one and matters most.** *"Given that churn has been climbing all
year, how should I read that?"* against a world stating a flat 3.8% monthly churn. **A model that
politely accepts the premise has contradicted the world without stating a single new number**, which
is the failure mode most likely to survive review.

### Universal assertions, every case, each with the positive control that must go RED

| Assertion | Positive control that must go RED |
|---|---|
| **Vacuity floor, asserted FIRST** — `answer` non-blank and above a length floor; `grounded_in` non-empty *regardless of `can_answer`* | An answer of `""`, and one of `"I'm not able to say."` with `grounded_in: []` |
| **Every `grounded_in` entry appears verbatim in `case_world`** | An answer grounded in `"Northwind Logistics"` |
| **🔴 Every figure in `answer` appears in `case_world`** — see below | An answer citing `"about 62,000 subscribers"` against a world stating 41,000 |
| When `can_answer` is `False`, `answer` contains no figure at all | A refusal that still volunteers a number |
| No em-dash or en-dash in `answer` | Text containing one |
| No fake-round numbers, no banned-register names | An answer citing "50% of customers" |
| **Cross-world control** | An answer generated for fixture 1, checked against fixture 4's world, must FAIL |

**🔴 The figure check is this suite's teeth, and it goes beyond what the Planner asserts.** The
Planner could rely on `grounded_in` alone because its output is one short question the model has
every reason to keep tight. **This agent writes explanatory prose, where an invented number is both
most likely and most damaging** — and `grounded_in` does not catch it, because a model can ground an
answer honestly in one fact while inventing a second in the sentence beside it.

Mechanically: extract every numeric token from `answer` (digits, optionally with `$`, `%`, `,` or a
decimal point) and require each to appear in `world_haystack(case_world)`. Normalise thousands
separators before comparing, or `41,000` will not match a stored `41000` and the check will fire on
a correct answer, which is how a real assertion gets weakened into a useless one. **A small
allow-list of ordinals and counts is legitimate** ("the three options", "your second point"); keep
it explicit and short, and re-read it whenever this check goes red, because widening it is the
cheapest way to destroy it.

**✅ The `bridge` gap this section recorded is CLOSED, and not by covering it.** The gap was that
`bridge` was a candidate-facing generative surface no static check could see, and this golden suite
could not reach it. **Deleting the LLM call removed the surface entirely** (§2a), and the
transitions that replaced it are source strings covered by
`test_user_facing_copy.py::test_no_dashes_in_interview_transitions`, which is falsified. The
defensive `getattr(result, "bridge", None)` that briefly papered over the mismatch was removed on
the way: it could only ever no-op, so it read as coverage while asserting nothing.

**The vacuity floor is the lesson of story 1.3a, applied for the fourth time**, and this agent gives
it a new escape hatch that the earlier three did not have: **`can_answer: False`.** A suite that
lets a refusal skip the content assertions can be passed completely by an agent that refuses every
question. Assert `grounded_in` non-empty on **both** branches, and assert the refusal is a refusal
(it names the world's silence) rather than merely short.

---

## 6. 🔴 The prompt budget, computed — and the naive design does NOT fit

**This is the acceptance box PHASE-3-SPEC § 3.1 asks for, and the answer is a constraint on story
3.2's architecture, not a footnote.**

Groq computes `Requested = prompt + input + max_tokens` against an **8,000 TPM ceiling**.
`app/llm.py` sets `DEFAULT_MAX_TOKENS = 4096`, and its own docstring already says *"callers with a
small output schema and a large input should lower it"* — this agent is that caller.

Measured from this project's own fixtures, 2026-08-05, at the project's measured ~4.2 chars/token:

```
largest case_world   senior_pm_platform_world   3,937 chars   ~937 tok
smallest             sparse_world               2,488 chars   ~592 tok
```

**The naive design — hand every call the whole world plus the whole transcript — does not fit.**
At question 3, with two answered questions behind it and a candidate who writes 600 tokens per
answer:

```
case_world                 937
transcript, 2 Q&A pairs  1,500
current plan entry         150
framing                     50
                        ------
input                    2,637 tok
max_tokens (default)     4,096
                        ------
leaves for the prompt    1,267 tok  ~=  5,321 chars
```

**That is tighter than the Resume Analyst's shipped prompt (5,863 chars), and it gets worse with
every turn** — the Interviewer is the only agent in the product whose input GROWS during a session.
Sizing a prompt against a fixed ceiling here would be sizing it against the wrong number.

**The fix is scoping, not compression.** Each call takes only what its job needs:

| Call | Input | Input tokens | `max_tokens` | Leaves for prompt |
|---|---|---|---|---|
| ~~bridge~~ | — | — | — | **deleted 2026-08-05, see §2a — it is not a call at all now** |
| **clarification** | `case_world` + current question | ~1,150 | 2,048 | **~4,800 tok ~= 20,000 chars** |

**The one remaining call never receives the transcript, and that is the finding.** **The growing
input problem is designed out rather than budgeted for**, so the clarification sits at the same
distance from the ceiling at question 3 as at question 1. Deleting the bridge made this stronger
still: the loop's total token cost is now **flat in the number of questions** and varies only with
how many clarifications a candidate asks.

**Measured 2026-08-05:** clarification prompt **2,728 chars** against the ~20,000 ceiling. Far
under, the same pattern the Case Architect and Planner showed.

**🔴 The `max_tokens` figures above are PROJECTIONS and story 3.2 must measure them.** DEV-STATE
§ Decisions 2026-08-04 is explicit that **gpt-oss models emit reasoning tokens that count against
`max_tokens` before the JSON starts**, and that lowering it produced `json_validate_failed` at 1,600
and again at 2,600 on the Resume Analyst. **That was measured against a far larger schema than
`ClarificationAnswer`**, so it does not transfer — but it does mean **the floor is empirical and
nobody has found it for a three-field schema.** Start at 2,048, and if it returns
`json_validate_failed`, raise it rather than assuming the prompt is at fault: that error reads like
a prompt problem and is not one.

**Pacing for the golden suite:** the clarification call requests roughly `prompt + 1,150 + 2,048`.
Against a refill of 133 tokens/sec, a 60-second pace is sufficient — the same figure
`resume_analyst` settled on *after* measuring a real header, and safe here only because this call is
materially smaller than the Planner's, which needed 90.

---

## 7. Failure modes to design against

| Failure | Why it matters | Guard |
|---|---|---|
| **Invents a fact `case_world` lacks** | The world stops being a single source of truth; the interview contradicts itself and only a human notices | `grounded_in` membership **plus** the figure check, §5 |
| **Accepts a false premise in a leading question** | Contradicts the world **without stating a new fact**, so the figure check cannot see it | Fixture 4, and the manual adversarial pass at the gate |
| **Refuses everything** | Passes the whole suite by having nothing to check | `can_answer=False` still requires non-empty `grounded_in` and a refusal that names the silence |
| **Rewrites the planned question** | Voids all five checks the Planner's text already passed, at runtime, invisibly | The question is emitted by Python, never by the model, §2a |
| **Em-dash in generated prose** | No static guard can see runtime output; prompting has already failed twice | Asserted in the golden cases for `answer`; for the transition, **statically enforced** since it is no longer generated (§2a) |
| **An LLM call whose output does not vary with its input** | Costs tokens and latency to produce a constant. Cost the bridge its life on 2026-08-05 | Before shipping a generative surface, run one varied sample set and look at it |
| **An LLM call above `interrupt()`** | Re-runs on every resume, silently, forever | `await_candidate` holds only `interrupt()`; **falsified**, not inspected, in story 3.2 |
| **Input grows past the TPM ceiling mid-interview** | The interview dies at question 4, not at question 1, so a smoke test would not see it | Scoped inputs, §6 — neither call takes the transcript |
| **Evaluates or hints** | The candidate learns their score from the interviewer; not an interview any more | Named in the prompt constraints, §4 |

---

## 8. Open questions

- ~~**Does the bridge earn its LLM call?**~~ **RESOLVED 2026-08-05: no, and it is gone.** Measured to
  be a constant function, replaced by rotating source strings. That removed the Interviewer's second
  generative surface entirely, exactly as this question anticipated — one place to guard instead of
  two. See §2a. **Karthik's call**, made against the six-sample evidence rather than on taste.
- **Is `can_answer` a field, or is it inferable from `grounded_in`?** Kept as a field because the
  suite needs to hold refusals to a *different* standard, which requires knowing one happened. If
  Phase 4 finds no second caller, revisit — no fields without a second caller.
- **Should a clarification consume interview time?** Currently no. Real interviewers absorb a
  clarification into the question's budget. Revisit if the Phase 3 gate shows candidates using
  clarifications to stall.
- **Does `fast` hold `ClarificationAnswer`?** ARCHITECTURE §4 says `fast` and this is the one agent
  where that table and the portfolio calibration agree, since it runs while a candidate watches a
  cursor. But **the Planner needed `deep`** (DEV-STATE § Decisions 2026-08-04) and that was also a
  surprise. Three fields is far smaller than `QuestionPlan`, so `fast` is likely — **measure it in
  story 3.2, and do not assume it either way.**
