"""Golden-case suite for the Resume Analyst agent. Run with
`make golden AGENT=resume_analyst` or `pytest tests/golden/resume_analyst -v`.

Hits the real NVIDIA endpoint (`@pytest.mark.live`) once per case against
`app.agents.resume_analyst.analyse_resume`. Eight fixed resumes spanning the
four levels and the four uncertainty modes from AGENT-RESUME-ANALYST-SPEC.md
§5, checked against the case table in `cases.py` plus the universal
assertions §5 also specifies (apply to every case, no exceptions).

CRITICAL -- collection must stay clean: `app.agents.resume_analyst` does not
exist yet as this suite is written (story 1.3a; the agent is story 1.3b's
job). A module-level `from app.agents.resume_analyst import ...` would make
`pytest tests -m "not live"` ERROR during collection -- deselection happens
after collection, so it would not save this file, it would break the
project's fastest feedback loop for every file. The import is therefore
lazy, inside the session-scoped `analyse_resume` fixture below: collection
succeeds unconditionally, and only actually running a `live` test raises
(loudly, as ImportError, naming exactly the missing module).

Deliberately NOT `pytest.importorskip`: once `app.agents.resume_analyst`
exists but is misnamed or mis-exported, importorskip would silently skip
forever, and a silently-skipped golden suite is worse than no suite --
nobody would notice the gate stopped gating.

Role: `GOLDEN_ROLE` env var, "deep" default (ARCHITECTURE §4 / spec §6),
"fast" opt-in so the orchestrator can re-run this identical set against the
other model without touching this file. Never parametrize over both in one
run within a single test session -- that doubles the cost against the 40
requests/minute ceiling for no benefit within a single invocation.
"""
from __future__ import annotations

import asyncio
import logging
import os

import pytest

from tests.golden.resume_analyst.assertions import (
    contains_forbidden_token,
    empty_quote_lists,
    missing_verbatim_quotes,
    no_dash_variants,
    rationale_cites_resume,
)
from tests.golden.resume_analyst.cases import CASES, FOUR_LEVELS

GOLDEN_ROLE = os.environ.get("GOLDEN_ROLE", "deep")
print(f"\n[golden/resume_analyst] GOLDEN_ROLE={GOLDEN_ROLE}")

pytestmark = pytest.mark.live


@pytest.fixture(scope="session")
def analyse_resume():
    """Imported here, not at module level -- see module docstring."""
    from app.agents.resume_analyst import analyse_resume as fn

    return fn


# Groq's binding limit is TOKENS per minute, not requests: 8000 TPM on the
# gpt-oss models, measured from x-ratelimit-* headers 2026-07-31.
#
# This paces the suite and changes NO assertion. A 429 here is a property of
# the free tier, not of the agent, and letting it fail a case would encode
# "the endpoint was busy" as "the prompt is wrong".
#
# 60s, not the 30s this started at, and the arithmetic is the reason. The
# prompt grew to ~2900 tokens, so a single case now REQUESTS about 7500
# against an 8000 bucket that refills at 8000/60 = 133 tokens per second:
# ~56s to make room for the next call. 30s could not work, and did not --
# cases 06 and 08 both 429'd mid-suite on 2026-08-01 and were recorded as
# failures until the messages were read. Observed both times:
#   "Limit 8000, Used 1177, Requested 7516"   <- refill, not our usage
# Raise this in step with the prompt, or the suite silently stops measuring
# the last cases in the run.
_PACE_SECONDS = 60


@pytest.fixture(autouse=True)
async def _pace_for_tokens_per_minute():
    yield
    await asyncio.sleep(_PACE_SECONDS)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_golden_case(case, analyse_resume, caplog) -> None:
    resume_text = case.resume_text

    with caplog.at_level(logging.INFO, logger="app.llm"):
        result = await analyse_resume(resume_text, role=GOLDEN_ROLE)

    # Spec §5 / AGENT-RESUME-ANALYST-SPEC.md §5: "at least one golden case
    # must record the observed retry behaviour on `deep`". Recorded on every
    # case rather than a single designated one -- cheap (it's reading the
    # log this call already produced, not an extra LLM call) and gives real
    # coverage of whether a retry ever actually fires across a full run.
    # Matches BOTH outcomes that trigger a retry in `_LoggedStructured`:
    # `outcome=empty` for `deep` returning None (its documented failure mode)
    # and `outcome=invalid` for a pydantic ValidationError. Matching only the
    # first under-reports retries and would have let this file record
    # "retry never fired" while retries were firing. Found 2026-07-31 by
    # reading llm.py's actual log vocabulary rather than the brief's.
    retried = any(
        "outcome=empty" in r.getMessage() or "outcome=invalid" in r.getMessage()
        for r in caplog.records
        if r.name == "app.llm"
    )
    print(f"[golden/resume_analyst] {case.id}: role={GOLDEN_ROLE} retry_fired={retried}")

    # --- Universal assertions, spec §5, apply to every case without exception ---

    # Guaranteed by the Literal in the schema; asserted anyway because the
    # schema itself is what this suite is testing.
    assert result.assessed_level in FOUR_LEVELS, result.assessed_level

    assert rationale_cites_resume(result.level_rationale, resume_text), (
        f"{case.id}: level_rationale cites nothing verbatim (8+ words) from the resume:\n"
        f"{result.level_rationale!r}"
    )

    # The floor under the two verbatim checks below. Without it an agent that
    # returns no quotes at all passes both of them vacuously -- proven against
    # all eight cases before this line existed. See assertions.empty_quote_lists.
    empty_lists = empty_quote_lists(
        result.candidate_profile.scope_evidence,
        result.candidate_profile.notable_outcomes,
        expect_outcomes=case.expect_outcomes,
    )
    assert not empty_lists, (
        f"{case.id}: {empty_lists} came back empty. The verbatim-quote assertions below "
        f"pass trivially on an empty list, so silence must fail here instead."
    )

    fabricated_scope = missing_verbatim_quotes(
        result.candidate_profile.scope_evidence, resume_text
    )
    assert not fabricated_scope, (
        f"{case.id}: fabricated scope_evidence quote(s), not present verbatim in the "
        f"resume: {fabricated_scope}"
    )

    fabricated_outcomes = missing_verbatim_quotes(
        result.candidate_profile.notable_outcomes, resume_text
    )
    assert not fabricated_outcomes, (
        f"{case.id}: fabricated notable_outcomes quote(s), not present verbatim in the "
        f"resume: {fabricated_outcomes}"
    )

    assert no_dash_variants(result.level_rationale), (
        f"{case.id}: em-dash or en-dash in level_rationale: {result.level_rationale!r}"
    )

    leaked = contains_forbidden_token(result.level_rationale, list(case.forbidden_tokens))
    assert leaked is None, (
        f"{case.id}: forbidden token {leaked!r} (name/university/nationality) leaked "
        f"into level_rationale: {result.level_rationale!r}"
    )

    # --- Case-specific assertion, spec §5's table ---
    case.check(result)
