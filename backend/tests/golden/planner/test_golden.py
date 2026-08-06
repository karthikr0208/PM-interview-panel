"""Golden-case suite for the Interview Planner agent. Run with
`make golden AGENT=planner` or `pytest tests/golden/planner -v`.

Hits the real Groq endpoint (`@pytest.mark.live`) once per case against
`app.agents.planner.plan_interview`. Five fixed `(assessed_level,
case_world)` inputs, per AGENT-PLANNER-SPEC.md §5, checked against the
universal assertions the spec's §5 table specifies, rewritten for story
3.5.3's contract: ONE question plus a probe ladder, not 5-7 free-form
questions. `result.questions` is always length 1 now -- coverage moved from
"every question x its own primary_dimension" to "every rubric dimension
appears somewhere across the probe ladder" (spec §3's rewrite, owed to
AGENT-PLANNER-SPEC.md by Karthik, not this file).

Story 3.5.2's three shape gates (`decorative_statistic`,
`is_recitation_shaped`, `matches_no_shape`) are this story's acceptance
test per PHASE-3.5-SPEC.md 3.5.3: the composed question must clear all
three, because it is Python-templated (`shape.template.format(**slots)`),
never model-written. If any of the three ever fires here, that is a real
finding -- do not relax the assertion to make it pass.

CRITICAL -- collection must stay clean: this suite must collect under
`pytest tests -m "not live"` even though `app.agents.planner` is a real,
importable module now (unlike when this file was first written, story 2.5).
The import stays lazy inside the session-scoped `plan_interview` fixture
regardless, so a future rename/break in that module surfaces loudly only
when a `live` test actually runs, not during collection -- matching
resume_analyst's, case_architect's, and this file's own prior precedent.

Role: `GOLDEN_ROLE` env var, "fast" default -- story 3.5.3 REVERSES the
pre-3.5.3 "deep" default (DEV-STATE § Decisions 2026-08-04's `QuestionPlan`
no longer exists; this call's output is a fraction of that size). "deep"
opt-in so the orchestrator can re-run this identical set against the other
model without touching this file.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os

import pytest

from tests.golden.planner.assertions import (
    RUBRIC_DIMENSIONS,
    blank_or_short_fields,
    contains_banned_register_name,
    contains_fake_round_number,
    decorative_statistic,
    empty_grounded_in,
    is_generic_question,
    is_recitation_shaped,
    matches_no_shape,
    missing_dimension_coverage,
    missing_grounding,
    no_dash_variants,
)
from tests.golden.planner.cases import CASES

GOLDEN_ROLE = os.environ.get("GOLDEN_ROLE", "fast")
print(f"\n[golden/planner] GOLDEN_ROLE={GOLDEN_ROLE}")

pytestmark = pytest.mark.live


@pytest.fixture(scope="session")
def plan_interview():
    """Imported here, not at module level -- see module docstring."""
    from app.agents.planner import plan_interview as fn

    return fn


# ==============================================================================
# NAMED TRAP arithmetic (brief, story 3.5.3 Part 4): re-measure, do not
# assume. The Planner's input is still the whole `case_world` (unchanged by
# this story), but the OUTPUT schema shrank from `QuestionPlan` (5-7 objects
# of 7 fields, `deep`-only per DEV-STATE § Decisions 2026-08-04) to one
# shape's slots (2-4 short strings) + a 5-8-entry probe ladder of short
# strings + one grounded_in list + one intent sentence -- a fraction of the
# old generation, which is exactly why `fast` is tried first below rather
# than assumed to fail the way it did on the old schema.
#
# `app/agents/planner.py` calls `get_llm(role, max_tokens=2048)`, lower than
# the product default 4096, freeing more of the 8,000 TPM ceiling for the
# ~900-1,200-token case_world input than the old `QuestionPlan` path could
# afford.
_PACE_SECONDS = 90


@pytest.fixture(autouse=True)
async def _pace_for_tokens_per_minute():
    yield
    await asyncio.sleep(_PACE_SECONDS)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_golden_case(case, plan_interview, caplog) -> None:
    with caplog.at_level(logging.INFO, logger="app.llm"):
        result = await plan_interview(case.assessed_level, case.case_world, role=GOLDEN_ROLE)

    # Same retry-observation shape as the other golden suites: reads the log
    # this call already produced, no extra LLM call, and covers both
    # outcomes `_LoggedStructured` logs on a retry.
    retried = any(
        "outcome=empty" in r.getMessage() or "outcome=invalid" in r.getMessage()
        for r in caplog.records
        if r.name == "app.llm"
    )
    print(f"[golden/planner] {case.id}: role={GOLDEN_ROLE} retry_fired={retried}")

    # --- Immutability: case_world must be byte-identical after the call ---
    assert json.dumps(case.case_world, sort_keys=True) == json.dumps(
        case._payload["case_world"], sort_keys=True
    ), f"{case.id}: case_world was mutated by plan_interview"

    assert len(result.questions) == 1, (
        f"{case.id}: story 3.5.3 plans exactly ONE question, got {len(result.questions)}"
    )
    q = result.questions[0]

    # --- Vacuity floor FIRST: everything below can pass trivially against
    # an empty field, so silence has to be caught before it can hide behind
    # them. Doubly emphasized for grounded_in, per spec §5/§7. ---
    ungrounded = empty_grounded_in([q.model_dump()])
    assert not ungrounded, (
        f"{case.id}: the question has an empty grounded_in list -- the "
        f"membership check below would pass it vacuously"
    )
    empty = blank_or_short_fields({"question": q.question}, min_len=15)
    assert not empty, f"{case.id}: vacuity floor -- question text empty or near-empty"

    # --- Grounding: every grounded_in entry must appear in case_world ---
    missing = missing_grounding(q.grounded_in, case.case_world)
    assert not missing, (
        f"{case.id}: grounded_in entry not found in case_world (fabricated): {missing}"
    )

    # --- Story 3.5.2's three shape gates -- THIS story's acceptance test.
    # The question is Python-templated, never model-written, so all three
    # must clear by construction. A failure here is a real finding. ---
    stat = decorative_statistic(q.question)
    assert stat is None, (
        f"{case.id}: composed question carries a decorative statistic "
        f"({stat!r}) -- the template should have made this structurally "
        f"impossible: {q.question!r}"
    )
    assert not is_recitation_shaped(q.question), (
        f"{case.id}: composed question is recitation-shaped: {q.question!r}"
    )
    assert not matches_no_shape(q.question), (
        f"{case.id}: composed question conforms to no bank shape (should "
        f"conform to its own, by construction): {q.question!r}"
    )

    # --- Rubric coverage moved to the probe ladder (spec §3's rewrite) ---
    assert 5 <= len(q.probe_ladder) <= 8, (
        f"{case.id}: probe_ladder has {len(q.probe_ladder)} entries, want 5-8"
    )
    missing_dims = missing_dimension_coverage([p.model_dump() for p in q.probe_ladder])
    assert not missing_dims, (
        f"{case.id}: rubric dimension(s) never covered across the probe "
        f"ladder: {missing_dims} (want all of {sorted(RUBRIC_DIMENSIONS)})"
    )

    # --- Candidate-facing copy hygiene: no em-dashes, no fake-round
    # numbers, no banned-register names -- the main question and every
    # probe angle ---
    for text in [q.question] + [p.angle for p in q.probe_ladder]:
        assert no_dash_variants(text), f"{case.id}: em-dash or en-dash: {text!r}"
        fake_round = contains_fake_round_number(text)
        assert fake_round is None, f"{case.id}: fake-round number ({fake_round!r}): {text!r}"
        banned_name = contains_banned_register_name(text)
        assert banned_name is None, f"{case.id}: banned-register name ({banned_name!r}): {text!r}"

    # --- Genericness: the question must name something specific to THIS
    # world (spec §5's "single most valuable test in this suite") ---
    assert not is_generic_question(q.question, case.case_world), (
        f"{case.id}: question is generic -- would fit any case world: {q.question!r}"
    )

    # --- Case-specific assertion, spec §5's table ---
    case.check(result, case.case_world)
