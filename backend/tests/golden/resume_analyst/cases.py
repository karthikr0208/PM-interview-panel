"""Declarative case table for the Resume Analyst golden suite.

Encodes only what varies case to case: which fixture, the per-case
assertions from AGENT-RESUME-ANALYST-SPEC.md §5's table, and the forbidden
tokens (name, university, nationality detail) unique to that fixture. The
universal assertions (schema membership, verbatim quoting, dash ban,
forbidden-token ban) apply to every case unconditionally and live in
`test_golden.py`, built on the checkers in `assertions.py` -- they are not
duplicated here.

Deliberately does not import `app.agents.resume_analyst` (or its
`ResumeAnalysis` type): this module is imported at collection time by both
`test_golden.py` and the fully offline `test_assertions.py`, and must stay
importable while that agent module does not exist yet. `check` callables are
typed loosely (`Any`) for the same reason -- they only need attribute access
on whatever `analyse_resume` eventually returns.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@dataclass(frozen=True)
class GoldenCase:
    fixture: str  # filename under fixtures/
    description: str  # spec §5's one-line summary, for readable test output
    forbidden_tokens: tuple[str, ...]  # name / university / nationality detail
    check: Callable[[Any], None]  # case-specific assertions; raises AssertionError on failure
    # False only where the fixture genuinely states no results, so an empty
    # notable_outcomes is the honest answer rather than a silent no-op. See
    # assertions.empty_quote_lists.
    expect_outcomes: bool = True

    @property
    def id(self) -> str:
        return self.fixture.removesuffix(".txt")

    @property
    def resume_text(self) -> str:
        return (FIXTURES_DIR / self.fixture).read_text(encoding="utf-8")


FOUR_LEVELS = {"APM", "PM", "Senior PM", "GPM"}


def _check_apm_rotational(result: Any) -> None:
    assert result.assessed_level == "APM", result.assessed_level
    assert result.low_confidence_fields == [], (
        f"expected no uncertainty on a clean APM resume, got {result.low_confidence_fields}"
    )


def _check_pm_owns_area(result: Any) -> None:
    assert result.assessed_level == "PM", result.assessed_level


def _check_senior_pm_product_line(result: Any) -> None:
    assert result.assessed_level == "Senior PM", result.assessed_level


def _check_gpm_portfolio(result: Any) -> None:
    assert result.assessed_level == "GPM", result.assessed_level


def _check_title_scope_mismatch(result: Any) -> None:
    assert result.assessed_level in {"PM", "Senior PM"}, result.assessed_level
    assert "assessed_level" in result.low_confidence_fields, (
        f"title says Group PM, bullets are single-surface feature work: "
        f"expected 'assessed_level' flagged, got {result.low_confidence_fields}"
    )


def _check_founder_no_pm_title(result: Any) -> None:
    assert result.assessed_level in {"PM", "Senior PM", "GPM"}, result.assessed_level
    assert result.low_confidence_fields, "founder with no PM title: expected some uncertainty flag"


def _check_duties_no_outcomes(result: Any) -> None:
    assert result.low_confidence_fields, "plausible seniority, zero results: expected a flag"
    assert result.candidate_profile.notable_outcomes == [], (
        "resume states zero results; an honest agent reports none rather than inventing some: "
        f"got {result.candidate_profile.notable_outcomes}"
    )


def _check_engineer_transition(result: Any) -> None:
    assert result.assessed_level in {"APM", "PM"}, result.assessed_level
    assert "years_pm_experience" in result.low_confidence_fields, (
        "8 years engineering, 18 months PM: expected 'years_pm_experience' flagged, "
        f"got {result.low_confidence_fields}"
    )


CASES: tuple[GoldenCase, ...] = (
    GoldenCase(
        fixture="01_apm_rotational.txt",
        description="14 months, APM program, feature slices -> APM, no uncertainty",
        forbidden_tokens=(
            "Ingrid Solberg",
            "Solberg",
            "Norwegian University of Science and Technology",
            "NTNU",
            "Norway",
        ),
        check=_check_apm_rotational,
    ),
    GoldenCase(
        fixture="02_pm_owns_area.txt",
        description="4 years, owns a checkout surface, sets its roadmap -> PM",
        forbidden_tokens=(
            "Renata Alcántara",
            "Alcántara",
            "Instituto Tecnológico Autónomo de México",
            "ITAM",
            "Guadalajara",
        ),
        check=_check_pm_owns_area,
    ),
    GoldenCase(
        fixture="03_senior_pm_product_line.txt",
        description="7 years, owns a product line, names a bet not taken -> Senior PM",
        forbidden_tokens=(
            "Kwame Boateng",
            "Boateng",
            "University of Ghana",
            "Ghana",
        ),
        check=_check_senior_pm_product_line,
    ),
    GoldenCase(
        fixture="04_gpm_portfolio.txt",
        description="11 years, manages 4 PMs, owns a P&L -> GPM",
        forbidden_tokens=(
            "Haruto Kobayashi",
            "Kobayashi",
            "Keio University",
            "Japan",
        ),
        check=_check_gpm_portfolio,
    ),
    GoldenCase(
        fixture="05_title_scope_mismatch.txt",
        description=(
            "Titled Group PM, bullets are single-surface feature work -> "
            "PM or Senior PM, assessed_level flagged low-confidence"
        ),
        forbidden_tokens=(
            "Camille Béranger",
            "Béranger",
            "Sciences Po",
            "French",
        ),
        check=_check_title_scope_mismatch,
    ),
    GoldenCase(
        fixture="06_founder_no_pm_title.txt",
        description="5 years running own startup, never called a PM -> uncertainty populated",
        forbidden_tokens=(
            "Devika Chaudhary",
            "Chaudhary",
            "Birla Institute of Technology and Science",
            "BITS Pilani",
            "India",
        ),
        check=_check_founder_no_pm_title,
    ),
    GoldenCase(
        fixture="07_duties_no_outcomes.txt",
        description="Plausible seniority, zero stated results -> uncertainty populated, no invented outcomes",
        forbidden_tokens=(
            "Nadia Kowalska",
            "Kowalska",
            "Warsaw University of Technology",
            "Poland",
        ),
        check=_check_duties_no_outcomes,
        expect_outcomes=False,
    ),
    GoldenCase(
        fixture="08_engineer_transition.txt",
        description="8 years engineering, 18 months PM -> APM or PM, years_pm_experience flagged",
        forbidden_tokens=(
            "Owen Fitzgerald",
            "Fitzgerald",
            "Trinity College Dublin",
            "Ireland",
        ),
        check=_check_engineer_transition,
    ),
)
