"""Offline tests for `app/agents/planner.py`'s new pure helpers (story
3.5.3): `_build_question` (Python-side template filling, the structural fix
the whole story is about), `MissingSlotError` (the loud-failure path when the
model omits a required slot), and `_first_dimension` (the value written into
`question_plan[0]["primary_dimension"]` for `ask_question`'s unmodified
`dimension_coverage` read -- see planner.py's module docstring).

No network, no LLM, no marker -- pure functions against hand-built
`SlotFill`/`ProbeAngle` objects, same shape as `app.questions.shapes`'s own
offline coverage.
"""
from __future__ import annotations

import pytest

from app.agents.planner import MissingSlotError, ProbeAngle, SlotFill, _build_question, _first_dimension
from app.questions.shapes import QuestionShape

# Built directly, not via `select_shape` -- decouples these tests from the
# bank's level-index scheme (which shape a given level resolves to is
# `app.questions.shapes`'s own concern, covered by its own tests), so this
# file only exercises `_build_question`'s slot-filling contract.
_ONE_SLOT_SHAPE = QuestionShape(
    category="pricing", template="How would you price {product}?", slots=("product",)
)
_TWO_SLOT_SHAPE = QuestionShape(
    category="gtm",
    template="{company} just built {capability}. How would you take it to market?",
    slots=("company", "capability"),
)


def test_build_question_fills_every_slot_from_the_model_output() -> None:
    question = _build_question(_ONE_SLOT_SHAPE, [SlotFill(name="product", value="Duolingo Max")])
    assert question == "How would you price Duolingo Max?"


def test_build_question_ignores_extra_slots_the_shape_does_not_need() -> None:
    """The model returning more slots than the shape requires must not
    raise -- only a MISSING required slot is an error, per `_build_question`'s
    own docstring ("nothing extra" is a prompt instruction, not something
    this function needs to enforce defensively)."""
    question = _build_question(
        _ONE_SLOT_SHAPE,
        [
            SlotFill(name="product", value="Duolingo Max"),
            SlotFill(name="unused_slot", value="ignored"),
        ],
    )
    assert question == "How would you price Duolingo Max?"


def test_build_question_raises_missing_slot_error_on_an_omitted_required_slot() -> None:
    """The exact failure mode a model returning an incomplete `slots` list
    produces. Must raise loudly (MissingSlotError), never silently format a
    KeyError or drop the slot from the question."""
    with pytest.raises(MissingSlotError):
        _build_question(_ONE_SLOT_SHAPE, [])


def test_build_question_raises_on_a_multi_slot_shape_missing_one_of_several() -> None:
    with pytest.raises(MissingSlotError):
        _build_question(_TWO_SLOT_SHAPE, [SlotFill(name="company", value="Figma")])  # missing "capability"


def test_first_dimension_returns_the_ladders_first_entry() -> None:
    ladder = [
        ProbeAngle(angle="push on margin", primary_dimension="business_model_fluency"),
        ProbeAngle(angle="push on competitors", primary_dimension="market_accuracy"),
    ]
    assert _first_dimension(ladder) == "business_model_fluency"


def test_first_dimension_raises_on_an_empty_ladder_rather_than_faking_a_default() -> None:
    """An empty probe_ladder must not silently resolve to some made-up
    dimension -- `ask_question` (app/graph/build.py:470) uses this value to
    seed `dimension_coverage`, and a fabricated dimension there would corrupt
    that count without any visible error."""
    with pytest.raises(ValueError):
        _first_dimension([])
