"""Declarative case table for the Coach golden suite.

**Fixtures here are NOT case worlds**, same rule as `tests/golden/evaluator/cases.py`
and `tests/golden/interviewer/cases.py`: this package's own fixture files hold only
the Coach-specific parts of each case -- a pointer to which world to load, the
question, the assessed_level, and a hand-written `answer_evaluations`-shaped payload
(mirroring `app/graph/state.py`'s `answer_evaluations: Annotated[list[dict],
operator.add]`) -- never a copy of `case_world` itself.

Unlike the Evaluator/Planner suites, which point `world_fixture` at a HAND-WRITTEN
world under `tests/golden/planner/fixtures/`, this package's `world_source` points
directly at a REAL curated world shipped to candidates, under
`backend/app/cases/<world_source>.json` (the same eight files
`tests/test_coach_budget.py` iterates for its own TPM-ceiling check). The brief for
this suite is explicit that a real curated world is wanted here, not a synthetic
one -- so the pointer target differs from the Evaluator's, even though the
"pointer, never a copy" discipline is identical.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.agents.coach import CoachReport

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# The real curated worlds this product actually ships -- backend/app/cases/*.json.
# The ONLY place a `case_world` is read from in this package; see module docstring.
_CASES_DIR = Path(__file__).resolve().parents[3] / "app" / "cases"


@dataclass(frozen=True)
class GoldenCase:
    fixture: str  # filename stem under fixtures/ (no .json)
    description: str  # one-line summary, for readable test output
    # Takes the real CoachReport `generate_coach_report` returned, plus THIS case's
    # evaluations -- case-specific, so it can check e.g. "every improvement is a
    # 'moment'" for full_coverage's known shape, which no universal assertion can.
    check: Callable[[CoachReport, list[dict]], None]

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
    def question(self) -> str:
        return self._payload["question"]

    @property
    def evaluations(self) -> list[dict]:
        return self._payload["evaluations"]

    @property
    def world_source(self) -> str:
        return self._payload["world_source"]

    @property
    def case_world(self) -> dict:
        return json.loads((_CASES_DIR / f"{self.world_source}.json").read_text(encoding="utf-8"))


# ==============================================================================
# Case-specific checks, run in ADDITION to the shared checks in test_golden.py.
# ==============================================================================


def _check_full_coverage(report: CoachReport, evaluations: list[dict]) -> None:
    """full_coverage.json evidences all five dimensions, so
    `unevidenced_dimensions(evaluations)` is empty -- there is no dimension left
    for a 'gap' improvement to name truthfully, and one that appeared anyway
    would be fabricated. Every improvement must therefore be a 'moment'."""
    non_moment = [i.kind for i in report.improvements if i.kind != "moment"]
    assert not non_moment, (
        f"full_coverage: every dimension was evidenced in this session, so "
        f"unevidenced_dimensions() is empty and a 'gap' improvement would be "
        f"fabricated -- got non-'moment' kind(s) {non_moment}"
    )


def _check_thin_coverage(report: CoachReport, evaluations: list[dict]) -> None:
    """thin_coverage.json evidences only decision_quality and
    business_model_fluency -- market_accuracy, structural_clarity, and
    point_of_view are never scored, so `unevidenced_dimensions(evaluations)`
    returns those three. At least one improvement must take the 'gap' path
    (the realistic case per PHASE-4-SPEC §1), and every 'gap' must name a
    dimension genuinely in that unevidenced set."""
    from app.agents.coach import unevidenced_dimensions

    gaps = [i for i in report.improvements if i.kind == "gap"]
    assert gaps, (
        "thin_coverage: expected at least one 'gap' improvement -- coverage is "
        "thin enough that unevidenced_dimensions() is non-empty, and a report "
        "with none is coaching around the gap rather than naming it"
    )
    absent = set(unevidenced_dimensions(evaluations))
    bad = sorted(g.dimension for g in gaps if g.dimension not in absent)
    assert not bad, (
        f"thin_coverage: gap improvement(s) named dimension(s) {bad}, which are "
        f"NOT in the unevidenced set {sorted(absent)} for this session -- a gap "
        f"must only name a dimension that genuinely never came up"
    )


CASES: tuple[GoldenCase, ...] = (
    GoldenCase(
        fixture="full_coverage",
        description="All five dimensions evidenced across three turns -> no gap available, three moments",
        check=_check_full_coverage,
    ),
    GoldenCase(
        fixture="thin_coverage",
        description="Only decision_quality and business_model_fluency evidenced -> gaps available and plentiful",
        check=_check_thin_coverage,
    ),
)
