# Agent spec — Case Architect

> **🔴 THIS AGENT NO LONGER RUNS IN PRODUCTION, as of story 3.5.4, 2026-08-06. Read this box before
> anything below it.**
>
> `generate_case_world` in `app/graph/build.py` calls **`select_case_world`** (`app/cases/`), which
> picks one of **eight hand-written fact sheets about real companies** — Reddit, Duolingo, YouTube,
> Airbnb, Figma, Cursor, OpenAI, Anthropic. Deterministic Python, no LLM, **zero tokens per
> interview**. Karthik's call of 2026-08-06, and the reason is the phase's whole point: a candidate
> has real intuition about a real company and none about an invented one.
>
> | | |
> |---|---|
> | **The generative agent** | Still in the tree, still tested, **deliberately not deleted** |
> | **Its 7 golden cases + 47 assertion tests** | Still run — now the more valuable direction: a hand-built world a human considers good, passing these assertions, is a **positive control on the assertions themselves** |
> | **Everything below about the prompt** | Describes an agent that no longer runs in an interview. Read it as the record of how the generative path was built, not as current runtime behaviour |
> | **`suits_categories`** | New field on each curated world. It scopes which question shapes a world can take, so nothing can ask a pricing question about Reddit's AI-licensing tension. **Non-empty at runtime for the first time as of this story** |
>
> **The round-number assertion now runs against reality**, and that changes what a failure means.
> `is_round_dollar_amount` was written to catch a model reaching for `$150M`. If a **real** public
> figure happens to be round, **the assertion is wrong and the data is right** — widen the assertion,
> do not distort a real number to satisfy a test written for a generative failure mode.
>
> The node keeps every side effect it always had: the `agent_events` start/done rows and the
> `case_worlds` audit insert. `case_world` is still written exactly once and still immutable.

**Written 2026-08-02, before the prompt exists**, per the story 1.3 split. The golden fixtures in
story 2.2 are written against this document and blind to the prompt, so the prompt cannot be tuned
against them.

**Status:** contract only. `app/agents/case_architect.py` does not exist yet (story 2.3).

**This agent produces the artifact the rest of the product is built on.** `case_world` is written
exactly once and read by every agent downstream (ARCHITECTURE §2). It is what stops the Interviewer
contradicting itself when a candidate asks a clarifying question forty minutes in. Every other
agent can be re-run; this one's output is load-bearing history.

---

## 1. Contract

| | |
|---|---|
| **Reads from state** | `assessed_level: str` (the **confirmed** level) · `candidate_profile: dict` |
| **Writes to state** | `case_world: dict` |
| **Side effects** | One `agent_events` row on start and on completion. One `case_worlds` insert |
| **Immediately preceded by** | `confirm_level`, whose resume value overwrites `assessed_level` |
| **Immediately followed by** | `plan_interview`, which reads `case_world` and must not write it |
| **Model** | `deep`, per ARCHITECTURE §4. Names come from `app/config.py`, never from ARCHITECTURE |

**The agent function is pure.** `generate_case_world(assessed_level, candidate_profile, *, role)`
takes values and returns a validated `CaseWorld`. **No database, no session, no `agent_events`.**
Those belong to the node, exactly as `analyse_resume` and `level_candidate` are split. The golden
cases call the function directly with no database, so a DB call inside it breaks every case at once.

**🔴 Read `assessed_level` from state, never level information from `candidate_profile`.**
`confirm_level` writes the candidate's correction into `assessed_level`. An agent that infers the
level from the profile instead would silently ignore every correction, **and no golden case would
catch it**, because golden cases pass a level directly and never exercise the correction path.
Story 2.3 asserts this separately for that reason.

---

## 2. Output schema

Sketch, not final code. Story 2.3 implements it; story 2.2 writes assertions against it.

```python
class Competitor(BaseModel):
    name: str
    positioning: str              # one line, how they win
    relative_strength: str        # where they beat us, honestly

class Company(BaseModel):
    name: str
    one_line: str                 # what it sells, to whom
    stage: Literal["seed", "series_a", "series_b", "series_c", "growth", "public"]
    employees: int
    founded_year: int

class Market(BaseModel):
    description: str
    size_usd: str                 # "$3.2B" — organic, never "$1B"
    growth_rate_pct: float
    competitors: list[Competitor] # 2-4

class BusinessMetrics(BaseModel):
    arr_usd: str
    yoy_growth_pct: float
    gross_margin_pct: float
    monthly_churn_pct: float
    customer_count: int

class StrategicSituation(BaseModel):
    prompt: str                   # what the candidate is asked to decide
    tension: str                  # why it is genuinely hard
    options: list[str]            # 2-3 defensible directions, none obviously right
    constraints: list[str]        # budget, headcount, timeline, tech debt
    leadership_belief: str        # what the exec team currently thinks, which may be wrong

class CaseWorld(BaseModel):
    company: Company
    market: Market
    metrics: BusinessMetrics
    situation: StrategicSituation
    supporting_facts: list[str]   # 8-15 atomic, verifiable statements
```

**🔴 `supporting_facts` is the most important field in this schema and the least obvious.** It is
the body of fact the Interviewer answers clarifying questions from in Phase 3. Without it, a
clarifying question forces the Interviewer to improvise, which is ARCHITECTURE §9's
"Interviewer contradicts the case world" failure — a failure whose only listed detection is manual.
**Each entry must be atomic and answerable**, in the register of "the enterprise tier is 61% of
revenue but 12% of logos", not "the company is doing well."

---

## 3. Scope scales with the confirmed level

The same schema, but the *situation* must match what someone at that level is actually asked to
decide. A GPM given an APM's feature question is not being interviewed; neither is the reverse.

| Level | `situation.prompt` is about | Typical shape |
|---|---|---|
| **APM** | One feature or surface, with a clear owner above | "Should we build X into the onboarding flow, given Y?" |
| **PM** | One product area, end to end, including what not to do | "Our activation rate is falling in one segment. What do you do?" |
| **Senior PM** | A product line or a domain with real ambiguity | "A competitor just bundled our core feature for free. Respond." |
| **GPM** | Multiple products or a portfolio, with a business outcome attached | "Two of our four products are growing. Where does next year's headcount go?" |

**`candidate_profile` informs the domain, not the difficulty.** A candidate whose profile is
fintech should get a business they can reason about, which makes the interview about their thinking
rather than their vocabulary. **It must not produce their actual employer** — that turns a case
into a memory test and risks the model asserting facts about a real company.

---

## 4. Constraints on the prompt

**These two are design rules that reach past the UI into this agent** (v1 §7 via CLAUDE.md and
ARCHITECTURE §8), and they bind harder here than anywhere else in the product, because this is the
first agent whose output a candidate must read as fiction and believe.

**No fake-round numbers.** `50%`, `$1M`, `99.99%`, `100 employees` are tells. Generated figures
must be organic: `31.4%` market share, `$4.7M` ARR, `18.2%` churn, `147 employees`.

**No generic placeholder names.** "John Doe", "Sarah Chan", "Acme", "TechCorp" and that whole
register are banned — for the company, competitors, and any person named in a fact.

**Both are mechanically assertable and MUST be asserted, not left to prompt prose.** Story 1.2
shipped three em-dashes into candidate-facing copy despite the rule being written down; no test
caught it until one was written. A rule in a prompt is a hope. See §7.

Also binding:
- **No real companies.** Not the candidate's employer, not a household name. A generated world that
  makes claims about Stripe's margins is both wrong and a liability.
- **The situation must have no obviously correct answer.** If one of `options` dominates, the
  interview measures reading comprehension. The tension is the point.
- **Internal consistency over richness.** A world with six coherent facts beats one with twenty
  that contradict.

---

## 5. Golden cases

**Written blind in story 2.2, against this table.** Input is `(assessed_level, candidate_profile)`.

| # | Fixture | Input | Asserts |
|---|---|---|---|
| 1 | `apm_consumer` | APM, consumer mobile profile | Situation is single-feature scope · all universal assertions |
| 2 | `pm_b2b_saas` | PM, B2B SaaS profile | Situation is one product area end to end |
| 3 | `senior_pm_platform` | Senior PM, platform/infra profile | Situation carries real ambiguity, not a feature choice |
| 4 | `gpm_portfolio` | GPM, multi-product profile | Situation spans products and names a business outcome |
| 5 | `sparse_profile` | PM, profile with almost nothing in it | **Still produces a complete, consistent world.** The agent must not degrade into vagueness when under-informed |
| 6 | `fintech_domain` | Senior PM, fintech profile | Domain is recognisably fintech · **the company is NOT the candidate's employer** |
| 7 | `career_changer` | PM, engineer-in-transition profile | Domain does not assume PM-native vocabulary |

**Universal assertions, applied to every case.** These are the suite, and each needs a positive
control proving it can fail:

| Assertion | Positive control that must go RED |
|---|---|
| No fake-round numbers in any numeric field | A world with `50.0%` growth and `$1M` ARR |
| No banned-register names | A world whose company is "Acme" or a person is "John Doe" |
| `supporting_facts` has 8-15 entries | A world with 2 facts, and one with 40 |
| `competitors` has 2-4 entries | A world with 0 competitors |
| `options` has 2-3 entries | A world with 1 option, which has no tension |
| **Internal consistency** — see below | A world whose numbers contradict each other |
| **Vacuity floor** — every string field non-empty and above a minimum length | A world of empty strings and empty lists |

**🔴 THE VACUITY FLOOR IS NOT OPTIONAL, AND IT IS THE LESSON OF STORY 1.3a.** There,
`missing_verbatim_quotes([])` returned `[]`, so an agent that quoted **nothing** passed the suite's
single most important assertion on all eight cases. **Silence beat effort.** Every denial assertion
in this suite must be paired with a check that the field had content to deny in the first place.

### Internal consistency, the assertion with teeth

The failure that will actually embarrass this product is a world that contradicts itself — 40
employees in one field and a 200-person sales org in a supporting fact. **Assert cross-field
relationships the schema cannot express:**

- **Implied ACV** — `arr_usd / customer_count` must be plausible for the stated stage and market.
  A seed company with 2 customers and `$40M` ARR is not a business.
- **Stage against employees** — a seed company with 900 employees, or a public company with 11.
- **Churn against growth** — `monthly_churn_pct` of 9% alongside `yoy_growth_pct` of 140% is
  arithmetic that does not close.
- **Facts against fields** — a number appearing in `supporting_facts` that contradicts the same
  number in `metrics`.

**Start with the two cheapest (stage/employees, implied ACV) and add the rest as they earn their
keep.** An over-strict consistency check that rejects legitimate worlds is worse than none, because
it gets relaxed rather than fixed — and the assertion is what usually gets relaxed.

---

## 6. The model question

ARCHITECTURE §4 assigns `deep`. **This is the second agent to produce evidence on whether that is
right**, and Phase 1 named it as the tiebreak when it accepted three flapping Resume Analyst cases
on 2026-08-02.

**Kept informal by decision, 2026-08-02.** There is no acceptance box forcing a dual-model run.
But if this agent's golden cases flap the way the Resume Analyst's do, that is evidence the
variance is the **model**, not the prompt — which is one of the four conditions that reopens
Phase 1's accepted flaps. **Record the flap counts honestly, whatever they are.**

**Prompt length matters more here than anywhere yet.** This schema is large and the constraints are
many, so the prompt will exceed the Resume Analyst's ~12,200 characters. Two consequences, both
measured on this project: **`_PACE_SECONDS` must be recomputed** against the 8,000 TPM bucket rather
than inherited, and NVIDIA's failure mode is a reminder that long prompts break serving stacks in
ways that look like agent bugs.

---

## 7. Failure modes to design against

| Failure | Why it matters | Guard |
|---|---|---|
| **A second write to `case_world`** | Breaks the immutability rule the whole architecture rests on | Story 2.3 asserts it by **attempting a second write and confirming rejection**, never by inspection |
| **Reads level from `candidate_profile`** | Silently discards the candidate's correction; no golden case would catch it | Story 2.3 asserts the correction path explicitly |
| Fake-round numbers | A candidate reads the world as generated and stops believing it | Regex assertion, with a positive control |
| Generic names | Same, and it is the most recognisable AI tell in the list | Banned-register list, with a positive control |
| Self-contradiction | Surfaces in Phase 3 as the Interviewer improvising, whose only listed detection is manual | Cross-field consistency assertions, §5 |
| Thin `supporting_facts` | Phase 3's clarifying questions have nothing to draw on, so the Interviewer invents | 8-15 count assertion plus the vacuity floor |
| The candidate's real employer | Turns a reasoning test into a memory test, and risks false claims about a real company | Fixture 6 asserts it |
| An obviously correct option | The case stops measuring judgment | `options` count, and a human read at the phase gate |
| Degrading on a sparse profile | The agent has least information exactly when a real candidate is hardest to read | Fixture 5 |

---

## 8. Open questions

- **Does `case_world` need a `difficulty` field**, or is level-appropriate scope enough? Deferred
  until Phase 3 shows whether the Interviewer needs it.
- **Should `supporting_facts` be structured** (`{claim, category}`) rather than strings? Strings
  first; structure only if Phase 3's clarifying-question matching needs it. No new abstractions
  without a second caller.
- **How much of `candidate_profile` should reach the prompt?** Passing all of it risks the world
  mirroring the resume back. Start with domain and level only, and widen only with evidence.
- **Is a fake-round-number regex too blunt?** `20%` may be a legitimate gross margin. The suite
  should reject a *small banned set* plus require most numeric fields to carry a decimal, rather
  than banning every round figure. Tune against the positive control, not against a failing case.
