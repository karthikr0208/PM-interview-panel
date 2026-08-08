"""Golden-case suite for the Evaluator agent. Run with `make golden
AGENT=evaluator` or `pytest tests/golden/evaluator -v` (NOT under `-m "not
live"` -- see below).

🔴 STORY 4.1's ACCEPTANCE CRITERION IS THAT THIS FILE IS RED, not green.
PHASE-4-SPEC.md 4.1: "Written blind, before the agent, same as 1.3a and
3.1... the suite is deliberately RED at the end of this story. The Evaluator
agent does not exist yet -- it is story 4.2." `evaluate_answer` is imported
LAZILY, inside the session-scoped fixture below, exactly like
`tests/golden/interviewer/test_golden.py`'s identical pattern for
`answer_clarification` at story 3.1: a module-level import would make
`pytest tests -m "not live"` ERROR at COLLECTION time (before deselection
even runs), which would break this project's fastest feedback loop for
every file in the repo, not just this one. The lazy import means collection
always succeeds; only actually RUNNING a `live`-marked test here raises,
loudly, naming exactly what is missing (`app.agents.evaluator` has no
`evaluate_answer` -- it currently exports only the schema, see that
module's docstring).

Marked `pytest.mark.live` for the same reason as every other golden suite:
`pytest tests -m "not live"` DESELECTS this whole file, so it costs ZERO of
the exhausted `fast` daily budget and never even attempts the import that
would fail. Running it directly (`pytest tests/golden/evaluator`, no marker
filter, or via `make golden AGENT=evaluator`) is what demonstrates the red
state -- and it demonstrates it as an `ImportError` naming `evaluate_answer`,
not a `ModuleNotFoundError` naming `app.agents.evaluator`, because the
module DOES exist (this story wrote its schema) -- only the function is
story 4.2's job. See `app/agents/evaluator.py`'s docstring for the same
distinction from the interviewer suite's `story 3.1 / 3.2` split.

🔴 THE CALL SHAPE BELOW IS PROVISIONAL, not a contract. PHASE-4-SPEC.md 4.2
sketches `evaluate_answer(case_world, question, answer, assessed_level,
prior_scores, *, role="fast")` but that signature, the per-answer loop, and
the "running summary, not a window" design (spec § "WHAT THE LIVE INTERVIEW
ALREADY DECIDED" #3) are ALL story 4.2's job to finalize, once it measures
the real token fit at the last answer -- exactly the way
AGENT-INTERVIEWER-SPEC.md's window size was a measurement, not a guess. This
file calls `evaluate_answer` ONCE per fixture, against the fixture's single
question and its LAST candidate answer turn, with `prior_scores=[]` -- a
simplification that keeps this file structurally complete without
pre-deciding 4.2's real per-probe loop. Story 4.2 should expect to rewrite
this call site, not merely un-skip it.
"""
from __future__ import annotations

import asyncio
import logging
import os

import pytest

from tests.golden.evaluator.assertions import (
    dimensions_unaccounted_for,
    duplicate_dimensions,
    not_assessed_carries_a_score,
    quotes_not_found_verbatim,
    score_out_of_range,
)
from tests.golden.evaluator.cases import CASES

GOLDEN_ROLE = os.environ.get("GOLDEN_ROLE", "fast")
print(f"\n[golden/evaluator] GOLDEN_ROLE={GOLDEN_ROLE}")

pytestmark = pytest.mark.live


@pytest.fixture(scope="session")
def evaluate_answer():
    """Imported here, not at module level -- see module docstring. Raises
    `ImportError` today: `app.agents.evaluator` exists (this story's schema)
    but exports no `evaluate_answer` -- that is story 4.2's job."""
    from app.agents.evaluator import evaluate_answer as fn

    return fn


# Pacing, same shape as every other golden suite -- unmeasured here (no
# `Requested` header exists yet, since the agent does not exist), so this is
# a placeholder matching the interviewer suite's own pre-launch estimate
# rather than a re-derivation of a measured figure. Re-measure in story 4.2.
_PACE_SECONDS = 60


@pytest.fixture(autouse=True)
async def _pace_for_tokens_per_minute():
    yield
    await asyncio.sleep(_PACE_SECONDS)


def _last_candidate_answer(transcript_turns: list[dict]) -> str:
    answers = [t for t in transcript_turns if t.get("role") == "candidate" and t.get("kind") == "answer"]
    if not answers:
        raise ValueError("fixture has no candidate answer turn")
    return answers[-1]["content"]


def _main_question(transcript_turns: list[dict]) -> str:
    questions = [t for t in transcript_turns if t.get("role") == "interviewer" and t.get("kind") == "question"]
    if not questions:
        raise ValueError("fixture has no interviewer question turn")
    return questions[0]["content"]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_golden_case(case, evaluate_answer, caplog) -> None:
    case_world = case.case_world
    transcript_turns = case.transcript_turns

    with caplog.at_level(logging.INFO, logger="app.llm"):
        result = await evaluate_answer(
            case_world,
            _main_question(transcript_turns),
            _last_candidate_answer(transcript_turns),
            case.assessed_level,
            [],  # prior_scores -- empty for a first-answer smoke; 4.2's job to thread the real running summary
            role=GOLDEN_ROLE,
        )

    retried = any(
        "outcome=empty" in r.getMessage() or "outcome=invalid" in r.getMessage()
        for r in caplog.records
        if r.name == "app.llm"
    )
    print(f"[golden/evaluator] {case.id}: role={GOLDEN_ROLE} retry_fired={retried}")

    # --- Universal assertions, spec §"Automated tests" table -----------------
    dump = result.model_dump()
    dimension_scores = dump["dimension_scores"]
    not_assessed = dump["not_assessed"]

    missing_quote_dims = quotes_not_found_verbatim(dimension_scores, transcript_turns)
    assert not missing_quote_dims, (
        f"{case.id}: evidence_quote not found verbatim in transcript for "
        f"dimension(s) {missing_quote_dims}"
    )

    both = not_assessed_carries_a_score(dimension_scores, not_assessed)
    assert not both, f"{case.id}: dimension(s) {both} are both scored AND not_assessed"

    unaccounted = dimensions_unaccounted_for(dimension_scores, not_assessed)
    assert not unaccounted, f"{case.id}: dimension(s) {unaccounted} are neither scored nor not_assessed"

    dupes = duplicate_dimensions(dimension_scores)
    assert not dupes, f"{case.id}: dimension(s) {dupes} scored more than once"

    out_of_range = score_out_of_range(dimension_scores)
    assert not out_of_range, f"{case.id}: dimension(s) {out_of_range} scored outside 1-4"

    # --- Case-specific assertion --------------------------------------------
    case.check(result)


# ==============================================================================
# 🔴 LEVEL-ANCHOR CONTROL, live: PHASE-4-SPEC.md 4.1's "the same answer
# scores lower at a higher assessed_level" assertion. Uses the level-pair
# fixtures (`senior_pm_platform_world_level_pair_pm` /
# `..._gpm`) -- identical transcript and world, only `assessed_level`
# differs. `scored_lower_at_higher_level` (assertions.py) does the actual
# comparison; this test only supplies the two real calls it needs.
# ==============================================================================


async def test_level_anchor_control_same_answer_scores_lower_at_gpm_than_pm(
    evaluate_answer, caplog
) -> None:
    from tests.golden.evaluator.assertions import scored_lower_at_higher_level

    pm_case = next(c for c in CASES if c.id == "senior_pm_platform_world_level_pair_pm")
    gpm_case = next(c for c in CASES if c.id == "senior_pm_platform_world_level_pair_gpm")

    with caplog.at_level(logging.INFO, logger="app.llm"):
        pm_result = await evaluate_answer(
            pm_case.case_world,
            _main_question(pm_case.transcript_turns),
            _last_candidate_answer(pm_case.transcript_turns),
            pm_case.assessed_level,
            [],
            role=GOLDEN_ROLE,
        )

    await asyncio.sleep(_PACE_SECONDS)  # two calls in one test; autouse fixture only paces AFTER the test

    with caplog.at_level(logging.INFO, logger="app.llm"):
        gpm_result = await evaluate_answer(
            gpm_case.case_world,
            _main_question(gpm_case.transcript_turns),
            _last_candidate_answer(gpm_case.transcript_turns),
            gpm_case.assessed_level,
            [],
            role=GOLDEN_ROLE,
        )

    pm_scores = {ds.dimension: ds.score for ds in pm_result.dimension_scores}
    gpm_scores = {ds.dimension: ds.score for ds in gpm_result.dimension_scores}

    violations = scored_lower_at_higher_level(pm_scores, gpm_scores)
    assert not violations, (
        f"level-anchor control: dimension(s) {violations} did NOT score lower "
        f"at GPM than PM for the identical answer -- pm_scores={pm_scores} "
        f"gpm_scores={gpm_scores}"
    )
