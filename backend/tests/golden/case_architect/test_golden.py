"""Golden-case suite for the Case Architect agent. Run with
`make golden AGENT=case_architect` or `pytest tests/golden/case_architect -v`.

Hits the real Groq endpoint (`@pytest.mark.live`) once per case against
`app.agents.case_architect.generate_case_world`. Seven fixed
`(assessed_level, candidate_profile)` inputs spanning all four levels, per
AGENT-CASE-ARCHITECT-SPEC.md §5, checked against the universal assertions
§5 specifies (apply to every case, no exceptions) plus the case table in
`cases.py`.

CRITICAL -- collection must stay clean: `app.agents.case_architect` does not
exist yet as this suite is written (story 2.2; the agent is story 2.3's
job). A module-level `from app.agents.case_architect import ...` would make
`pytest tests -m "not live"` ERROR during collection -- deselection happens
after collection, so it would not save this file, it would break the
project's fastest feedback loop for every file. The import is therefore
lazy, inside the session-scoped `generate_case_world` fixture below:
collection succeeds unconditionally, and only actually running a `live` test
raises (loudly, as `ModuleNotFoundError`, naming exactly the missing
module).

Deliberately NOT `pytest.importorskip`: once `app.agents.case_architect`
exists but is misnamed or mis-exported, `importorskip` would silently skip
forever, and a silently-skipped golden suite is worse than no suite --
nobody would notice the gate stopped gating. See resume_analyst's identical
choice (story 1.3a).

Role: `GOLDEN_ROLE` env var, "deep" default (ARCHITECTURE §4 / spec §6),
"fast" opt-in so the orchestrator can re-run this identical set against the
other model without touching this file.
"""
from __future__ import annotations

import asyncio
import logging
import os

import pytest

from tests.golden.case_architect.assertions import (
    banned_round_numbers,
    blank_or_short_fields,
    contains_banned_register_name,
    count_out_of_range,
    implied_acv_implausible,
    organic_ratio_below_floor,
    stage_employee_mismatch,
)
from tests.golden.case_architect.cases import CASES

GOLDEN_ROLE = os.environ.get("GOLDEN_ROLE", "deep")
print(f"\n[golden/case_architect] GOLDEN_ROLE={GOLDEN_ROLE}")

pytestmark = pytest.mark.live


@pytest.fixture(scope="session")
def generate_case_world():
    """Imported here, not at module level -- see module docstring."""
    from app.agents.case_architect import generate_case_world as fn

    return fn


# Groq's binding limit is TOKENS per minute, not requests: 8000 TPM on the
# gpt-oss models (measured on resume_analyst, 2026-07-31; same bucket, per
# CLAUDE.md's "Not NVIDIA NIM" note, since both agents call `get_llm`).
# `app/llm.py` sets max_tokens=4096 (confirmed, line ~264).
#
# This agent's prompt does not exist yet (story 2.3), so unlike
# resume_analyst's PACE (which rounds a value observed from a real
# `Requested` header), this pacing is computed from a projected worst case
# and carries a larger safety margin as a result.
#
# Assumptions, stated explicitly per the brief:
#   - chars/token ~= 4.2, resume_analyst's own measured ratio (~12,200 chars
#     / ~2,900 prompt tokens). No case_architect-specific measurement exists
#     yet, so this is inherited, not re-derived.
#   - candidate_profile input tokens: measured directly from this package's
#     own fixtures, not guessed. The largest (`gpm_portfolio.json`)
#     serializes its `candidate_profile` dict to 521 compact-JSON chars =~
#     124 tokens at 4.2 chars/token. Padded to 200 tokens for the
#     `assessed_level` field plus whatever framing text the eventual human
#     message adds around the JSON (e.g. "Assessed level: ...\n\nCandidate
#     profile:\n...").
#
# Budget: prompt_tokens + input_tokens + max_tokens(4096) < 8000
#      => prompt_tokens < 3904 - 200 = 3704
#      => max prompt size at 4.2 chars/token ~= 3704 * 4.2 ~= 15,557 chars.
# Close to, not materially different from, the brief's own ~15,100-char
# estimate (which assumed a heavier 300-token input) -- the 450-char gap is
# fully explained by the measured-vs-assumed input estimate, not a
# disagreement about the ceiling's shape. This is a HARD CEILING for story
# 2.3's prompt, not a target: spec §6 already states the schema is large
# enough that the prompt will exceed resume_analyst's ~12,200 chars, so
# there is headroom, but not much (~3,300 chars, ~27%).
#
# Pacing: refill rate is 8000/60 = 133.3 tokens/sec. Worst case, a call at
# the computed ceiling requests close to prompt_tokens(3704) +
# input_tokens(200) + max_tokens(4096) ~= 8000 -- i.e. up against the bucket
# by construction. Using a conservative Requested ~= 7900:
#   7900 / 133.3 ~= 59.3s to refill room for the next call.
# resume_analyst rounded a MEASURED 56.5s up to 60s (~6% margin) because it
# had an observed `Requested` header to round from. This figure is a
# pre-launch projection, not an observation, so it carries a much larger
# margin: 90s, not 60s. Revisit once story 2.3 exists and a real `Requested`
# value can replace this projection, the same way resume_analyst's 30s
# guess was replaced by its measured 60s on 2026-08-01.
_PACE_SECONDS = 90


@pytest.fixture(autouse=True)
async def _pace_for_tokens_per_minute():
    yield
    await asyncio.sleep(_PACE_SECONDS)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_golden_case(case, generate_case_world, caplog) -> None:
    with caplog.at_level(logging.INFO, logger="app.llm"):
        result = await generate_case_world(
            case.assessed_level, case.candidate_profile, role=GOLDEN_ROLE
        )

    # Same retry-observation shape as resume_analyst's golden suite: reads
    # the log this call already produced, no extra LLM call, and covers both
    # outcomes `_LoggedStructured` logs on a retry (`outcome=empty` for
    # `deep` returning None, `outcome=invalid` for a ValidationError).
    retried = any(
        "outcome=empty" in r.getMessage() or "outcome=invalid" in r.getMessage()
        for r in caplog.records
        if r.name == "app.llm"
    )
    print(f"[golden/case_architect] {case.id}: role={GOLDEN_ROLE} retry_fired={retried}")

    # --- Universal assertions, spec §5's table, apply to every case ---

    # Vacuity floor first, same ordering logic as resume_analyst: every
    # other assertion below can pass trivially against an empty field, so
    # silence has to be caught before it can hide behind them.
    string_fields = {
        "company.name": result.company.name,
        "company.one_line": result.company.one_line,
        "market.description": result.market.description,
        "situation.prompt": result.situation.prompt,
        "situation.tension": result.situation.tension,
        "situation.leadership_belief": result.situation.leadership_belief,
    }
    empty = blank_or_short_fields(string_fields)
    assert not empty, f"{case.id}: vacuity floor -- fields empty or near-empty: {empty}"

    assert result.supporting_facts, f"{case.id}: supporting_facts is empty"
    assert not count_out_of_range(result.supporting_facts, 8, 15), (
        f"{case.id}: supporting_facts has {len(result.supporting_facts)} entries, want 8-15"
    )
    assert not count_out_of_range(result.market.competitors, 2, 4), (
        f"{case.id}: competitors has {len(result.market.competitors)}, want 2-4"
    )
    assert not count_out_of_range(result.situation.options, 2, 3), (
        f"{case.id}: options has {len(result.situation.options)}, want 2-3"
    )

    percentages = {
        "market.growth_rate_pct": result.market.growth_rate_pct,
        "metrics.yoy_growth_pct": result.metrics.yoy_growth_pct,
        "metrics.gross_margin_pct": result.metrics.gross_margin_pct,
        "metrics.monthly_churn_pct": result.metrics.monthly_churn_pct,
    }
    dollar_amounts = {
        "market.size_usd": result.market.size_usd,
        "metrics.arr_usd": result.metrics.arr_usd,
    }
    round_violations = banned_round_numbers(percentages, dollar_amounts)
    assert not round_violations, f"{case.id}: fake-round number(s): {round_violations}"
    assert not organic_ratio_below_floor(percentages), (
        f"{case.id}: too many round-looking percentages across the world: {percentages}"
    )

    # Schema §2 has no dedicated "person" field -- a banned placeholder
    # person name (the "John Doe" half of spec §5's positive control) can
    # only appear inside free text: supporting_facts or leadership_belief.
    # contains_banned_register_name does a substring match, so it doubles as
    # a free-text scanner here, not just a name-list check.
    names_and_text = (
        [result.company.name]
        + [c.name for c in result.market.competitors]
        + list(result.supporting_facts)
        + [result.situation.leadership_belief]
    )
    leaked = contains_banned_register_name(*names_and_text)
    assert leaked is None, f"{case.id}: banned-register name leaked: {leaked!r}"

    assert not stage_employee_mismatch(result.company.stage, result.company.employees), (
        f"{case.id}: {result.company.employees} employees implausible for "
        f"stage {result.company.stage!r}"
    )
    assert not implied_acv_implausible(result.metrics.arr_usd, result.metrics.customer_count), (
        f"{case.id}: implied ACV implausible: arr={result.metrics.arr_usd} "
        f"customers={result.metrics.customer_count}"
    )

    # --- Case-specific assertion, spec §5's table ---
    case.check(result)
