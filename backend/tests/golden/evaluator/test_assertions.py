"""Offline tests for the Evaluator golden suite: the checkers in
`assertions.py`, and the schema-level guarantees on `AnswerEvaluation` /
`DimensionScore` in `app/agents/evaluator.py`. No network, no `live` marker,
no import of an `evaluate_answer` that does not exist yet (story 4.2) --
collects and runs under `pytest tests -m "not live"` today.

PHASE-4-SPEC.md 4.1's item 4, THE central falsification this file exists
for: "Falsify the verbatim-quote assertion against a hand-written evaluation
containing a quote that is nearly right (a word changed). If a paraphrase
passes, the assertion is decorative." See
`test_quotes_not_found_verbatim_rejects_a_one_word_paraphrase` below --
its docstring carries the observed failure output, pasted verbatim after
running it once by hand as required by the brief.

Precedent (CLAUDE.md / DEV-STATE, story 0.6, 1.3a, 1.5, 2.2, 2.5): a denial
assertion is not trusted until it has been shown to FAIL against input it
should reject. Every checker below gets both directions.
"""
from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.agents.evaluator import AnswerEvaluation, DimensionScore
from tests.golden.evaluator.assertions import (
    blank_or_short_fields,
    dimensions_unaccounted_for,
    duplicate_dimensions,
    not_assessed_carries_a_score,
    quotes_not_found_verbatim,
    score_out_of_range,
    scored_lower_at_higher_level,
    transcript_haystack,
)
from tests.golden.evaluator.cases import CASES, FIXTURES_DIR, _PLANNER_FIXTURES_DIR

RUBRIC_DIMENSIONS = {
    "business_model_fluency",
    "market_accuracy",
    "decision_quality",
    "structural_clarity",
    "point_of_view",
}

# A real sentence from fixture 1 (the real corpus, session
# ac569e9b-db6a-4a17-9a73-b5c1ed43e59f, turn idx 19), used below for both the
# verbatim-accept test and the falsification test. Copied character for
# character from the fixture file, not retyped from memory -- retyping is
# exactly how a "near miss" test could accidentally test nothing.
_REAL_TRANSCRIPT_TURNS = [
    {
        "idx": 19,
        "role": "candidate",
        "kind": "answer",
        "content": (
            "Experiences carry a take rate rather than full booking value, so the right\n"
            "comparison is contribution margin per confirmed stay, not gross bookings.\n"
            "Airbnb runs an 82.6% gross margin overall and Services should be dilutive to\n"
            "that at first, because supply acquisition and trust operations are heavier\n"
            "per unit.\n"
        ),
    }
]


# ==============================================================================
# Sanity: the case table itself.
# ==============================================================================


def test_seven_cases_defined() -> None:
    """Pins the count -- a fixture silently dropped from `CASES` (but left on
    disk) would otherwise pass every other check here. Widened from 6-8 to
    6-9 on 2026-08-10 (commit 565a92c's follow-up coverage): the
    `followup_defends_decision` / `followup_abandons_decision` pair brought
    the original seven fixtures to nine."""
    assert 6 <= len(CASES) <= 9, [c.id for c in CASES]


def test_every_fixture_file_exists_and_has_a_transcript_and_level() -> None:
    for case in CASES:
        assert (FIXTURES_DIR / f"{case.fixture}.json").exists(), case.id
        assert case.assessed_level.strip(), case.id
        assert case.transcript_turns, f"{case.id}: empty transcript_turns"


def test_every_case_world_pointer_resolves_or_is_the_documented_exception() -> None:
    """Every fixture either points at a real planner fixture (the reuse
    rule) or is the one documented exception (the real corpus, which embeds
    its own case_world because it has nothing else to point at)."""
    exceptions = {"karthik_live_airbnb_senior_pm"}
    for case in CASES:
        if case.id in exceptions:
            assert case.world_fixture is None, f"{case.id}: expected the documented exception"
            assert case.case_world, f"{case.id}: exception fixture has no embedded case_world"
        else:
            assert case.world_fixture is not None, f"{case.id}: expected a world_fixture pointer"
            world_path = _PLANNER_FIXTURES_DIR / f"{case.world_fixture}.json"
            assert world_path.exists(), f"{case.id}: points at missing planner fixture {world_path}"


def test_fixtures_that_reuse_a_world_do_not_embed_a_copy_of_it() -> None:
    """Rule 3 of the brief, mechanically checked, same shape as
    interviewer/test_assertions.py's identical test: a fixture that points
    at a planner world via `world_fixture` must never ALSO carry a
    `case_world` key -- that would be exactly the silent-copy drift the
    pointer rule exists to prevent."""
    for case in CASES:
        payload = json.loads((FIXTURES_DIR / f"{case.fixture}.json").read_text(encoding="utf-8"))
        if payload.get("world_fixture") is not None:
            assert "case_world" not in payload, f"{case.id}: embeds a case_world despite having a world_fixture pointer"


def test_the_real_corpus_fixture_is_labelled_as_real_not_hand_written() -> None:
    """PHASE-4-SPEC.md 4.1's own instruction: if the DB is unreachable,
    fixture 1 must be hand-written and CLEARLY labelled as such, never
    presented as the real transcript. The DB WAS reachable this session (see
    session report), so this pins the positive case: the fixture says so
    itself, in its own `source` field, rather than this test's docstring
    being the only place that fact lives."""
    payload = json.loads((FIXTURES_DIR / "karthik_live_airbnb_senior_pm.json").read_text(encoding="utf-8"))
    assert "REAL" in payload["source"]
    assert "ac569e9b-db6a-4a17-9a73-b5c1ed43e59f" in payload["source"]


# ==============================================================================
# transcript_haystack / quotes_not_found_verbatim -- THIS suite's teeth.
# ==============================================================================


def test_transcript_haystack_flattens_candidate_content() -> None:
    haystack = transcript_haystack(_REAL_TRANSCRIPT_TURNS)
    assert "82.6% gross margin" in haystack
    assert "contribution margin per confirmed stay" in haystack


def test_quotes_not_found_verbatim_accepts_an_exact_quote() -> None:
    exact = "Airbnb runs an 82.6% gross margin overall and Services should be dilutive to\nthat at first"
    dimension_scores = [
        {"dimension": "business_model_fluency", "score": 3, "evidence_quote": exact, "reasoning": "x"}
    ]
    assert quotes_not_found_verbatim(dimension_scores, _REAL_TRANSCRIPT_TURNS) == []


def test_quotes_not_found_verbatim_rejects_a_one_word_paraphrase() -> None:
    """🔴 THE FALSIFICATION, PHASE-4-SPEC.md 4.1's item 4. The real sentence
    is "Airbnb runs an 82.6% gross margin overall..."; this quote changes
    ONE word ("runs" -> "operates") and otherwise matches character for
    character. If this assertion is real, the check must reject it.

    OBSERVED, 2026-08-08 -- run standalone with the assertion INVERTED to
    `== []` (asserting the paraphrase is NOT caught), to prove this test
    would fail if the checker were decorative:

        $ .venv/Scripts/python.exe -c "..."
        Traceback (most recent call last):
          File "<string>", line 25, in <module>
        AssertionError: INVERTED assertion, expecting this to fail to prove the checker has teeth
        quotes_not_found_verbatim result: ['business_model_fluency']

    -- the inverted version raised, which is the observed proof the check
    has teeth: `quotes_not_found_verbatim` returned
    `['business_model_fluency']`, NOT `[]`, for a quote one word off from the
    real transcript sentence ("runs" -> "operates"). With the assertion
    restored to its real (non-inverted) form below, that same result is
    exactly what this test expects and it passes. Same control shape as
    `interviewer/assertions.py`'s `ungrounded_figures` docstring records for
    its own first (too-loose) version -- the failure mode this suite exists
    to catch.
    """
    near_miss = "Airbnb operates an 82.6% gross margin overall and Services should be dilutive to\nthat at first"
    dimension_scores = [
        {"dimension": "business_model_fluency", "score": 3, "evidence_quote": near_miss, "reasoning": "x"}
    ]
    result = quotes_not_found_verbatim(dimension_scores, _REAL_TRANSCRIPT_TURNS)
    assert result == ["business_model_fluency"], (
        f"expected the paraphrased quote to be REJECTED (dimension flagged), got {result!r} -- "
        f"if this is [], the verbatim check is decorative"
    )


def test_quotes_not_found_verbatim_rejects_a_quote_from_a_different_fixture_entirely() -> None:
    """Positive control, cross-fixture: a quote that is real, but from a
    DIFFERENT transcript, must still fail against THIS one -- the check is
    per-transcript, not "is this a real sentence somewhere in the product."""
    foreign_quote = "Circuitway's ARR is $6.1M and gross margin is 71.8%"
    dimension_scores = [
        {"dimension": "business_model_fluency", "score": 3, "evidence_quote": foreign_quote, "reasoning": "x"}
    ]
    assert quotes_not_found_verbatim(dimension_scores, _REAL_TRANSCRIPT_TURNS) == ["business_model_fluency"]


def test_quotes_not_found_verbatim_returns_empty_on_an_empty_dimension_scores_list() -> None:
    """Vacuity note, not a trap: an empty `dimension_scores` list has
    nothing to fail to find, same shape as `missing_grounding([], world)` in
    the interviewer/planner suites. This is fine here specifically because
    `AnswerEvaluation`'s own schema validator (tested below) already forbids
    an evaluation that scores nothing AND lists nothing in not_assessed --
    the vacuity floor lives at the schema level for this suite, not as a
    separate mechanical check duplicating it."""
    assert quotes_not_found_verbatim([], _REAL_TRANSCRIPT_TURNS) == []


def test_blank_or_short_fields_rejects_an_empty_reasoning() -> None:
    fields = {"reasoning": ""}
    assert blank_or_short_fields(fields, min_len=15) == ["reasoning"]


def test_blank_or_short_fields_accepts_substantive_reasoning() -> None:
    fields = {
        "reasoning": (
            "The candidate cited Airbnb's real 82.6% gross margin to argue Services "
            "should be dilutive at first -- correct mechanics, grounded in the case."
        )
    }
    assert blank_or_short_fields(fields, min_len=15) == []


# ==============================================================================
# not_assessed coherence -- the mechanical (dict-level) twins of the pydantic
# validator tested further below.
# ==============================================================================


def test_not_assessed_carries_a_score_accepts_disjoint_sets() -> None:
    dimension_scores = [{"dimension": "decision_quality", "score": 3, "evidence_quote": "x", "reasoning": "y"}]
    not_assessed = ["market_accuracy", "point_of_view"]
    assert not_assessed_carries_a_score(dimension_scores, not_assessed) == []


def test_not_assessed_carries_a_score_rejects_the_positive_control() -> None:
    """Brief's exact positive control: a dimension in not_assessed that
    also carries a score."""
    dimension_scores = [{"dimension": "market_accuracy", "score": 2, "evidence_quote": "x", "reasoning": "y"}]
    not_assessed = ["market_accuracy"]
    assert not_assessed_carries_a_score(dimension_scores, not_assessed) == ["market_accuracy"]


def test_dimensions_unaccounted_for_accepts_full_coverage() -> None:
    dimension_scores = [
        {"dimension": d, "score": 2, "evidence_quote": "x", "reasoning": "y"} for d in RUBRIC_DIMENSIONS
    ]
    assert dimensions_unaccounted_for(dimension_scores, []) == set()


def test_dimensions_unaccounted_for_rejects_a_silently_dropped_dimension() -> None:
    """Positive control: point_of_view is neither scored nor not_assessed --
    the silent-drop failure the module docstring names."""
    scored_dims = RUBRIC_DIMENSIONS - {"point_of_view"}
    dimension_scores = [{"dimension": d, "score": 2, "evidence_quote": "x", "reasoning": "y"} for d in scored_dims]
    assert dimensions_unaccounted_for(dimension_scores, []) == {"point_of_view"}


def test_duplicate_dimensions_accepts_five_unique_dimensions() -> None:
    dimension_scores = [
        {"dimension": d, "score": 2, "evidence_quote": "x", "reasoning": "y"} for d in RUBRIC_DIMENSIONS
    ]
    assert duplicate_dimensions(dimension_scores) == []


def test_duplicate_dimensions_rejects_the_positive_control() -> None:
    dimension_scores = [
        {"dimension": "decision_quality", "score": 2, "evidence_quote": "x", "reasoning": "y"},
        {"dimension": "decision_quality", "score": 3, "evidence_quote": "z", "reasoning": "w"},
    ]
    assert duplicate_dimensions(dimension_scores) == ["decision_quality"]


def test_score_out_of_range_accepts_one_through_four() -> None:
    dimension_scores = [
        {"dimension": "decision_quality", "score": s, "evidence_quote": "x", "reasoning": "y"} for s in (1, 2, 3, 4)
    ]
    assert score_out_of_range(dimension_scores) == []


def test_score_out_of_range_rejects_the_positive_control() -> None:
    """Brief control: a score of 0 and a score of 5 -- neither is a valid
    rubric position (PRD §7: 1 to 4)."""
    dimension_scores = [
        {"dimension": "decision_quality", "score": 0, "evidence_quote": "x", "reasoning": "y"},
        {"dimension": "market_accuracy", "score": 5, "evidence_quote": "x", "reasoning": "y"},
    ]
    assert score_out_of_range(dimension_scores) == ["decision_quality", "market_accuracy"]


# ==============================================================================
# scored_lower_at_higher_level -- PRD §7's anchor-shift rule.
# ==============================================================================


def test_scored_lower_at_higher_level_accepts_a_genuine_decrease() -> None:
    assert scored_lower_at_higher_level({"decision_quality": 3}, {"decision_quality": 2}) == []


def test_scored_lower_at_higher_level_rejects_the_positive_control() -> None:
    """Brief control: the SAME score at both levels is a violation -- "the
    same answer scores lower," not "no worse." """
    assert scored_lower_at_higher_level({"decision_quality": 3}, {"decision_quality": 3}) == ["decision_quality"]


def test_scored_lower_at_higher_level_rejects_a_higher_score_at_the_higher_level() -> None:
    assert scored_lower_at_higher_level({"decision_quality": 2}, {"decision_quality": 3}) == ["decision_quality"]


def test_scored_lower_at_higher_level_ignores_dimensions_not_shared_by_both() -> None:
    """A dimension not_assessed at one level and scored at the other has
    nothing to compare -- that mismatch belongs to the not_assessed checks
    above, not this one."""
    lower = {"decision_quality": 3}
    higher = {"decision_quality": 2, "market_accuracy": 4}
    assert scored_lower_at_higher_level(lower, higher) == []


# ==============================================================================
# Schema-level guarantees, `app/agents/evaluator.py`. PRD §8: "every score
# carries a verbatim quote ... enforced at the schema level, not by
# convention." Each test below constructs a BAD `AnswerEvaluation` /
# `DimensionScore` and observes pydantic itself refuse it -- the strongest
# form of falsification available: not "the test caught it," but "the value
# could not be built in the first place."
# ==============================================================================

_FULL_VALID_SCORES = [
    DimensionScore(dimension=d, score=3, evidence_quote="x", reasoning="y")
    for d in ("business_model_fluency", "decision_quality", "structural_clarity")
]
_FULL_NOT_ASSESSED = ["market_accuracy", "point_of_view"]


def test_answer_evaluation_accepts_a_coherent_construction() -> None:
    """Positive control for every negative test below: this exact shape
    (three scored, two not_assessed, no overlap, all five accounted for)
    must construct cleanly, or the negative tests are not proving anything
    the positive case could not already fail."""
    evaluation = AnswerEvaluation(
        dimension_scores=_FULL_VALID_SCORES,
        framework_narration=False,
        not_assessed=_FULL_NOT_ASSESSED,
    )
    assert len(evaluation.dimension_scores) == 3
    assert evaluation.not_assessed == _FULL_NOT_ASSESSED


def test_dimension_score_rejects_an_empty_evidence_quote() -> None:
    """PRD §8, enforced in the schema, not by convention."""
    with pytest.raises(ValidationError):
        DimensionScore(dimension="decision_quality", score=3, evidence_quote="", reasoning="y")


def test_dimension_score_rejects_a_score_of_zero() -> None:
    with pytest.raises(ValidationError):
        DimensionScore(dimension="decision_quality", score=0, evidence_quote="x", reasoning="y")


def test_dimension_score_rejects_a_score_of_five() -> None:
    with pytest.raises(ValidationError):
        DimensionScore(dimension="decision_quality", score=5, evidence_quote="x", reasoning="y")


def test_dimension_score_rejects_an_unrecognised_dimension_name() -> None:
    with pytest.raises(ValidationError):
        DimensionScore(dimension="storytelling", score=3, evidence_quote="x", reasoning="y")


def test_answer_evaluation_rejects_a_dimension_both_scored_and_not_assessed() -> None:
    """The brief's central not_assessed rule, enforced in the schema: a
    dimension cannot be both scored and not_assessed at the same time."""
    with pytest.raises(ValidationError):
        AnswerEvaluation(
            dimension_scores=_FULL_VALID_SCORES,
            framework_narration=False,
            not_assessed=["market_accuracy", "business_model_fluency"],  # overlaps a scored dimension
        )


def test_answer_evaluation_rejects_a_silently_dropped_dimension() -> None:
    """Four scored, one listed not_assessed -- point_of_view is neither.
    Must be rejected, not silently accepted with four-fifths coverage."""
    with pytest.raises(ValidationError):
        AnswerEvaluation(
            dimension_scores=_FULL_VALID_SCORES,
            framework_narration=False,
            not_assessed=["market_accuracy"],  # point_of_view accounted for nowhere
        )


def test_answer_evaluation_rejects_a_duplicate_dimension_score() -> None:
    with pytest.raises(ValidationError):
        AnswerEvaluation(
            dimension_scores=[
                DimensionScore(dimension="decision_quality", score=3, evidence_quote="x", reasoning="y"),
                DimensionScore(dimension="decision_quality", score=2, evidence_quote="a", reasoning="b"),
                DimensionScore(dimension="business_model_fluency", score=3, evidence_quote="x", reasoning="y"),
                DimensionScore(dimension="structural_clarity", score=3, evidence_quote="x", reasoning="y"),
            ],
            framework_narration=False,
            not_assessed=["market_accuracy", "point_of_view"],
        )


def test_answer_evaluation_rejects_an_unrecognised_not_assessed_value() -> None:
    with pytest.raises(ValidationError):
        AnswerEvaluation(
            dimension_scores=_FULL_VALID_SCORES,
            framework_narration=False,
            not_assessed=["market_accuracy", "storytelling"],
        )


def test_answer_evaluation_accepts_all_five_scored_and_nothing_not_assessed() -> None:
    """The other extreme from the positive control above: full coverage,
    empty not_assessed -- must construct cleanly, matching
    `apm_consumer_world_full_coverage`'s expected shape."""
    all_five = [
        DimensionScore(dimension=d, score=2, evidence_quote="x", reasoning="y") for d in RUBRIC_DIMENSIONS
    ]
    evaluation = AnswerEvaluation(dimension_scores=all_five, framework_narration=False, not_assessed=[])
    assert evaluation.not_assessed == []
    assert len(evaluation.dimension_scores) == 5


def test_answer_evaluation_accepts_all_five_not_assessed_and_nothing_scored() -> None:
    """The other extreme: an interview so far off-topic nothing was
    evidenced at all. Must still construct -- an empty `dimension_scores`
    is coherent PROVIDED every dimension is accounted for in not_assessed,
    which is exactly what this constructs."""
    evaluation = AnswerEvaluation(
        dimension_scores=[], framework_narration=False, not_assessed=sorted(RUBRIC_DIMENSIONS)
    )
    assert evaluation.dimension_scores == []
    assert set(evaluation.not_assessed) == RUBRIC_DIMENSIONS
