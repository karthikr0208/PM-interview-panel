# Agent spec — Resume Analyst

**Node:** `level_candidate` · **Runs:** once, on upload · **Model:** `deep`
(`nemotron-3-super-120b-a12b`) · **Built in:** Phase 1, story 1.3

The first agent. It reads extracted resume text and decides what level to interview the candidate
at. Everything downstream inherits that decision: the Case Architect builds a world sized to it,
the Planner sets question difficulty from it, and the Evaluator's scoring anchors shift with it.
**A wrong level does not produce a wrong score, it produces a wrong interview.**

---

## 1. Contract

| | |
|---|---|
| **Reads from state** | `resume_text: str` |
| **Writes to state** | `candidate_profile: dict` · `assessed_level: str` · `level_rationale: str` · `low_confidence_fields: list[str]` |
| **Side effects** | One `agent_events` row on start and on completion. One `resumes.profile` write |
| **Immediately followed by** | `confirm_level`, which contains only `interrupt()` and its return |

The candidate sees and can correct `assessed_level` at `confirm_level`. **This agent proposes; the
candidate decides.** That is why an honest `low_confidence_fields` matters more than a confident
guess: it tells the candidate what to check.

---

## 2. Output schema

Enforced by Pydantic through `with_structured_output()`, not by prompt text. `assessed_level` is a
`Literal`, so an out-of-vocabulary level is a validation failure and triggers the retry wrapper
rather than flowing into state.

```python
class CandidateProfile(BaseModel):
    years_pm_experience: float | None      # None when genuinely not derivable
    domains: list[str]                     # "B2B fintech", "consumer marketplaces"
    product_types: list[str]               # "platform APIs", "consumer mobile"
    company_contexts: list[str]            # "seed startup", "public enterprise"
    scope_evidence: list[str]              # verbatim resume phrases showing ownership scope
    notable_outcomes: list[str]            # verbatim phrases showing shipped impact
    people_leadership: str | None          # "mentored 2 APMs", None if absent

class ResumeAnalysis(BaseModel):
    candidate_profile: CandidateProfile
    assessed_level: Literal["APM", "PM", "Senior PM", "GPM"]
    level_rationale: str
    low_confidence_fields: list[str]
```

**`scope_evidence` and `notable_outcomes` hold verbatim resume phrases, not paraphrase.** Two
reasons. It is what makes `level_rationale` checkable rather than a matter of taste, and it is the
same discipline the database enforces on `answer_evaluations.evidence_quote` in Phase 4. An agent
that stops quoting should fail visibly here too.

**`candidate_profile` is not decoration.** Phase 2's Case Architect reads `domains` and
`product_types` to build a case world the candidate can reason about. A profile that omits domain
produces a generic case, which is the difference between a real interview and a quiz.

---

## 3. The levelling rubric

**Scope and autonomy are the signal. Years and titles are weak evidence and both are gameable.**
Title inflation at small companies and title deflation at large ones are both common; a "Senior
Product Manager" at a twelve-person startup and one at a public company are frequently two
different jobs. Read what the person actually owned.

| Level | Scope of ownership | Autonomy | Typical years | People |
|---|---|---|---|---|
| **APM** | A feature, or a defined slice of a surface | Executes a roadmap someone else set | 0-2 | None |
| **PM** | A product area or surface, end to end | Sets the roadmap for that area | 2-5 | None, or informal mentoring |
| **Senior PM** | A product line, or a domain with real ambiguity | Sets strategy for it, influences beyond own team | 5-8 | Mentors; may guide APMs |
| **GPM** | Multiple products, or a portfolio | Sets multi-quarter strategy, accountable for a business outcome | 8+ | Manages PMs |

**The strongest single discriminator is who set the direction.** A candidate who describes
executing well against a given roadmap is at most a PM regardless of tenure. A candidate who
describes choosing what not to build, and why, is at least a Senior PM.

**Ambiguity in the resume is itself the signal for Senior PM and above.** Resumes that describe
tidy problems with tidy solutions usually describe feature work. Ownership of something genuinely
underdetermined is what separates the top two rows.

**Do not level on company prestige.** A FAANG PM is not automatically senior to a startup PM.

### When `low_confidence_fields` must populate

An agent that is never uncertain is broken in a way that only shows up in front of a real
candidate. Populate it, naming the specific field, when any of these hold:

- **Title and scope disagree** — the title says GPM, the bullets read as PM
- **Non-linear background** — founder, consultant, engineer-turned-PM, long gap, career changer
- **Responsibilities without outcomes** — the resume lists duties and never says what happened
- **Tenure not derivable** — overlapping roles, no dates, or dates without months
- **Domain unclear** — which matters specifically because Phase 2 builds the case world from it

**A populated `low_confidence_fields` is a success, not a failure.** It drives the confirmation UI
in story 1.6, where flagged fields are visually marked so the candidate knows what to check rather
than being asked to verify everything equally.

---

## 4. Constraints on the prompt

These bind this agent's *prompt*, not just the UI. From `design-taste-frontend-v1` §7 via
CLAUDE.md, because `level_rationale` and the profile summary are candidate-visible:

- **No em-dashes** in anything the candidate reads.
- **No fake-round numbers.** If the resume says "grew retention 31.4%", carry that. Never round it
  to 30% and never invent a figure the resume does not contain.
- **No generic placeholder names.** Never substitute "a large tech company" for a named employer
  the resume gives, and never invent one it does not.
- **No praise.** `level_rationale` explains a levelling decision to the person being levelled. "An
  impressive track record of driving impact" is noise. "Owned the payments surface end to end and
  set its roadmap for six quarters, but no evidence of setting direction beyond that surface" is a
  rationale.

**Never infer protected characteristics**, and never let name, nationality, gender, age, or
university influence the level. This is a levelling tool that a real person's real resume goes
into.

---

## 5. Golden cases

At `backend/tests/golden/resume_analyst/`, run with `make golden AGENT=resume_analyst`.
**They must pass before any prompt change to this agent is committed.**

Each case is a resume text fixture plus assertions. Eight cases, spanning the four levels and the
four uncertainty modes:

| # | Fixture | Asserts |
|---|---|---|
| 1 | `apm_rotational` — 14 months, APM program, feature slices | `assessed_level == "APM"` · `low_confidence_fields` empty |
| 2 | `pm_owns_area` — 4 years, owns a checkout surface, sets its roadmap | `assessed_level == "PM"` |
| 3 | `senior_pm_product_line` — 7 years, owns a product line, names a bet not taken | `assessed_level == "Senior PM"` |
| 4 | `gpm_portfolio` — 11 years, manages 4 PMs, owns a P&L | `assessed_level == "GPM"` |
| 5 | `title_scope_mismatch` — titled "Group PM", bullets are single-surface feature work | level in `{"PM", "Senior PM"}` · **`low_confidence_fields` contains `assessed_level`** |
| 6 | `founder_no_pm_title` — 5 years running own startup, never called a PM | level in `{"PM", "Senior PM", "GPM"}` · `low_confidence_fields` non-empty |
| 7 | `duties_no_outcomes` — plausible seniority, zero stated results | `low_confidence_fields` non-empty · `notable_outcomes` empty rather than invented |
| 8 | `engineer_transition` — 8 years engineering, 18 months PM | `assessed_level == "APM"` or `"PM"` · `low_confidence_fields` contains `years_pm_experience` |

**Every case additionally asserts, without exception:**

- `assessed_level` is one of the four values — guaranteed by the schema, asserted anyway, because
  the schema is what we are testing
- **`level_rationale` contains at least one verbatim substring of eight or more words from the
  input resume.** This is how "cites specific resume content, not generic praise" becomes
  falsifiable instead of a matter of opinion
- Every entry in `scope_evidence` and `notable_outcomes` appears verbatim in the input. **A
  fabricated quote fails the case.** This is the single most important assertion in the file
- No em-dash in `level_rationale`
- No name, university, or nationality from the fixture appears in `level_rationale`

**Cases 5 through 8 are the ones with teeth.** Cases 1 to 4 mostly prove the thing works. An agent
that gets all four clear levels right and is confidently wrong on every ambiguous one is exactly
the failure this product cannot afford, because the ambiguous resumes are the ones where the
candidate most needs the flag.

### Tolerance, and why it is asymmetric

Clear cases assert an exact level. Ambiguous cases assert a *set* plus a populated
`low_confidence_fields`. **This is deliberate: on an ambiguous resume there is no single correct
level, so asserting one would encode my guess as ground truth and make the suite brittle for the
wrong reason.** What is genuinely assertable is that the agent noticed the ambiguity.

### Retry behaviour must be observed, not assumed

`deep` scores **7-9/10 on structured output and never 10/10** (DEV-STATE 2026-07-30), and its
failures return `None` rather than raising. **At least one golden case must record the observed
retry behaviour on `deep`**, with the real pass rate written into DEV-STATE. Run the set enough
times to see a retry actually fire. If it never fires across a full run, say so — that is data too,
and it is a claim nobody has yet been able to make.

---

## 6. The model question, still open

ARCHITECTURE §4 assigns `deep` to this agent. **On reliability grounds that assignment is
backwards** — `fast` is 10/10 on structured output at a ~7.2s median where `deep` is 7-9/10 at
9.2-20.4s. It was left alone deliberately, because `deep` was chosen for reasoning quality and no
quality comparison has ever been measured. Reassigning would trade an unmeasured property for a
measured one.

**These golden cases are the first real quality signal in the project.** Run the set against both
models and record both results. If `fast` matches `deep` on cases 5 to 8 — the ones needing actual
judgment — the assignment should change and Phase 2 should inherit that finding rather than
rediscovering it.

---

## 7. Failure modes to design against

| Failure | Why it matters | Guard |
|---|---|---|
| Confident level off a scanned resume with no text | Story 1.2 must have failed the upload first; if empty text reaches here the agent will still answer | Assert non-empty `resume_text` at the node boundary, fail loudly |
| Fabricated quotes in `scope_evidence` | Destroys the one property making the rationale checkable | Verbatim-substring assertion in every golden case |
| Never uncertain | Ambiguous resumes get a confident wrong level and the candidate has no signal to correct it | Cases 5-8 |
| Levels on years alone | Gameable, and wrong for career changers and founders | Rubric weights scope over tenure; cases 6 and 8 |
| Levels on prestige | Unfair and wrong | Named in the prompt constraints |
| Double execution across the interrupt | `confirm_level` re-runs its node from the top on resume | Story 1.4 asserts a single call **against `app/llm.py`'s call log**, never against state |

---

## 8. Open questions

- **Does `low_confidence_fields` name schema field names or human labels?** Story 1.6 renders these
  next to fields in the confirmation UI. Field names are easier to bind to, human labels are easier
  to read. Decide when 1.6 is built; record it here.
- **Should the candidate's correction at `confirm_level` be fed back to this agent?** Currently no,
  and it should stay no in V1 — the candidate's stated level simply wins. Revisit only if
  corrections turn out to cluster in one direction, which would mean the rubric is miscalibrated.
