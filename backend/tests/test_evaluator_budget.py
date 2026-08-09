"""Offline token-budget test for `app/agents/evaluator.py`'s
`_build_evaluation_messages` -- the arithmetic recorded in that module's
budget comment block, made executable so a later prompt or template change
that breaks it fails here instead of at 429-time against a live candidate.

No network, no LLM, no marker: it assembles messages and counts them with
`tiktoken`, exactly like `test_interviewer_probe.py`'s probe-10 budget test,
whose shape this follows. It runs inside `pytest tests -m "not live"` and
costs nothing.

`Requested = system + human + max_tokens` (see `app/llm.py`'s `get_llm` note
-- `max_tokens` is part of the REQUEST size on Groq, not merely a cap on the
reply), against the 8,000 tokens-per-minute ceiling.

Two things are measured, not one:
  1. every real golden fixture, each with a WORST-CASE `prior_scores` (all
     five dimensions, long quotes) that no fixture actually sends today, and
  2. a stress case -- the largest real curated world (`app/cases/openai.json`,
     ~1,392 tokens) plus a 500-word verbose answer plus the same full
     `prior_scores`.

PHASE-4-SPEC.md § "WHAT THE LIVE INTERVIEW ALREADY DECIDED" #2 measured the
FULL transcript at 10,274 tokens, over the ceiling, which is what forces
per-answer scoring in the first place. This file is the other half of that
measurement: proof that per-answer actually fits.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import tiktoken

from app.agents.evaluator import _build_evaluation_messages
from app.agents.planner import RUBRIC_DIMENSIONS
from tests.golden.evaluator.cases import CASES

_TPM_CEILING = 8000
_MAX_TOKENS = 2048  # `evaluate_answer`'s value -- part of the request, see module docstring

_OPENAI_WORLD = json.loads(
    (Path(__file__).resolve().parent.parent / "app" / "cases" / "openai.json").read_text(
        encoding="utf-8"
    )
)


def _tokens(text: str) -> int:
    return len(tiktoken.get_encoding("o200k_base").encode(text))


# 220 characters of high-entropy prose. Long, because a real `evidence_quote`
# is a whole sentence the model copied out of the answer, and a short
# stand-in would understate the one input that grows with the interview.
_LONG_QUOTE = (
    "I would prioritize the enterprise surface over the free consumer tier because the margin profile "
    "there funds the compute commitments that already exist, and the sales cycle in regulated accounts "
    "means the bet has to start now."
)

assert len(_LONG_QUOTE) >= 220, "the worst-case quote stopped being worst-case"

# WORST CASE, and deliberately worse than anything sent today: all five
# dimensions carrying a score, a long quote and a reason. In the real loop
# `prior_scores` is often shorter than this and is NEVER larger, because it is
# a running summary bounded at five dimensions rather than a transcript.
_FULL_PRIOR_SCORES: list[dict] = [
    {
        "dimension": dimension,
        "score": 3,
        "evidence_quote": _LONG_QUOTE,
        "reasoning": "The quote states a criterion and commits to one side of the tradeoff.",
    }
    for dimension in RUBRIC_DIMENSIONS
]


def _first_question(transcript_turns: list[dict]) -> str:
    return next(
        t["content"]
        for t in transcript_turns
        if t.get("role") == "interviewer" and t.get("kind") == "question"
    )


def _last_answer(transcript_turns: list[dict]) -> str:
    return [
        t["content"]
        for t in transcript_turns
        if t.get("role") == "candidate" and t.get("kind") == "answer"
    ][-1]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_evaluation_request_fits_the_tpm_ceiling_for_every_golden_fixture(case) -> None:
    """Every real fixture, at its LAST answer (the longest point of that
    interview), with a worst-case running summary bolted on."""
    turns = case.transcript_turns
    messages = _build_evaluation_messages(
        case.case_world,
        _first_question(turns),
        _last_answer(turns),
        case.assessed_level,
        _FULL_PRIOR_SCORES,
    )
    system_tokens = _tokens(messages[0][1])
    human_tokens = _tokens(messages[1][1])
    requested = system_tokens + human_tokens + _MAX_TOKENS

    assert requested < _TPM_CEILING, (
        f"{case.id}: requested {requested} tokens (system {system_tokens} + human "
        f"{human_tokens} + max_tokens {_MAX_TOKENS}), at or over the {_TPM_CEILING} "
        f"TPM ceiling -- over by {requested - _TPM_CEILING}"
    )


# ==============================================================================
# THE STRESS CASE: the largest real curated world, a 500-word verbose answer,
# and the full running summary. Nothing in the fixture set combines all three,
# which is the point -- the fixtures measure what is sent today, this measures
# the worst thing production can send.
# ==============================================================================

_ANSWER_SENTENCE = (
    "I would prioritize the enterprise and API surface over the free consumer tier because the margin "
    "profile there funds the compute commitments that already exist, and because the sales cycle length "
    "in regulated accounts means the healthcare bet needs to start now even though it will not show "
    "results for at least two quarters, and I would track weekly active users alongside gross margin so "
    "the tradeoff stays visible rather than assumed"
)


def _verbose_answer(words: int) -> str:
    """High-entropy prose, not a repeated word pair: a two-word repeat
    compresses far below a real answer's tokens-per-word under BPE, which
    would understate the count this test exists to measure. Same construction
    as `test_interviewer_probe.py`'s `_build_ten_probe_transcript`."""
    source = (_ANSWER_SENTENCE + " ").split(" ")
    padded = source * (words // len(_ANSWER_SENTENCE.split(" ")) + 1)
    return " ".join(padded[:words])


def test_evaluation_request_fits_with_the_largest_world_and_a_verbose_answer() -> None:
    answer = _verbose_answer(500)
    messages = _build_evaluation_messages(
        _OPENAI_WORLD,
        "What is OpenAI's biggest threat over the next three years, and what would you do about it?",
        answer,
        "Senior PM",
        _FULL_PRIOR_SCORES,
    )
    system_tokens = _tokens(messages[0][1])
    human_tokens = _tokens(messages[1][1])
    requested = system_tokens + human_tokens + _MAX_TOKENS

    assert requested < _TPM_CEILING, (
        f"stress case: requested {requested} tokens (system {system_tokens} + human "
        f"{human_tokens} + max_tokens {_MAX_TOKENS}), at or over the {_TPM_CEILING} "
        f"TPM ceiling -- over by {requested - _TPM_CEILING}"
    )


# ==============================================================================
# The vacuity floor. A budget assertion passes trivially if the thing being
# budgeted never made it into the message -- an assembler that silently
# dropped the answer, the world, or the running summary would make every
# assertion above GREENER, which is the wrong direction for a bug to move a
# test. These pin that the counted string actually contains what it is
# supposed to be paying for.
# ==============================================================================


def test_the_assembled_message_actually_carries_what_it_is_budgeting() -> None:
    answer = _verbose_answer(500)
    question = "What is OpenAI's biggest threat over the next three years?"
    messages = _build_evaluation_messages(
        _OPENAI_WORLD, question, answer, "Senior PM", _FULL_PRIOR_SCORES
    )
    human = messages[1][1]

    assert answer in human, "the candidate's answer is not in the message being measured"
    assert question in human, "the question is not in the message being measured"
    assert "Senior PM" in human, "the assessed level is not in the message being measured"
    assert _OPENAI_WORLD["company"]["name"] in human, "the case world is not in the message being measured"
    assert _LONG_QUOTE in human, "prior_scores is not in the message being measured"


def test_an_empty_prior_scores_is_said_out_loud_not_rendered_as_an_empty_list() -> None:
    """The first answer of every interview takes this branch. `[]` under a
    heading about earlier scores reads as a gap; the sentence does not."""
    messages = _build_evaluation_messages(
        _OPENAI_WORLD, "Question?", "Answer.", "PM", []
    )
    human = messages[1][1]

    assert "(none yet - this is the first answer being scored)" in human
    assert "[]" not in human
