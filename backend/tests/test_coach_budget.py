"""Offline token-budget test for `app/agents/coach.py`'s `_build_coach_messages`.

No network, no LLM, no marker: it assembles messages and counts them with
`tiktoken`, exactly like `test_evaluator_budget.py`, whose shape this follows.
It runs inside `pytest tests -m "not live"` and costs nothing.

🔴 `max_tokens` is imported from the agent module, NEVER redeclared here.
`test_evaluator_budget.py` pinned its own `_MAX_TOKENS = 2048` literal while
`evaluate_answer` shipped 4096, so it sat green measuring a request shape that
no longer existed and would have kept passing well past the ceiling (DEV-STATE
§ Decisions 2026-08-11). Importing the constant makes that drift impossible
rather than merely unlikely.

`Requested = system + human + max_tokens` (see `app/llm.py`'s `get_llm` note --
`max_tokens` is part of the REQUEST size on Groq, not merely a cap on the
reply), against the 8,000 tokens-per-minute ceiling.

PHASE-5-SPEC.md § 2 projected ~6,290 tokens and said plainly that the number
was PROJECTED, not measured. This file is what replaces the projection with a
measurement, and it is deliberately written before the graph node exists --
3.5.4's trap, verbatim: compute the fit BEFORE building the loop, not after.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import tiktoken

from app.agents.coach import COACH_MAX_TOKENS, _build_coach_messages
from app.agents.planner import RUBRIC_DIMENSIONS

_TPM_CEILING = 8000

_CASES_DIR = Path(__file__).resolve().parent.parent / "app" / "cases"


def _tokens(text: str) -> int:
    return len(tiktoken.get_encoding("o200k_base").encode(text))


# 220 characters, matching `test_evaluator_budget.py`'s `_LONG_QUOTE` rationale:
# a real `evidence_quote` is a whole sentence the Evaluator copied out of an
# answer, and a short stand-in would understate the input that grows with the
# interview.
_LONG_QUOTE = (
    "I would prioritize the enterprise surface over the free consumer tier because the margin profile "
    "there funds the compute commitments that already exist, and the sales cycle in regulated accounts "
    "means the bet has to start now."
)

_LONG_REASONING = (
    "The quote states a criterion and commits to one side of the tradeoff, which is the anchor-4 "
    "behaviour for this dimension at this level, and it survives the pushback two turns later."
)

assert len(_LONG_QUOTE) >= 220, "the worst-case quote stopped being worst-case"


def _worst_case_evaluations() -> list[dict]:
    """The largest input this agent can be handed: five scored answers, every
    dimension scored in every one, each carrying a long quote and long
    reasoning.

    🔴 Deliberately worse than any real interview. `_QUESTIONS_THIS_PHASE` is 1
    and probes were cut 8 -> 4 on 2026-08-08, so a real session produces at most
    five scored answers -- and PHASE-4-SPEC § 1 measured a real one evidencing
    THREE of five dimensions per answer, not five. This fixture assumes full
    coverage on every turn, which is the shape that would blow the ceiling if
    anything does.
    """
    return [
        {
            "turn_idx": turn,
            "dimension_scores": [
                {
                    "dimension": dimension,
                    "score": 3,
                    "evidence_quote": _LONG_QUOTE,
                    "reasoning": _LONG_REASONING,
                }
                for dimension in RUBRIC_DIMENSIONS
            ],
        }
        for turn in range(5)
    ]


_REAL_WORLDS = sorted(_CASES_DIR.glob("*.json"))

assert _REAL_WORLDS, "no curated case worlds found -- this test would pass vacuously"


@pytest.mark.parametrize("world_path", _REAL_WORLDS, ids=lambda p: p.stem)
def test_coach_request_fits_the_tpm_ceiling_for_every_real_world(world_path: Path) -> None:
    """Every one of the eight curated real worlds, at the worst-case evaluation
    load. The world is the largest single component of the prompt, so the
    binding case is the biggest world rather than the busiest interview."""
    case_world = json.loads(world_path.read_text(encoding="utf-8"))
    messages = _build_coach_messages(
        case_world,
        "What is this company's biggest threat over the next three years?",
        "Senior PM",
        _worst_case_evaluations(),
    )
    system_tokens = _tokens(messages[0][1])
    human_tokens = _tokens(messages[1][1])
    requested = system_tokens + human_tokens + COACH_MAX_TOKENS

    assert requested < _TPM_CEILING, (
        f"{world_path.stem}: requested {requested} tokens (system {system_tokens} + human "
        f"{human_tokens} + max_tokens {COACH_MAX_TOKENS}), at or over the {_TPM_CEILING} "
        f"TPM ceiling -- over by {requested - _TPM_CEILING}"
    )


def test_the_budget_test_reads_the_agents_own_max_tokens() -> None:
    """🔴 The regression guard for the 2026-08-11 finding itself.

    The Evaluator's budget test declared its own `_MAX_TOKENS = 2048` literal
    and went on passing after `evaluate_answer` moved to 4096, measuring a
    request shape that no longer shipped. This asserts the coupling that
    prevents the same thing here: the number this file measures with is the
    number the agent actually sends.
    """
    from app.agents import coach

    assert COACH_MAX_TOKENS is coach.COACH_MAX_TOKENS
    assert "max_tokens=COACH_MAX_TOKENS" in Path(coach.__file__).read_text(encoding="utf-8"), (
        "generate_coach_report no longer passes COACH_MAX_TOKENS to get_llm -- the budget "
        "measured here has decoupled from the request actually sent, which is exactly the "
        "drift this test exists to prevent"
    )
