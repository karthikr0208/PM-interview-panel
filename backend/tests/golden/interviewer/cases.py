"""Declarative case table for the Interviewer golden suite.

**Fixtures here are NOT case worlds.** Per AGENT-INTERVIEWER-SPEC.md §5 and
the story 3.1 brief, this package's own fixture files hold only the
interviewer-specific parts of each case -- which planner fixture to load,
the planned question, and the clarifying question -- and a `world_fixture`
pointer. The `case_world` itself is read at test time from
`tests/golden/planner/fixtures/<world_fixture>.json`, never copied. This
coupling is deliberate (spec §5): a `CaseWorld` schema change must break
every downstream suite loudly, rather than leaving this package quietly
describing a world shape that no longer exists.

Fixture storage: JSON, not Python literals, same two reasons as
`planner/cases.py` and `case_architect/cases.py`: it keeps this module a
table of metadata and `check` callables rather than a wall of nested dict
literals, and a JSON fixture can be read, diffed, and edited without
touching Python.

Deliberately does not import `app.agents.interviewer` (or a
`ClarificationAnswer` type that does not exist yet, story 3.2): this module
is imported at collection time by both `test_golden.py` and the fully
offline `test_assertions.py`, and must stay importable while that agent
module does not exist. `check` callables are typed loosely (`Any`) for the
same reason -- they only need attribute access on whatever
`answer_clarification` eventually returns, per spec §3's schema sketch.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from tests.golden.interviewer.assertions import (
    echoes_false_premise,
    grounded_in_is_empty,
    missing_grounding,
    refusal_names_silence,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# Planner's fixtures dir, per the reuse rule above -- the ONLY place a
# `case_world` is read from in this package.
_PLANNER_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "planner" / "fixtures"


@dataclass(frozen=True)
class GoldenCase:
    fixture: str  # filename stem under fixtures/ (no .json) -- THIS package's fixture
    description: str  # spec §5's one-line summary, for readable test output
    # Takes (result, case_world) -- same shape as planner/cases.py's
    # GoldenCase.check, for the same reason: a case-specific check needs
    # the world alongside the result to judge groundedness/premise-handling
    # against IT specifically, not just the result in isolation.
    check: Callable[[Any, dict], None]

    @property
    def id(self) -> str:
        return self.fixture

    @property
    def _payload(self) -> dict:
        return json.loads((FIXTURES_DIR / f"{self.fixture}.json").read_text(encoding="utf-8"))

    @property
    def world_fixture(self) -> str:
        return self._payload["world_fixture"]

    @property
    def planned_question(self) -> str:
        return self._payload["planned_question"]

    @property
    def clarifying_question(self) -> str:
        return self._payload["clarifying_question"]

    @property
    def case_world(self) -> dict:
        payload = json.loads(
            (_PLANNER_FIXTURES_DIR / f"{self.world_fixture}.json").read_text(encoding="utf-8")
        )
        return payload["case_world"]


def _check_apm_consumer_world(result: Any, case_world: dict) -> None:
    """Spec §5 fixture 1: a fact the world states plainly -> answered,
    grounded, can_answer=True."""
    assert result.can_answer is True, (
        f"apm_consumer_world: expected can_answer=True for a plainly-stated "
        f"fact, got False -- answer={result.answer!r}"
    )
    assert not grounded_in_is_empty(result.grounded_in), "apm_consumer_world: grounded_in is empty"
    assert missing_grounding(result.grounded_in, case_world) == [], (
        "apm_consumer_world: grounded_in entry not found in case_world"
    )


def _check_pm_b2b_world(result: Any, case_world: dict) -> None:
    """Spec §5 fixture 2: a fact reachable only by combining two
    `supporting_facts` -> grounded synthesis, not a single-fact lookup.
    Mechanical proxy: `grounded_in` must cite at least two distinct facts,
    the shape of an answer that combined rather than looked up."""
    assert result.can_answer is True, (
        f"pm_b2b_world: expected can_answer=True (the world DOES support "
        f"this via two combined facts), got False -- answer={result.answer!r}"
    )
    assert len(set(result.grounded_in)) >= 2, (
        f"pm_b2b_world: grounded_in has fewer than 2 distinct entries "
        f"({result.grounded_in!r}) -- reads as a single-fact lookup, not the "
        f"synthesis this fixture requires"
    )
    assert missing_grounding(result.grounded_in, case_world) == [], (
        "pm_b2b_world: grounded_in entry not found in case_world"
    )


def _check_senior_pm_platform_world(result: Any, case_world: dict) -> None:
    """Spec §5 fixture 3, REVERSED by story 3.5.4 (PHASE-3.5-SPEC.md "THREE
    DECISIONS" #2 -- the refusal branch is deleted): a fact the world does
    not contain -> can_answer False, but now INVENT-AND-RECORD, not refusal.
    Asserts a non-empty `improvised_fact`, an `answer` that states the
    invented assumption as given rather than naming the world's silence, and
    `grounded_in` still non-empty (the invention still sits next to
    something real)."""
    assert result.can_answer is False, (
        f"senior_pm_platform_world: expected can_answer=False -- eNPS is "
        f"nowhere in this world -- got True with answer={result.answer!r}"
    )
    assert (result.improvised_fact or "").strip(), (
        f"senior_pm_platform_world: can_answer=False but improvised_fact is "
        f"blank -- the invented eNPS figure was never recorded, so a later "
        f"call has nothing to repeat consistently"
    )
    assert not grounded_in_is_empty(result.grounded_in), (
        "senior_pm_platform_world: grounded_in is empty -- an invented "
        "answer must still sit next to something the world DOES say"
    )
    assert not refusal_names_silence(result.answer), (
        f"senior_pm_platform_world: answer still reads as a refusal (names "
        f"the world's silence) instead of stating the invented assumption "
        f"as given -- the refusal branch was supposed to be gone: {result.answer!r}"
    )


def _check_gpm_portfolio_world(result: Any, case_world: dict) -> None:
    """Spec §5 fixture 4, the adversarial one: a leading question
    presupposing a FALSE fact (business banking is the LARGEST line, when
    the world states it is the smallest at $28M ARR). The answer must not
    accept the premise -- mechanical proxy: it must not claim business
    banking is the largest/biggest line.

    🔴 WIDENED 2026-08-07. The original check below looks for the false
    claim being ASSERTED ("banking" plus "largest"), and the live failure of
    2026-08-07 shows that is not the shape these take: the interviewer
    accepted a false premise in a SUBORDINATE CLAUSE and built on it ("Yes,
    the shrinking market makes..."), never asserting it outright. Against
    this fixture the equivalent evasion is "to protect business banking's
    lead, I would..." -- which the original check walks straight past.
    `echoes_false_premise` covers that shape; both run, because they fail on
    different things. See DEV-STATE § Decisions 2026-08-07.

    🔴 AND THIS FIXTURE HAS NEVER RUN LIVE. Per the agent table, only
    `apm_consumer_world` and `senior_pm_platform_world` were ever smoked.
    The regression shipped with its own test sitting right here, unexecuted
    -- which is the real lesson, not the narrowness of the assertion."""
    lowered = result.answer.lower()
    accepted_premise = (
        ("business banking" in lowered or "banking" in lowered)
        and ("largest" in lowered or "biggest" in lowered)
        and "smallest" not in lowered
    )
    assert not accepted_premise, (
        f"gpm_portfolio_world: answer appears to accept the false premise "
        f"that business banking is the largest line: {result.answer!r}"
    )
    assert not echoes_false_premise(result.answer, ("largest", "most established", "its lead")), (
        f"gpm_portfolio_world: answer echoes the false premise (business "
        f"banking being the largest / most established line, or having a "
        f"'lead' to protect) with no correcting language beside it -- the "
        f"world states it is the SMALLEST at $28M ARR: {result.answer!r}"
    )


def _check_sparse_world(result: Any, case_world: dict) -> None:
    """Spec §5 fixture 5, REVERSED by story 3.5.4, same reasoning as fixture
    3: a fact a thin world is silent on (no year-ago churn figure exists at
    all) -> can_answer=False, but now degrades to a RECORDED invention, not
    a refusal. This is also the thinnest world in the suite, so it is the
    hardest case for "ground the invention in the nearest real thing" --
    if it passes here, the invention design holds even with very little to
    lean on."""
    assert result.can_answer is False, (
        f"sparse_world: expected can_answer=False -- no year-ago churn "
        f"figure exists in this world -- got True with answer={result.answer!r}"
    )
    assert (result.improvised_fact or "").strip(), (
        f"sparse_world: can_answer=False but improvised_fact is blank -- "
        f"the invented churn figure was never recorded"
    )
    assert not grounded_in_is_empty(result.grounded_in), (
        "sparse_world: grounded_in is empty -- an invented answer must "
        "still sit next to something the world DOES say"
    )
    assert not refusal_names_silence(result.answer), (
        f"sparse_world: answer still reads as a refusal (names the world's "
        f"silence) instead of stating the invented assumption as given: "
        f"{result.answer!r}"
    )


CASES: tuple[GoldenCase, ...] = (
    GoldenCase(
        fixture="apm_consumer_world",
        description="A fact the world states plainly -> answered, grounded, can_answer=True",
        check=_check_apm_consumer_world,
    ),
    GoldenCase(
        fixture="pm_b2b_world",
        description="A fact reachable only by combining two supporting_facts -> grounded synthesis",
        check=_check_pm_b2b_world,
    ),
    GoldenCase(
        fixture="senior_pm_platform_world",
        description="A fact the world does not contain -> can_answer=False, invents and records it",
        check=_check_senior_pm_platform_world,
    ),
    GoldenCase(
        fixture="gpm_portfolio_world",
        description="A leading question presupposing a false fact -> does not accept the premise",
        check=_check_gpm_portfolio_world,
    ),
    GoldenCase(
        fixture="sparse_world",
        description="A fact a thin world is silent on -> degrades to a recorded invention, not a refusal",
        check=_check_sparse_world,
    ),
)
