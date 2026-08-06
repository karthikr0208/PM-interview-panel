"""Declarative case table for the Planner golden suite.

**Fixtures are hand-written CASE WORLDS, not candidate profiles.** Per
AGENT-PLANNER-SPEC.md §5, corrected 2026-08-02: the Case Architect's golden
fixtures (`tests/golden/case_architect/fixtures/`) are that agent's INPUT,
not this one's. The Planner's input is `(assessed_level, case_world)`, so
these fixtures are hand-built `CaseWorld`-shaped JSON, one per scenario in
`tests/golden/case_architect/cases.py`, named identically (`apm_consumer` ->
`apm_consumer_world`) so the two suites describe the same seven situations
(spec §5 names five of the seven for this suite).

Fixture storage: JSON, not Python literals, under `fixtures/` -- same two
reasons as `case_architect/cases.py`: it keeps this module a table of
metadata and `check` callables rather than a wall of nested dict literals,
and a JSON fixture can be read, diffed, and edited without touching Python.

Deliberately does not import `app.agents.planner` at module level: this
module is imported at collection time by both `test_golden.py` and the
fully offline `test_assertions.py`. `check` callables are typed loosely
(`Any`) so they only need attribute access on whatever `plan_interview`
returns, not a hard import.

Each fixture file is `{"assessed_level": str, "case_world": dict}`, where
`case_world` conforms to AGENT-CASE-ARCHITECT-SPEC.md §2's `CaseWorld`
schema. None of these five carry `suits_categories` (that field is new in
story 3.5.3 and only the eight CURATED worlds under `app/cases/*.json` set
it) -- `select_category`'s documented fallback to the full category set
handles that, exactly the "untouched generative path" case. Every one of
the five fixtures here is asserted (in `test_assertions.py`) to pass
`case_architect/assertions.py`'s universal battery -- the positive control
spec §5 requires: a hand-built world a human considers good should pass the
Case Architect's own checks.

🔴 Story 3.5.3 rewrites these `check` callables for the new one-question-
plus-probe-ladder contract: `result.questions` is always length 1 now, so
every callable below reads `result.questions[0]` (the main question) AND
`result.questions[0].probe_ladder` (the follow-up angles) rather than
iterating a 5-7-question list -- scope and business-outcome language can
show up in either.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from tests.golden.planner.assertions import is_generic_question

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

FOUR_LEVELS = {"APM", "PM", "Senior PM", "GPM"}

# Same shape as case_architect/cases.py's identical constant -- catches the
# cheap, unambiguous scope failure (portfolio language leaking into an APM
# or PM's question). The full scope judgment is a human call at the phase
# gate, not this suite's job.
_PORTFOLIO_LANGUAGE = ("portfolio", "across our products", "multiple products", "business unit")

# Spec §5, fixture 4's assertion: "at least one question attaches to a
# business outcome". Mechanical proxy, not a semantic read: text that
# mentions revenue, headcount, growth, or a dollar/percent figure is
# reasoning about the business, not a single surface's UX detail.
_BUSINESS_OUTCOME_LANGUAGE = ("revenue", "headcount", "growth", "$", "%", "market position")


def _all_text(result: Any) -> list[str]:
    """The main question plus every probe angle's text -- the full surface
    a case-specific check should scan, now that coverage and scope can live
    in either the one question or its ladder (spec §3's rewrite)."""
    q = result.questions[0]
    return [q.question] + [p.angle for p in q.probe_ladder]


@dataclass(frozen=True)
class GoldenCase:
    fixture: str  # filename stem under fixtures/ (no .json)
    description: str  # spec §5's one-line summary, for readable test output
    # Takes (result, case_world) -- unlike case_architect's cases.py, this
    # suite's case-specific checks need the world alongside the result (to
    # check groundedness/genericness against IT specifically), not just the
    # result in isolation.
    check: Callable[[Any, dict], None]

    @property
    def id(self) -> str:
        return self.fixture

    @property
    def _payload(self) -> dict:
        return json.loads((FIXTURES_DIR / f"{self.fixture}.json").read_text(encoding="utf-8"))

    @property
    def assessed_level(self) -> str:
        return self._payload["assessed_level"]

    @property
    def case_world(self) -> dict:
        return self._payload["case_world"]


def _check_apm_consumer_world(result: Any, case_world: dict) -> None:
    """Spec §5 fixture 1: the question and its probe ladder are
    feature-scoped, not portfolio-scoped."""
    for text in _all_text(result):
        text_lower = text.lower()
        leaked = [w for w in _PORTFOLIO_LANGUAGE if w in text_lower]
        assert not leaked, (
            f"apm_consumer_world: reads portfolio-scale, not single-feature: "
            f"{leaked} in {text!r}"
        )


def _check_pm_b2b_world(result: Any, case_world: dict) -> None:
    """Spec §5 fixture 2: product-area scope -- neither APM's narrower
    single-feature slice nor GPM's portfolio breadth."""
    for text in _all_text(result):
        text_lower = text.lower()
        leaked = [w for w in _PORTFOLIO_LANGUAGE if w in text_lower]
        assert not leaked, (
            f"pm_b2b_world: reads portfolio-scale, not one product area: "
            f"{leaked} in {text!r}"
        )


def _check_senior_pm_platform_world(result: Any, case_world: dict) -> None:
    """Spec §5 fixture 3: the question carries ambiguity, not a single
    right answer. Mechanical proxy, one question now instead of many: the
    main question's own `grounded_in` names more than one world fact/
    entity, which is the shape of a question that requires weighing a
    tradeoff rather than recalling a single number."""
    q = result.questions[0]
    assert len(q.grounded_in) >= 2, (
        "senior_pm_platform_world: the question is grounded in fewer than "
        f"two world facts ({q.grounded_in!r}) -- reads as a single-fact "
        "lookup, not real ambiguity"
    )


def _check_gpm_portfolio_world(result: Any, case_world: dict) -> None:
    """Spec §5 fixture 4: the question or its probe ladder attaches to a
    business outcome (revenue, headcount, market position), not a single
    surface's metric."""
    outcome_hits = [text for text in _all_text(result) if any(
        term in text.lower() for term in _BUSINESS_OUTCOME_LANGUAGE
    )]
    assert outcome_hits, (
        "gpm_portfolio_world: nothing in the question or probe ladder "
        "mentions a business outcome (revenue, headcount, growth, market "
        "position) -- reads as feature-level, not portfolio-level"
    )


def _check_sparse_world(result: Any, case_world: dict) -> None:
    """Spec §5 fixture 5: a thin case world still yields a grounded
    question rather than a generic one -- the agent must not degrade into
    vagueness when under-informed. The main question must fail
    `is_generic_question` against this world (i.e. contain a proper noun or
    figure from it)."""
    question = result.questions[0].question
    assert not is_generic_question(question, case_world), (
        f"sparse_world: question names no entity or figure from the (thin) "
        f"world, which is the exact degradation this fixture exists to "
        f"catch: {question!r}"
    )


CASES: tuple[GoldenCase, ...] = (
    GoldenCase(
        fixture="apm_consumer_world",
        description="APM, consumer mobile world -> questions are feature-scoped, not portfolio-scoped",
        check=_check_apm_consumer_world,
    ),
    GoldenCase(
        fixture="pm_b2b_world",
        description="PM, B2B SaaS world -> questions carry product-area scope",
        check=_check_pm_b2b_world,
    ),
    GoldenCase(
        fixture="senior_pm_platform_world",
        description="Senior PM, platform world -> questions carry ambiguity, not a single right answer",
        check=_check_senior_pm_platform_world,
    ),
    GoldenCase(
        fixture="gpm_portfolio_world",
        description="GPM, portfolio world -> at least one question attaches to a business outcome",
        check=_check_gpm_portfolio_world,
    ),
    GoldenCase(
        fixture="sparse_world",
        description="PM, thin world -> still yields grounded questions rather than generic ones",
        check=_check_sparse_world,
    ),
)
