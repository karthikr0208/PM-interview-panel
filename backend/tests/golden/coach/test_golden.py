"""Golden-case suite for the Coach agent. Run with `make golden AGENT=coach` or
`pytest tests/golden/coach -v` (NOT under `-m "not live"` -- see below).

Unlike the Evaluator/Planner/Interviewer suites at their own story-1 time, the
Coach (`app/agents/coach.py`, Phase 5) already exists when this suite is written --
this file is not written blind and is not expected to be red, so `generate_coach_report`
is imported at module level rather than lazily inside a fixture.

Marked `pytest.mark.live` for the same reason as every other golden suite:
`pytest tests -m "not live"` DESELECTS this whole file, so it costs ZERO of the
exhausted `fast` daily budget.
"""
from __future__ import annotations

import asyncio
import logging
import os

import pytest

from app.agents.coach import IMPROVEMENTS_PER_REPORT, generate_coach_report, verify_anchors
from tests.golden.coach.assertions import blank_or_short_fields, dashes_in_text, duplicate_drills
from tests.golden.coach.cases import CASES

GOLDEN_ROLE = os.environ.get("GOLDEN_ROLE", "fast")
print(f"\n[golden/coach] GOLDEN_ROLE={GOLDEN_ROLE}")

pytestmark = pytest.mark.live

# Pacing, same shape and same figure as evaluator's own suite (`fast`, one call
# per fixture, single-turn-question shaped requests) -- see that file's own note.
_PACE_SECONDS = 60


@pytest.fixture(autouse=True)
async def _pace_for_tokens_per_minute():
    yield
    await asyncio.sleep(_PACE_SECONDS)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_golden_case(case, caplog) -> None:
    evaluations = case.evaluations

    with caplog.at_level(logging.INFO, logger="app.llm"):
        result = await generate_coach_report(
            case.case_world,
            case.question,
            case.assessed_level,
            evaluations,
            role=GOLDEN_ROLE,
        )

    retried = any(
        "outcome=empty" in r.getMessage() or "outcome=invalid" in r.getMessage()
        for r in caplog.records
        if r.name == "app.llm"
    )
    print(f"[golden/coach] {case.id}: role={GOLDEN_ROLE} retry_fired={retried}")

    # --- Universal assertions, brief's own list -------------------------------

    # THE most important assertion in this suite: every anchor is a real quote
    # from this session, and every gap names a genuinely unevidenced dimension.
    problems = verify_anchors(result, evaluations)
    assert problems == [], f"{case.id}: verify_anchors found problem(s): {problems}"

    # Redundant with CoachReport's own schema validator (which refuses to
    # construct a report of any other length) -- kept here anyway, same reason
    # the Evaluator suite re-checks `score_out_of_range` despite the schema
    # already enforcing it: this suite also exercises checkers that must keep
    # working against a plain dict once the graph writes `coach_report`.
    assert len(result.improvements) == IMPROVEMENTS_PER_REPORT, (
        f"{case.id}: expected exactly {IMPROVEMENTS_PER_REPORT} improvements, "
        f"got {len(result.improvements)}"
    )

    dashes_found: dict[str, list[str]] = {}
    thin_fields: dict[str, str] = {}
    for idx, improvement in enumerate(result.improvements):
        for field_name in ("stronger_version", "drill"):
            text = getattr(improvement, field_name)
            found = dashes_in_text(text)
            if found:
                dashes_found[f"improvement {idx}.{field_name}"] = found
        thin = blank_or_short_fields(
            {"stronger_version": improvement.stronger_version, "drill": improvement.drill},
            min_len=40,
        )
        for field_name in thin:
            thin_fields[f"improvement {idx}.{field_name}"] = getattr(improvement, field_name)

    assert not dashes_found, (
        f"{case.id}: banned dash character(s) found in candidate-facing copy: {dashes_found}"
    )
    assert not thin_fields, (
        f"{case.id}: field(s) blank or under 40 characters -- {thin_fields}"
    )

    drills = [i.drill for i in result.improvements]
    dupe_drills = duplicate_drills(drills)
    assert not dupe_drills, f"{case.id}: duplicate drill text across improvements: {dupe_drills}"

    # --- Case-specific assertion ----------------------------------------------
    case.check(result, evaluations)
