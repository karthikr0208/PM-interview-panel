"""Golden-case suite for the Interview Planner agent. Run with
`make golden AGENT=planner` or `pytest tests/golden/planner -v`.

Hits the real Groq endpoint (`@pytest.mark.live`) once per case against
`app.agents.planner.plan_interview`. Five fixed `(assessed_level,
case_world)` inputs, per AGENT-PLANNER-SPEC.md §5, checked against the
universal assertions §5 specifies (apply to every case, no exceptions) plus
the case table in `cases.py`.

CRITICAL -- collection must stay clean: `app.agents.planner` does not exist
yet as this suite is written (story 2.5; the agent is story 2.6's job). A
module-level `from app.agents.planner import ...` would make `pytest tests
-m "not live"` ERROR during collection -- deselection happens after
collection, so it would not save this file, it would break the project's
fastest feedback loop for every file. The import is therefore lazy, inside
the session-scoped `plan_interview` fixture below: collection succeeds
unconditionally, and only actually running a `live` test raises (loudly, as
`ModuleNotFoundError`, naming exactly the missing module).

Deliberately NOT `pytest.importorskip`: once `app.agents.planner` exists but
is misnamed or mis-exported, `importorskip` would silently skip forever, and
a silently-skipped golden suite is worse than no suite -- nobody would
notice the gate stopped gating. See resume_analyst's and case_architect's
identical choice.

Role: `GOLDEN_ROLE` env var, "deep" default (ARCHITECTURE §4 / spec §6),
"fast" opt-in so the orchestrator can re-run this identical set against the
other model without touching this file.
"""
from __future__ import annotations

import asyncio
import logging
import os

import pytest

from tests.golden.planner.assertions import (
    RUBRIC_DIMENSIONS,
    blank_or_short_fields,
    contains_banned_register_name,
    contains_fake_round_number,
    count_out_of_range,
    empty_grounded_in,
    is_generic_question,
    missing_dimension_coverage,
    missing_grounding,
    no_dash_variants,
    probe_angle_violations,
    total_minutes_mismatch,
)
from tests.golden.planner.cases import CASES

GOLDEN_ROLE = os.environ.get("GOLDEN_ROLE", "deep")
print(f"\n[golden/planner] GOLDEN_ROLE={GOLDEN_ROLE}")

pytestmark = pytest.mark.live


@pytest.fixture(scope="session")
def plan_interview():
    """Imported here, not at module level -- see module docstring."""
    from app.agents.planner import plan_interview as fn

    return fn


# ==============================================================================
# NAMED TRAP 4 arithmetic (brief, story 2.5): the Planner's input is the
# whole `case_world`, the largest input any agent in the product takes.
# Groq reports `Requested = prompt + input + max_tokens` against an 8,000
# TPM ceiling; `app/llm.py` sets `max_tokens=4096` (confirmed, line ~264).
#
# Measured directly from THIS package's own fixtures (not guessed), the
# same discipline case_architect's test_golden.py used for its own
# candidate_profile estimate:
#
#   compact-JSON char count of each fixture's `case_world`, measured
#   2026-08-02:
#     apm_consumer_world.json        3,472 chars (~827 tokens)
#     pm_b2b_world.json              3,518 chars (~838 tokens)
#     senior_pm_platform_world.json  3,937 chars (~937 tokens)  <- largest
#     gpm_portfolio_world.json       3,866 chars (~920 tokens)
#     sparse_world.json              2,488 chars (~592 tokens)
#
# At ~4.2 chars/token (the project's measured ratio, inherited from
# resume_analyst and case_architect -- no planner-specific measurement
# exists yet since the prompt does not exist), the LARGEST world is ~937
# input tokens. This is well under spec §6's own worst-case estimate of a
# "1,200-token case world" -- the schema's actual worst case is smaller
# than the spec assumed, which matters for the ceiling below.
#
# The eventual human message will also carry framing text around the
# serialized world (e.g. "Assessed level: ...\n\nCase world:\n..."), so a
# rounded 1,000-token input budget is used below rather than the bare 937,
# matching case_architect's padding discipline (it padded 124 measured
# tokens to 200 for framing overhead -- a smaller absolute pad here since
# the base number is already much larger and proportionally less framing
# text is needed).
#
# Budget: prompt_tokens + input_tokens(1000) + max_tokens(4096) < 8000
#      => prompt_tokens < 8000 - 4096 - 1000 = 2,904
#      => max prompt size at 4.2 chars/token ~= 2,904 * 4.2 ~= 12,197 chars.
#
# NOT a blocker: 2,904 prompt tokens / ~12,200 chars is comparable to
# resume_analyst's actual shipped prompt (~12,200 chars) and workable for a
# schema this size. It IS tighter than case_architect's own budget (~3,704
# prompt tokens / ~15,557 chars, per that suite's test_golden.py) by about
# 22% -- expected and not a red flag, since case_world (this agent's input)
# is roughly 5x candidate_profile (Case Architect's input) in token terms.
# Story 2.6 should treat ~12,000 chars as the hard prompt ceiling, not a
# target, and re-measure once a real prompt exists, the same way
# resume_analyst's projected pacing was replaced by a measured one.
#
# Pacing: refill rate is 8000/60 = 133.3 tokens/sec. A call at the computed
# ceiling requests close to prompt_tokens(2904) + input_tokens(1000) +
# max_tokens(4096) = 8000 -- against the bucket by construction. This
# pre-launch estimate has no observed `Requested` header to round from (the
# prompt does not exist yet), so it carries the same larger margin
# case_architect's identical pre-launch projection used: 90s, not the 60s
# resume_analyst settled on only after measuring a real header.
_PACE_SECONDS = 90


@pytest.fixture(autouse=True)
async def _pace_for_tokens_per_minute():
    yield
    await asyncio.sleep(_PACE_SECONDS)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_golden_case(case, plan_interview, caplog) -> None:
    with caplog.at_level(logging.INFO, logger="app.llm"):
        result = await plan_interview(case.assessed_level, case.case_world, role=GOLDEN_ROLE)

    # Same retry-observation shape as resume_analyst's and case_architect's
    # golden suites: reads the log this call already produced, no extra LLM
    # call, and covers both outcomes `_LoggedStructured` logs on a retry.
    retried = any(
        "outcome=empty" in r.getMessage() or "outcome=invalid" in r.getMessage()
        for r in caplog.records
        if r.name == "app.llm"
    )
    print(f"[golden/planner] {case.id}: role={GOLDEN_ROLE} retry_fired={retried}")

    # --- Immutability: story 2.6's first real test of the ARCHITECTURE §2
    # rule by a downstream agent (spec §1). `case_world` must be
    # byte-identical after the call; a mutation here would corrupt the
    # artifact every later agent (Interviewer, Evaluator, Coach) depends on.
    import json

    assert json.dumps(case.case_world, sort_keys=True) == json.dumps(
        case._payload["case_world"], sort_keys=True
    ), f"{case.id}: case_world was mutated by plan_interview"

    questions = result.questions

    # --- Universal assertions, spec §5's table, apply to every case ---

    # Vacuity floor FIRST, same ordering logic as resume_analyst and
    # case_architect: every assertion below can pass trivially against an
    # empty field, so silence has to be caught before it can hide behind
    # them. Doubly emphasized for `grounded_in` per spec §5/§7 -- the
    # suite's single most important assertion (grounding) is vacuous on an
    # empty list, so that floor is asserted separately, before grounding.
    ungrounded = empty_grounded_in([q.model_dump() for q in questions])
    assert not ungrounded, (
        f"{case.id}: question(s) {ungrounded} have an empty grounded_in list -- "
        f"the membership check below would pass them vacuously"
    )

    string_fields = {f"question[{q.idx}].question": q.question for q in questions}
    empty = blank_or_short_fields(string_fields, min_len=15)
    assert not empty, f"{case.id}: vacuity floor -- question text empty or near-empty: {empty}"

    # --- Grounding: every grounded_in entry must appear in case_world ---
    for q in questions:
        missing = missing_grounding(q.grounded_in, case.case_world)
        assert not missing, (
            f"{case.id}: question {q.idx} grounded_in entry not found in "
            f"case_world (fabricated): {missing}"
        )

    # --- Rubric coverage against PRD §7's five dimensions ---
    missing_dims = missing_dimension_coverage([q.model_dump() for q in questions])
    assert not missing_dims, (
        f"{case.id}: rubric dimension(s) never covered as primary_dimension: "
        f"{missing_dims} (want all of {sorted(RUBRIC_DIMENSIONS)})"
    )

    # --- Question count: 5-7 ---
    assert not count_out_of_range(questions, 5, 7), (
        f"{case.id}: {len(questions)} questions, want 5-7"
    )

    # --- probe_angles: 2-3 per question ---
    probe_violations = probe_angle_violations([q.model_dump() for q in questions])
    assert not probe_violations, (
        f"{case.id}: question(s) {probe_violations} have probe_angles outside 2-3"
    )

    # --- Time budget: <=45 minutes, matches sum of per-question minutes ---
    assert not total_minutes_mismatch(
        result.total_minutes, [q.model_dump() for q in questions]
    ), (
        f"{case.id}: total_minutes={result.total_minutes} inconsistent with "
        f"sum of per-question minutes, or exceeds 45"
    )

    # --- Candidate-facing copy hygiene: no em-dashes, no fake-round numbers,
    # no banned-register names ---
    for q in questions:
        assert no_dash_variants(q.question), (
            f"{case.id}: question {q.idx} contains an em-dash or en-dash: {q.question!r}"
        )
        fake_round = contains_fake_round_number(q.question)
        assert fake_round is None, (
            f"{case.id}: question {q.idx} cites a fake-round number ({fake_round!r}): "
            f"{q.question!r}"
        )
        banned_name = contains_banned_register_name(q.question)
        assert banned_name is None, (
            f"{case.id}: question {q.idx} cites a banned-register name ({banned_name!r}): "
            f"{q.question!r}"
        )

    # --- Genericness: every question must name something specific to THIS
    # world (spec §5's "single most valuable test in this suite") ---
    generic = [q.idx for q in questions if is_generic_question(q.question, case.case_world)]
    assert not generic, (
        f"{case.id}: question(s) {generic} are generic -- would fit any case world"
    )

    # --- Case-specific assertion, spec §5's table ---
    case.check(result, case.case_world)
