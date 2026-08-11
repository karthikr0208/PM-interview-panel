"""Offline tests for the Coach golden suite: the checkers in `assertions.py`, the
case-specific checks in `cases.py`, and the schema-level / pure-function
guarantees `app/agents/coach.py` already provides (`verify_anchors`,
`unevidenced_dimensions`). No network, no `live` marker -- collects and runs
under `pytest tests -m "not live"`.

Precedent (CLAUDE.md / DEV-STATE, and `tests/golden/evaluator/test_assertions.py`
above it): a denial assertion is not trusted until it has been shown to FAIL
against input it should reject. Every checker below gets both directions --
🔴 the four required by the brief (near-paraphrase anchor, em-dash in `drill`, a
`gap` naming an already-scored dimension, and a fully valid report) plus the
suite's own helper functions.

Note on construction vs assertion time, as the brief anticipates: `CoachReport`'s
own `model_validator`s already block a `gap` improvement from being duplicated
with another `gap`'s dimension, and block two `moment` improvements from sharing
an `anchor_quote` -- see `test_coach_report_blocks_duplicate_anchors_and_gap_dimensions_at_construction_time`
below. Those two failure modes are therefore proven at CONSTRUCTION time
(`pytest.raises(ValidationError)`), not at `verify_anchors`/assertion time, and
that is exactly what the brief says to expect and note when it happens.
"""
from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from app.agents.coach import CoachReport, Improvement, unevidenced_dimensions, verify_anchors
from tests.golden.coach.assertions import blank_or_short_fields, dashes_in_text, duplicate_drills
from tests.golden.coach.cases import CASES, FIXTURES_DIR, _CASES_DIR, GoldenCase
from tests.golden.coach.cases import _check_full_coverage, _check_thin_coverage

# A self-contained evaluations payload, independent of the live fixtures, so
# these tests do not depend on `full_coverage.json` / `thin_coverage.json`
# staying byte-identical over time. Shape matches `app/graph/state.py`'s
# `answer_evaluations: list[dict]`.
_QUOTE_MARGIN = (
    "Airbnb runs an 82.6% gross margin on $11.1B in ARR, so the marginal cost of "
    "trying the pilot is genuinely low relative to the size of the core business."
)
_QUOTE_DECISION = (
    "I'd sequence it: keep Services in two or three pilot markets while the core "
    "team fixes the trust and safety issues, and revisit the bigger bet in a year."
)

_EVALUATIONS = [
    {
        "turn_idx": 1,
        "dimension_scores": [
            {
                "dimension": "business_model_fluency",
                "score": 3,
                "evidence_quote": _QUOTE_MARGIN,
                "reasoning": "Correct use of the real margin and ARR figures.",
            },
            {
                "dimension": "decision_quality",
                "score": 2,
                "evidence_quote": _QUOTE_DECISION,
                "reasoning": "Names a real option and a timeline, no exit criteria.",
            },
        ],
        "not_assessed": ["market_accuracy", "structural_clarity", "point_of_view"],
    }
]

# unevidenced_dimensions(_EVALUATIONS) -- market_accuracy, structural_clarity,
# point_of_view never carry a score above. Computed via the real function, not
# hardcoded, so a change to RUBRIC_DIMENSIONS can't silently desync this file.
_UNEVIDENCED = set(unevidenced_dimensions(_EVALUATIONS))

_LONG_STRONGER_1 = (
    "I would keep Services in exactly two pilot markets for two quarters and set an "
    "explicit exit bar up front: host and provider supply growth has to outpace "
    "demand before I scale it any further."
)
_LONG_STRONGER_2 = (
    "I would say plainly that lodging still funds the company, so any Services spend "
    "this year has to be small enough that killing it in six months costs nothing."
)
_LONG_STRONGER_3 = (
    "I would name market_accuracy directly: New York already banned most listings "
    "under Local Law 18, and I would size the core-defense budget against that, not "
    "against a hypothetical worst case."
)
_LONG_DRILL_1 = "Write the one number that would make you kill the Services pilot, before your next mock interview."
_LONG_DRILL_2 = "Practice stating your position on a tradeoff in one sentence before you list any evidence for it."
_LONG_DRILL_3 = "Pick one rubric dimension you skipped last time and rehearse a two-sentence answer addressing it."


def _good_report() -> CoachReport:
    """Two 'moment' improvements anchored on real quotes from `_EVALUATIONS`,
    one 'gap' naming a genuinely unevidenced dimension. Fully valid: this is the
    positive control every rejection test below is measured against."""
    return CoachReport(
        improvements=[
            Improvement(
                kind="moment",
                anchor_quote=_QUOTE_MARGIN,
                stronger_version=_LONG_STRONGER_1,
                drill=_LONG_DRILL_1,
            ),
            Improvement(
                kind="moment",
                anchor_quote=_QUOTE_DECISION,
                stronger_version=_LONG_STRONGER_2,
                drill=_LONG_DRILL_2,
            ),
            Improvement(
                kind="gap",
                dimension="market_accuracy",
                stronger_version=_LONG_STRONGER_3,
                drill=_LONG_DRILL_3,
            ),
        ]
    )


# ==============================================================================
# Sanity: the case table itself.
# ==============================================================================


def test_exactly_two_cases_defined() -> None:
    """Pins the count -- a matched pair, per the brief: full_coverage and
    thin_coverage, no more, no fewer."""
    assert len(CASES) == 2, [c.id for c in CASES]
    assert {c.id for c in CASES} == {"full_coverage", "thin_coverage"}


def test_every_fixture_file_exists_and_points_at_a_real_curated_world() -> None:
    for case in CASES:
        assert (FIXTURES_DIR / f"{case.fixture}.json").exists(), case.id
        assert case.assessed_level.strip(), case.id
        assert case.question.strip(), case.id
        assert case.evaluations, f"{case.id}: empty evaluations"
        world_path = _CASES_DIR / f"{case.world_source}.json"
        assert world_path.exists(), (
            f"{case.id}: world_source {case.world_source!r} does not resolve to a "
            f"real curated world under {world_path}"
        )


def test_full_coverage_fixture_really_evidences_all_five_dimensions() -> None:
    """Pins the fixture's own claim: `unevidenced_dimensions` must return []
    for `full_coverage.json`'s evaluations, or the case does not test what its
    name says it tests."""
    case = next(c for c in CASES if c.id == "full_coverage")
    assert unevidenced_dimensions(case.evaluations) == [], (
        "full_coverage.json: expected every dimension evidenced, but "
        f"unevidenced_dimensions() returned {unevidenced_dimensions(case.evaluations)!r}"
    )


def test_thin_coverage_fixture_really_leaves_three_dimensions_unevidenced() -> None:
    """Pins the fixture's own claim: exactly market_accuracy, structural_clarity,
    and point_of_view are unevidenced in `thin_coverage.json`."""
    case = next(c for c in CASES if c.id == "thin_coverage")
    assert set(unevidenced_dimensions(case.evaluations)) == {
        "market_accuracy",
        "structural_clarity",
        "point_of_view",
    }, (
        f"thin_coverage.json: expected exactly those three unevidenced, got "
        f"{unevidenced_dimensions(case.evaluations)!r}"
    )


def test_fixtures_do_not_embed_a_copy_of_the_world() -> None:
    """Rule from the module docstring, mechanically checked: a fixture points
    at a real curated world via `world_source` and never ALSO carries a
    `case_world` key -- that would be the silent-copy drift the pointer rule
    exists to prevent."""
    for case in CASES:
        payload = json.loads((FIXTURES_DIR / f"{case.fixture}.json").read_text(encoding="utf-8"))
        assert "world_source" in payload, f"{case.id}: missing world_source pointer"
        assert "case_world" not in payload, f"{case.id}: embeds a case_world despite having a world_source pointer"


# ==============================================================================
# verify_anchors -- 🔴 THIS suite's teeth, per the brief. Reuses
# `app.agents.coach.verify_anchors` directly rather than reimplementing it.
# ==============================================================================


def test_verify_anchors_accepts_a_fully_grounded_report() -> None:
    """Positive control every rejection test below is measured against."""
    assert verify_anchors(_good_report(), _EVALUATIONS) == []


def test_verify_anchors_rejects_a_near_paraphrase_anchor() -> None:
    """🔴 REQUIRED by the brief. The real quote is "...I'd sequence it: keep
    Services in two or three pilot markets..."; this anchor changes ONE word
    ("sequence" -> "stagger") and otherwise matches character for character. If
    this is caught, `verify_anchors` is checking exact membership, not fuzzy
    similarity -- the same class of falsification
    `evaluator/test_assertions.py`'s `quotes_not_found_verbatim` test performs
    for its own suite.
    """
    near_miss = _QUOTE_DECISION.replace("sequence", "stagger", 1)
    assert near_miss != _QUOTE_DECISION  # the substitution actually happened

    bad_report = CoachReport(
        improvements=[
            Improvement(
                kind="moment",
                anchor_quote=_QUOTE_MARGIN,
                stronger_version=_LONG_STRONGER_1,
                drill=_LONG_DRILL_1,
            ),
            Improvement(
                kind="moment",
                anchor_quote=near_miss,
                stronger_version=_LONG_STRONGER_2,
                drill=_LONG_DRILL_2,
            ),
            Improvement(
                kind="gap",
                dimension="market_accuracy",
                stronger_version=_LONG_STRONGER_3,
                drill=_LONG_DRILL_3,
            ),
        ]
    )
    problems = verify_anchors(bad_report, _EVALUATIONS)
    assert problems, "expected the one-word-changed anchor to be REJECTED, got no problems at all"
    assert any("improvement 1" in p for p in problems), (
        f"expected a problem naming improvement 1 (the paraphrased anchor), got {problems!r}"
    )


def test_verify_anchors_rejects_a_gap_naming_an_already_scored_dimension() -> None:
    """🔴 REQUIRED by the brief. `business_model_fluency` IS scored in
    `_EVALUATIONS` (score 3, via `_QUOTE_MARGIN`), so a 'gap' improvement
    naming it is false: the topic plainly came up. `Improvement`'s own
    validator only checks that the name is a real rubric dimension, not that
    it is genuinely unevidenced for THIS session -- that check lives in
    `verify_anchors`, which is exactly what this proves.
    """
    bad_report = CoachReport(
        improvements=[
            Improvement(
                kind="moment",
                anchor_quote=_QUOTE_MARGIN,
                stronger_version=_LONG_STRONGER_1,
                drill=_LONG_DRILL_1,
            ),
            Improvement(
                kind="moment",
                anchor_quote=_QUOTE_DECISION,
                stronger_version=_LONG_STRONGER_2,
                drill=_LONG_DRILL_2,
            ),
            Improvement(
                kind="gap",
                dimension="business_model_fluency",  # scored above -- false gap
                stronger_version=_LONG_STRONGER_3,
                drill=_LONG_DRILL_3,
            ),
        ]
    )
    problems = verify_anchors(bad_report, _EVALUATIONS)
    assert problems, "expected the false gap (business_model_fluency, which IS scored) to be REJECTED"
    assert any("business_model_fluency" in p for p in problems), (
        f"expected a problem naming business_model_fluency, got {problems!r}"
    )


def test_coach_report_blocks_duplicate_anchors_and_gap_dimensions_at_construction_time() -> None:
    """Contradiction to note, per the brief's own instruction: two of the
    failure modes an assertion-layer test might expect to catch are actually
    blocked EARLIER, at `CoachReport` construction, by its own
    `model_validator` (see `app/agents/coach.py`'s
    `_report_is_three_distinct_improvements`). Constructing either shape below
    raises `ValidationError` before `verify_anchors` is ever called -- proven
    here rather than assumed, so this suite is honest about where the floor
    actually sits.
    """
    with pytest.raises(ValidationError):
        CoachReport(
            improvements=[
                Improvement(
                    kind="moment",
                    anchor_quote=_QUOTE_MARGIN,
                    stronger_version=_LONG_STRONGER_1,
                    drill=_LONG_DRILL_1,
                ),
                Improvement(
                    kind="moment",
                    anchor_quote=_QUOTE_MARGIN,  # same anchor as above
                    stronger_version=_LONG_STRONGER_2,
                    drill=_LONG_DRILL_2,
                ),
                Improvement(
                    kind="gap",
                    dimension="market_accuracy",
                    stronger_version=_LONG_STRONGER_3,
                    drill=_LONG_DRILL_3,
                ),
            ]
        )

    with pytest.raises(ValidationError):
        CoachReport(
            improvements=[
                Improvement(
                    kind="gap",
                    dimension="market_accuracy",
                    stronger_version=_LONG_STRONGER_1,
                    drill=_LONG_DRILL_1,
                ),
                Improvement(
                    kind="gap",
                    dimension="market_accuracy",  # same dimension as above
                    stronger_version=_LONG_STRONGER_2,
                    drill=_LONG_DRILL_2,
                ),
                Improvement(
                    kind="moment",
                    anchor_quote=_QUOTE_MARGIN,
                    stronger_version=_LONG_STRONGER_3,
                    drill=_LONG_DRILL_3,
                ),
            ]
        )


def test_coach_report_rejects_a_report_of_the_wrong_length_at_construction_time() -> None:
    """The "exactly 3 improvements" shared assertion, also blocked at
    construction time rather than at `test_golden.py`'s assertion layer."""
    with pytest.raises(ValidationError):
        CoachReport(
            improvements=[
                Improvement(
                    kind="moment",
                    anchor_quote=_QUOTE_MARGIN,
                    stronger_version=_LONG_STRONGER_1,
                    drill=_LONG_DRILL_1,
                ),
                Improvement(
                    kind="moment",
                    anchor_quote=_QUOTE_DECISION,
                    stronger_version=_LONG_STRONGER_2,
                    drill=_LONG_DRILL_2,
                ),
            ]
        )


# ==============================================================================
# dashes_in_text -- candidate-facing copy rule (CLAUDE.md, and the Coach's own
# system prompt: "No em dashes anywhere in your output.").
# ==============================================================================


def test_dashes_in_text_accepts_clean_prose_including_a_real_hyphen() -> None:
    clean = "I would drop the SMB tier entirely for two quarters, a thirty-minute rehearsal is enough."
    assert dashes_in_text(clean) == []


def test_dashes_in_text_rejects_an_em_dash() -> None:
    assert dashes_in_text("Do this drill—it takes ten minutes.") == ["em dash"]


def test_dashes_in_text_rejects_an_en_dash() -> None:
    assert dashes_in_text("Practice the 5–10 minute framing drill.") == ["en dash"]


def test_dashes_in_text_rejects_a_non_breaking_hyphen() -> None:
    assert dashes_in_text("A follow‑up drill for tomorrow.") == ["non-breaking hyphen"]


def test_a_report_with_an_em_dash_in_drill_is_rejected_by_the_dash_check() -> None:
    """🔴 REQUIRED by the brief. `Improvement` itself has no opinion on dash
    characters (only `min_length=1`), so this constructs cleanly -- the check
    that must catch it is `dashes_in_text`, applied the same way
    `test_golden.py` applies it to every improvement's `drill` and
    `stronger_version`.
    """
    report_with_em_dash = CoachReport(
        improvements=[
            Improvement(
                kind="moment",
                anchor_quote=_QUOTE_MARGIN,
                stronger_version=_LONG_STRONGER_1,
                drill="Write down the number that would kill the pilot—then say it out loud.",
            ),
            Improvement(
                kind="moment",
                anchor_quote=_QUOTE_DECISION,
                stronger_version=_LONG_STRONGER_2,
                drill=_LONG_DRILL_2,
            ),
            Improvement(
                kind="gap",
                dimension="market_accuracy",
                stronger_version=_LONG_STRONGER_3,
                drill=_LONG_DRILL_3,
            ),
        ]
    )
    found = dashes_in_text(report_with_em_dash.improvements[0].drill)
    assert found == ["em dash"], (
        f"expected the em dash in improvement 0's drill to be REJECTED, got {found!r} -- "
        f"if this is [], the dash check is decorative"
    )
    # the other two improvements are clean -- proves the check is per-field, not
    # a report-wide false positive
    assert dashes_in_text(report_with_em_dash.improvements[1].drill) == []
    assert dashes_in_text(report_with_em_dash.improvements[2].drill) == []


# ==============================================================================
# blank_or_short_fields
# ==============================================================================


def test_blank_or_short_fields_accepts_substantive_fields() -> None:
    fields = {"stronger_version": _LONG_STRONGER_1, "drill": _LONG_DRILL_1}
    assert blank_or_short_fields(fields, min_len=40) == []


def test_blank_or_short_fields_rejects_an_empty_drill() -> None:
    fields = {"stronger_version": _LONG_STRONGER_1, "drill": ""}
    assert blank_or_short_fields(fields, min_len=40) == ["drill"]


def test_blank_or_short_fields_rejects_a_whitespace_only_drill() -> None:
    fields = {"stronger_version": _LONG_STRONGER_1, "drill": "   \n  "}
    assert blank_or_short_fields(fields, min_len=40) == ["drill"]


def test_blank_or_short_fields_rejects_a_one_word_drill() -> None:
    """🔴 The brief's own example of a failure this must catch: "A one-word
    drill is a failure." """
    fields = {"stronger_version": _LONG_STRONGER_1, "drill": "Practice."}
    assert blank_or_short_fields(fields, min_len=40) == ["drill"]


# ==============================================================================
# duplicate_drills
# ==============================================================================


def test_duplicate_drills_accepts_three_distinct_drills() -> None:
    assert duplicate_drills([_LONG_DRILL_1, _LONG_DRILL_2, _LONG_DRILL_3]) == []


def test_duplicate_drills_rejects_the_positive_control() -> None:
    assert duplicate_drills([_LONG_DRILL_1, _LONG_DRILL_1, _LONG_DRILL_3]) == [_LONG_DRILL_1]


# ==============================================================================
# Case-specific checks from cases.py -- proven to reject a bad shape, not just
# to accept the real live output blindly.
# ==============================================================================


# A third real quote, distinct from `_QUOTE_MARGIN` / `_QUOTE_DECISION`, so an
# all-'moment' report can anchor three DIFFERENT quotes rather than reusing one
# (CoachReport's own validator forbids reusing an anchor across improvements).
_QUOTE_THIRD = (
    "New York's Local Law 18 already removed most active listings there, so I would "
    "size any core-defense spend against that fact, not a hypothetical worst case."
)
_EVALUATIONS_WITH_THIRD_QUOTE = [
    {
        **_EVALUATIONS[0],
        "dimension_scores": _EVALUATIONS[0]["dimension_scores"]
        + [
            {
                "dimension": "market_accuracy",
                "score": 3,
                "evidence_quote": _QUOTE_THIRD,
                "reasoning": "Correctly cites Local Law 18 from the case world.",
            }
        ],
    }
]


def _all_moment_report() -> CoachReport:
    """Three 'moment' improvements, all anchored on real quotes -- the shape
    `full_coverage` requires and `thin_coverage` must reject (thin_coverage's
    own dimensions leave market_accuracy unevidenced, so anchoring a 'moment'
    to `_QUOTE_THIRD` only makes sense against
    `_EVALUATIONS_WITH_THIRD_QUOTE`, where market_accuracy IS scored)."""
    return CoachReport(
        improvements=[
            Improvement(
                kind="moment",
                anchor_quote=_QUOTE_MARGIN,
                stronger_version=_LONG_STRONGER_1,
                drill=_LONG_DRILL_1,
            ),
            Improvement(
                kind="moment",
                anchor_quote=_QUOTE_DECISION,
                stronger_version=_LONG_STRONGER_2,
                drill=_LONG_DRILL_2,
            ),
            Improvement(
                kind="moment",
                anchor_quote=_QUOTE_THIRD,
                stronger_version=_LONG_STRONGER_3,
                drill=_LONG_DRILL_3,
            ),
        ]
    )


def test_check_full_coverage_accepts_an_all_moment_report() -> None:
    _check_full_coverage(_all_moment_report(), _EVALUATIONS_WITH_THIRD_QUOTE)


def test_check_full_coverage_rejects_a_report_containing_a_gap() -> None:
    """`_good_report()` carries one 'gap' (on market_accuracy, which is
    legitimately unevidenced in `_EVALUATIONS`) -- the WRONG shape for
    `full_coverage`'s own rule ("no dimension is unevidenced, so every
    improvement must be a 'moment'"). This proves `_check_full_coverage`
    rejects the very report `_check_thin_coverage` accepts below, confirming
    the two checks are not vacuously identical.
    """
    with pytest.raises(AssertionError):
        _check_full_coverage(_good_report(), _EVALUATIONS)


def test_check_thin_coverage_accepts_a_report_with_a_gap_in_the_unevidenced_set() -> None:
    _check_thin_coverage(_good_report(), _EVALUATIONS)


def test_check_thin_coverage_rejects_an_all_moment_report() -> None:
    """The mirror control: a report with zero 'gap' improvements fails
    `_check_thin_coverage`'s "at least one gap" requirement, even though every
    field is otherwise perfectly valid and fully grounded."""
    with pytest.raises(AssertionError):
        _check_thin_coverage(_all_moment_report(), _EVALUATIONS)
