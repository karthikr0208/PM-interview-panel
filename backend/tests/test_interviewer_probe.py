"""Offline tests for `app/agents/interviewer.py`'s story 3.5.4 additions:
`Probe` (the schema), `_windowed_transcript` (the token-budget fix),
`resolve_primary_dimension` (the Python-side dimension resolution --
`_first_dimension` in `planner.py`'s shape, applied a second time), and
`generate_probe`'s `ValueError` guards.

No network, no LLM, no marker -- pure functions against hand-built dicts,
same shape as `test_planner_slot_fill.py`'s coverage of `_build_question`
and `_first_dimension`. `generate_probe`'s guards raise before any call to
`get_llm`, so they are exercised here with `asyncio.run` and no mocking.

The token-budget test is PHASE-3.5-SPEC.md's acceptance box "the TPM
computation at probe 10, done and recorded" -- it reuses the largest real
curated world (`app/cases/openai.json`, ~1,392 tokens) rather than a
synthetic fixture, because the measured numbers in `interviewer.py`'s
`_TRANSCRIPT_TAIL_TURNS` comment were measured against the real worlds, not
a stand-in.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
import tiktoken

from app.agents.interviewer import (
    Probe,
    _build_probe_messages,
    _covered_probe_count,
    _windowed_transcript,
    generate_probe,
    resolve_primary_dimension,
)

_OPENAI_WORLD = json.loads(
    (Path(__file__).resolve().parent.parent / "app" / "cases" / "openai.json").read_text(
        encoding="utf-8"
    )
)

_MAIN_QUESTION = "What is OpenAI's biggest threat over the next three years?"

_LADDER: list[dict] = [
    {
        "angle": "push on what happens to compute cost if free-tier growth keeps outpacing paid conversion",
        "primary_dimension": "business_model_fluency",
    },
    {
        "angle": "push on how OpenAI defends consumer share if a rival ships a comparable assistant into every phone",
        "primary_dimension": "market_accuracy",
    },
    {
        "angle": "push on what the candidate would actually do in the next two quarters, not just diagnose",
        "primary_dimension": "decision_quality",
    },
    {
        "angle": "ask the candidate to lay out the tradeoff structurally before picking a side",
        "primary_dimension": "structural_clarity",
    },
    {
        "angle": "push on why the candidate would make that call over the alternative",
        "primary_dimension": "point_of_view",
    },
]


# ==============================================================================
# Probe's schema -- both fields required, both plain strings.
# ==============================================================================


def test_probe_schema_accepts_both_fields() -> None:
    probe = Probe(probe="You said margin matters more than reach. What changes if margin doesn't?", angle_used="")
    assert probe.probe.endswith("?")
    assert probe.angle_used == ""


def test_probe_schema_rejects_a_missing_field() -> None:
    with pytest.raises(Exception):  # pydantic.ValidationError, not re-imported for a one-line check
        Probe(probe="Only one field given.")


# ==============================================================================
# _windowed_transcript -- first candidate answer + last 4 turns, no
# duplication when the interview is short enough that they overlap.
# ==============================================================================


def test_windowed_transcript_returns_everything_when_short() -> None:
    turns = [
        {"role": "interviewer", "text": "main question"},
        {"role": "candidate", "text": "first answer"},
    ]
    window = _windowed_transcript(turns)
    assert window == turns


def test_windowed_transcript_keeps_first_answer_plus_last_four_when_long() -> None:
    # main question, then 6 candidate/interviewer pairs -- 13 turns total,
    # far more than the 5-turn window (1 first-answer + 4 tail).
    turns = [{"role": "interviewer", "text": "main question"}]
    for i in range(6):
        turns.append({"role": "candidate", "text": f"answer {i}"})
        turns.append({"role": "interviewer", "text": f"probe {i}"})
    window = _windowed_transcript(turns)

    assert window[0] == {"role": "candidate", "text": "answer 0"}, "first candidate answer must be kept"
    assert window[1:] == turns[-4:], "everything after the first answer must be exactly the last 4 turns"
    assert len(window) == 5


def test_windowed_transcript_does_not_duplicate_first_answer_already_in_the_tail() -> None:
    """A 4-turn interview: the first answer already sits inside the last-4
    window, so the window must not repeat it."""
    turns = [
        {"role": "interviewer", "text": "main question"},
        {"role": "candidate", "text": "first answer"},
        {"role": "interviewer", "text": "probe 1"},
        {"role": "candidate", "text": "second answer"},
    ]
    window = _windowed_transcript(turns)
    assert window == turns[-4:]
    assert window.count({"role": "candidate", "text": "first answer"}) == 1


def test_windowed_transcript_handles_an_empty_transcript() -> None:
    assert _windowed_transcript([]) == []


def test_windowed_transcript_handles_no_candidate_turns_yet() -> None:
    """Defensive: a transcript with only interviewer turns (should not
    happen in practice -- a probe is only generated after an answer -- but
    must not raise)."""
    turns = [{"role": "interviewer", "text": "main question"}]
    assert _windowed_transcript(turns) == turns


# ==============================================================================
# resolve_primary_dimension -- Python decides, the model only fills
# angle_used. Same philosophy as planner.py's _first_dimension.
# ==============================================================================


def test_resolve_primary_dimension_matches_a_ladder_angle_exactly() -> None:
    dimension = resolve_primary_dimension(
        "push on what the candidate would actually do in the next two quarters, not just diagnose",
        _LADDER,
        transcript_turns=[],
    )
    assert dimension == "decision_quality"


@pytest.mark.parametrize(
    "angle_used",
    [
        "push on what the candidate would actually do in the next two quarters, not just diagnose.",
        "Push on what the candidate would actually do in the next two quarters, not just diagnose",
        "push on what the candidate would actually do in the next two  quarters, not just diagnose",
        "  push on what the candidate would actually do in the next two quarters, not just diagnose  ",
    ],
    ids=["trailing period", "capitalised", "doubled space", "surrounding whitespace"],
)
def test_resolve_primary_dimension_matches_an_angle_the_model_retyped(angle_used: str) -> None:
    """🔴 OBSERVED LIVE, 2026-08-06, not hypothesised. The prompt tells the
    model to copy the ladder angle "EXACTLY, character for character"; across
    four live probes it obeyed once and dropped the trailing period the other
    three times. Each of those three fell through to the positional fallback
    and resolved to the SAME dimension, which collapses the ladder's rubric
    coverage -- the thing Phase 4's Evaluator reads.

    The trailing-period case is the one actually seen. The other three are
    the same class of near-miss and cost nothing to pin."""
    assert (
        resolve_primary_dimension(angle_used, _LADDER, transcript_turns=[]) == "decision_quality"
    )


def test_resolve_primary_dimension_still_rejects_a_genuinely_different_angle() -> None:
    """The vacuity floor on normalisation: forgiving punctuation must not
    become forgiving semantics. A different ladder entry's text must never
    resolve to this entry's dimension -- if it did, normalisation would be
    attributing probes to the wrong rubric dimension, which is worse than
    the positional fallback it replaced."""
    assert (
        resolve_primary_dimension(
            "push on why the candidate would make that call over the alternative.",
            _LADDER,
            transcript_turns=[],
        )
        == "point_of_view"
    )


def test_resolve_primary_dimension_falls_back_to_first_uncovered_when_angle_used_is_empty() -> None:
    """angle_used == "" (the model followed the candidate's own thread
    instead of a ladder entry): falls back to the first ladder dimension
    not yet covered, inferred from how many probes have already been asked.
    Two probes already asked (3 interviewer turns: main question + 2
    probes) -> the THIRD ladder entry (index 2, 0-based) is next."""
    transcript = [
        {"role": "interviewer", "text": "main question"},
        {"role": "candidate", "text": "answer 1"},
        {"role": "interviewer", "text": "probe 1"},
        {"role": "candidate", "text": "answer 2"},
        {"role": "interviewer", "text": "probe 2"},
        {"role": "candidate", "text": "answer 3"},
    ]
    dimension = resolve_primary_dimension("", _LADDER, transcript)
    assert dimension == _LADDER[2]["primary_dimension"] == "decision_quality"


def test_resolve_primary_dimension_falls_back_when_angle_used_matches_nothing() -> None:
    """A non-empty angle_used that matches no ladder entry (a paraphrase,
    not a verbatim copy) takes the SAME fallback path as an empty string --
    the brief's "if angle_used matches nothing" clause."""
    dimension = resolve_primary_dimension(
        "some paraphrase the model invented instead of copying the ladder text",
        _LADDER,
        transcript_turns=[{"role": "interviewer", "text": "main question"}],
    )
    assert dimension == _LADDER[0]["primary_dimension"]  # 0 probes issued yet -> first entry


def test_resolve_primary_dimension_falls_back_to_first_entry_once_ladder_is_exhausted() -> None:
    """More probes have been asked than the ladder has entries (a long
    interview, 8-10 probes against a 5-entry ladder): falls back to the
    first entry's dimension rather than raising an IndexError."""
    transcript = [{"role": "interviewer", "text": "main question"}]
    for i in range(10):  # 10 probes issued, ladder only has 5 entries
        transcript.append({"role": "candidate", "text": f"answer {i}"})
        transcript.append({"role": "interviewer", "text": f"probe {i}"})
    dimension = resolve_primary_dimension("", _LADDER, transcript)
    assert dimension == _LADDER[0]["primary_dimension"]


def test_covered_probe_count_ignores_the_opening_question() -> None:
    """Pins the off-by-one this whole resolution depends on: the opening
    question is an interviewer turn but consumes no ladder entry."""
    assert _covered_probe_count([{"role": "interviewer", "text": "main question"}]) == 0
    assert (
        _covered_probe_count(
            [
                {"role": "interviewer", "text": "main question"},
                {"role": "candidate", "text": "answer"},
                {"role": "interviewer", "text": "probe 1"},
            ]
        )
        == 1
    )


# ==============================================================================
# generate_probe's ValueError guards -- raised before any LLM call, so these
# run with no network and no mocking.
# ==============================================================================


def test_generate_probe_raises_on_empty_case_world() -> None:
    with pytest.raises(ValueError):
        asyncio.run(generate_probe({}, [], _MAIN_QUESTION, _LADDER, []))


def test_generate_probe_raises_on_empty_main_question() -> None:
    with pytest.raises(ValueError):
        asyncio.run(generate_probe(_OPENAI_WORLD, [], "   ", _LADDER, []))


def test_generate_probe_raises_on_empty_probe_ladder() -> None:
    with pytest.raises(ValueError):
        asyncio.run(generate_probe(_OPENAI_WORLD, [], _MAIN_QUESTION, [], []))


# ==============================================================================
# 🔴 THE TOKEN BUDGET, done and recorded -- PHASE-3.5-SPEC.md's acceptance
# box. Builds a 10-probe transcript of 500-word (verbose) candidate answers,
# the worst case the budget comment in interviewer.py measures against, and
# asserts the assembled probe messages stay under the 8,000 TPM ceiling.
# ==============================================================================


_ANSWER_SENTENCE = (
    "I would prioritize the enterprise and API surface over the free consumer tier because the margin "
    "profile there funds the compute commitments that already exist, and because the sales cycle length "
    "in regulated accounts means the healthcare bet needs to start now even though it will not show "
    "results for at least two quarters, and I would track weekly active users alongside gross margin so "
    "the tradeoff stays visible rather than assumed"
)


def _build_ten_probe_transcript(words_per_answer: int) -> list[dict]:
    """Simulates the transcript AT probe 10 -- the longest it ever gets in a
    45-minute interview capped at 6-10 probes. 10 candidate answers of
    `words_per_answer` words each, interleaved with 9 prior interviewer
    probes. High-entropy prose, not a two-word repeat: a repeated word pair
    compresses far below a real answer's tokens-per-word under BPE, which
    would understate the token count this test exists to measure."""
    words = (_ANSWER_SENTENCE + " ").split(" ") * (words_per_answer // len(_ANSWER_SENTENCE.split(" ")) + 1)
    answer_text = " ".join(words[:words_per_answer])
    turns = [{"role": "interviewer", "text": _MAIN_QUESTION}]
    for i in range(10):
        turns.append({"role": "candidate", "text": f"Turn {i}: {answer_text}"})
        if i < 9:
            turns.append(
                {"role": "interviewer", "text": f"Can you say more about that specific tradeoff, point {i}?"}
            )
    return turns


def test_probe_messages_stay_under_8000_tokens_at_probe_ten_with_verbose_answers() -> None:
    """The acceptance box, verbatim: builds a 10-probe transcript of 500-word
    (verbose) answers against the LARGEST real curated world, and asserts
    the assembled human message stays under 8,000 tokens."""
    enc = tiktoken.get_encoding("o200k_base")
    transcript = _build_ten_probe_transcript(words_per_answer=500)

    messages = _build_probe_messages(_OPENAI_WORLD, [], _MAIN_QUESTION, _LADDER, transcript)
    total_tokens = sum(len(enc.encode(text)) for _, text in messages)

    assert total_tokens < 8000, (
        f"assembled probe messages at probe 10 with verbose answers are "
        f"{total_tokens} tokens, at or over the 8,000 TPM ceiling"
    )


def test_probe_messages_also_fit_with_typical_250_word_answers() -> None:
    """The less extreme case from the same measurement table -- kept as a
    second data point, not a redundant assertion: it pins that the window
    fits comfortably rather than by a hair at the boundary the verbose test
    already checks."""
    enc = tiktoken.get_encoding("o200k_base")
    transcript = _build_ten_probe_transcript(words_per_answer=250)

    messages = _build_probe_messages(_OPENAI_WORLD, [], _MAIN_QUESTION, _LADDER, transcript)
    total_tokens = sum(len(enc.encode(text)) for _, text in messages)

    assert total_tokens < 8000
