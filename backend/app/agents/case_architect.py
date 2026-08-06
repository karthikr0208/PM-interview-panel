"""Case Architect — builds the fictional company, market, and strategic
situation a candidate is interviewed about. `case_world` is written exactly
once and read by every agent downstream (ARCHITECTURE §2); this agent's
output is load-bearing history, not a draft.

Pure function, no side effects. `generate_case_world` performs no database
writes and emits no `agent_events` rows — those belong to the
`generate_case_world` *node* in `app/graph/build.py`, exactly as
`analyse_resume` and `level_candidate` are split (see that module's
docstring). Golden cases call this function directly with no session and no
database, so a DB call in here would break every one of them.

See docs/specs/agents/AGENT-CASE-ARCHITECT-SPEC.md for the full contract.
"""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel

from app.llm import Role, get_llm


class Competitor(BaseModel):
    name: str
    positioning: str  # one line, how they win
    relative_strength: str  # where they beat us, honestly


class Company(BaseModel):
    name: str
    one_line: str  # what it sells, to whom
    stage: Literal["seed", "series_a", "series_b", "series_c", "growth", "public"]
    employees: int
    founded_year: int


class Market(BaseModel):
    description: str
    size_usd: str  # "$3.2B" — organic, never "$1B"
    growth_rate_pct: float
    competitors: list[Competitor]  # 2-4


class BusinessMetrics(BaseModel):
    arr_usd: str
    yoy_growth_pct: float
    gross_margin_pct: float
    monthly_churn_pct: float
    customer_count: int


class StrategicSituation(BaseModel):
    prompt: str  # what the candidate is asked to decide
    tension: str  # why it is genuinely hard
    options: list[str]  # 2-3 defensible directions, none obviously right
    constraints: list[str]  # budget, headcount, timeline, tech debt
    leadership_belief: str  # what the exec team currently thinks, which may be wrong


class CaseWorld(BaseModel):
    company: Company
    market: Market
    metrics: BusinessMetrics
    situation: StrategicSituation
    supporting_facts: list[str]  # 8-15 atomic, verifiable statements
    # PHASE-3.5-SPEC.md 3.5.2: curated worlds describe REAL companies, whose
    # facts go stale in a way a generated world's never do -- OpenAI and
    # Anthropic move faster than the other six curated worlds combined.
    # Shown to the candidate verbatim ("This brief reflects public
    # information as of <as_of>. Treat it as ground truth for this
    # interview.") so staleness is disclosed rather than silently wrong.
    # Left "" for agent-generated worlds, which have no real-world date to
    # anchor to -- generate_case_world's prompt is unchanged by this story.
    as_of: str = ""
    # PHASE-3.5-SPEC.md 3.5.3: which of the Planner's four question
    # categories (strategy | gtm | pricing | growth) this world's
    # `situation.prompt` actually supports -- 2-3 per curated world, chosen
    # by reading the situation honestly (asking a pricing question about
    # Reddit's AI-licensing tension would be a bad interview). Consumed by
    # `app.questions.shapes.select_shape_for_world`, deterministic Python,
    # no LLM call. Left [] for agent-generated worlds, exactly like `as_of`
    # above -- `select_category` falls back to the full category set when
    # this is empty, so the untouched generative path keeps working.
    suits_categories: list[str] = []


# One block, not built up piecemeal — see resume_analyst.py's identical
# reasoning: every constraint the golden suite checks (fake-round numbers,
# banned names, internal consistency, level scope) has to stay visible in one
# place so it cannot silently drop out of a future edit.
_SYSTEM_PROMPT = """You are the Case Architect for a PM interview simulator. Build a fictional \
company, market, and strategic situation for the candidate's interview. Answer directly with the \
JSON object; do not deliberate at length before answering. `case_world` is written once and read \
by every later agent, so it must be complete and internally consistent on the first try.

SCOPE BY LEVEL for `situation.prompt`:
- APM: one feature or surface, clear owner above. "Should we add guest checkout to the signup \
flow?"
- PM: one product area end to end, including what NOT to build.
- Senior PM: a product line or domain with real ambiguity, no playbook.
- GPM: multiple products or a portfolio, with a business outcome attached (revenue, headcount, \
market position).
Do not use single-surface language ("this feature/screen/flow") in a GPM prompt, and do not use \
portfolio language ("portfolio", "across our products", "business unit") in an APM or PM prompt.

DOMAIN: use the candidate profile's domains/product types/company contexts for flavor, not \
difficulty. Sparse profile: still build a complete, specific world. The company must never be the \
candidate's real employer and must never be a real company.

NUMBERS, mechanically checked: every percentage (growth_rate_pct, yoy_growth_pct, \
gross_margin_pct, monthly_churn_pct) needs an organic decimal, e.g. 31.4, 18.2, 22.7 — never a \
round value like 20.0, 30.0, 50.0, 100.0. Every dollar figure (size_usd, arr_usd) needs a decimal \
mantissa, e.g. "$4.7M", "$3.2B" — never "$1M".

NAMES: never use "Acme", "TechCorp", "Globex", "Initech", "John Doe", "Jane Doe", "Sarah Chan", or \
that register, for the company, a competitor, or any named person. Give the company and every \
competitor a two-word name (e.g. "Verdant Ledger", "Northline Analytics"), never a single word.

NEVER USE AN ALGEBRA PLACEHOLDER as the name of anything: no "feature X", "Product A", \
"Competitor B", "the X feature". Every feature, product and team named anywhere, and especially in \
supporting_facts and situation.prompt, gets a real specific name ("guest checkout", "saved \
filters", "the referral widget"). A candidate reads these strings.

CONSISTENCY, briefly: employees fit stage (seed 1-40, series_a 5-120, series_b 30-400, series_c \
100-1200, growth 200-5000, public 300+). arr_usd / customer_count is a plausible ACV for the stage \
AND the market: a few dollars per user is right for a consumer product with millions of users, \
thousands per account is right for B2B with hundreds of customers, and the two must not be mixed. \
monthly_churn_pct and yoy_growth_pct do not contradict (heavy churn plus triple-digit growth does \
not close). Numbers in supporting_facts match the same numbers in market/metrics.

supporting_facts: 8-15 short, atomic, specific statements a candidate could ask about, e.g. "the \
enterprise tier is 61.4% of revenue but 12.1% of logos" — never vague color.

market.competitors: 2-4, each with one real reason it wins (relative_strength), not a strawman.

situation.options: 2-3 defensible directions, none obviously right. situation.tension: why the \
choice is genuinely hard, grounded in this world's numbers. situation.leadership_belief: what \
the exec team currently believes, which may be wrong.

No em-dash or en-dash anywhere; use a comma or "and" instead. Every string field must be \
substantive, never a placeholder or single word.
"""


async def generate_case_world(
    assessed_level: str, candidate_profile: dict, *, role: Role = "fast"
) -> CaseWorld:
    """Builds a level-appropriate `CaseWorld` for `assessed_level`, informed
    by (but never overridden by) `candidate_profile`. Pure function: no DB,
    no session, no side effects — see module docstring.

    `assessed_level` must be the CONFIRMED level from graph state, never
    inferred from `candidate_profile` — the caller (the `generate_case_world`
    node) is responsible for reading it from `state["assessed_level"]`, which
    `confirm_level` may have overwritten with the candidate's correction.
    This function has no way to check that; it only ever uses the level it
    is handed.

    Raises `ValueError` on an empty `assessed_level` rather than silently
    building an unscoped world.
    """
    if not assessed_level or not assessed_level.strip():
        raise ValueError("generate_case_world requires a non-empty assessed_level")

    llm = get_llm(role).with_structured_output(CaseWorld)
    messages = [
        ("system", _SYSTEM_PROMPT),
        (
            "human",
            "Assessed level: "
            + assessed_level
            + "\n\nCandidate profile:\n"
            + json.dumps(candidate_profile, indent=2),
        ),
    ]
    return await llm.ainvoke(messages)
