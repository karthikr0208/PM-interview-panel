"""Declarative case table for the Evaluator golden suite.

**Fixtures here are NOT case worlds**, same rule as
`tests/golden/interviewer/cases.py` (§5, and the story 3.1 brief it
inherited): this package's own fixture files hold the Evaluator-specific
parts of each case -- a pointer to which world to load, the assessed_level,
and a hand-written transcript -- never a copy of `case_world` itself. The
world is read at test time from `tests/golden/planner/fixtures/<world_fixture>
.json`, via `world_fixture`, exactly like the interviewer suite's own
`case_world` property. A `CaseWorld` schema change must break every
downstream suite loudly, not leave a stale copy sitting here.

**ONE exception, and it is documented, not silent**: fixture
`karthik_live_airbnb_senior_pm` sets `world_fixture` to `null` and carries
its own `case_world` inline. This is the real corpus PHASE-4-SPEC.md 4.1
names (Karthik's 2026-08-07 interview, session
`ac569e9b-db6a-4a17-9a73-b5c1ed43e59f`, read directly from the
`case_worlds` and `transcript_turns` tables on 2026-08-08). It has nowhere
to point TO -- it is not a copy of anything, it is the one place this
specific case_world exists on disk -- so embedding it here is the source,
not the duplication the pointer rule exists to prevent.

Deliberately DOES import `app.agents.evaluator` for `AnswerEvaluation` /
`DimensionScore` -- unlike `interviewer/cases.py`'s deliberate avoidance of
`app.agents.interviewer`. The reason those differ: at story 3.1,
`ClarificationAnswer` did not exist yet either, so importing it would have
broken collection. Here, the SCHEMA (not the agent) is story 4.1's own
deliverable and exists from the moment this file is written -- only
`evaluate_answer`, the function, does not exist yet (story 4.2), and only
`test_golden.py`'s lazily-imported fixture touches that name. Importing the
schema costs nothing and lets `check` callables construct real
`AnswerEvaluation` instances instead of staying typed as `Any`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.agents.evaluator import AnswerEvaluation

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# Planner's fixtures dir, per the reuse rule above -- the ONLY place a
# `case_world` is read from in this package, except the one documented
# exception (the real corpus, which has no planner fixture to point at).
_PLANNER_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "planner" / "fixtures"


@dataclass(frozen=True)
class GoldenCase:
    fixture: str  # filename stem under fixtures/ (no .json) -- THIS package's fixture
    description: str  # one-line summary, for readable test output
    # Takes the real AnswerEvaluation once story 4.2's evaluate_answer exists
    # and test_golden.py calls this -- case-specific, so it can check
    # e.g. "not_assessed is exactly {market_accuracy, point_of_view}" for
    # THIS fixture's known content, which no universal assertion can.
    check: Callable[[AnswerEvaluation], None]

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
    def transcript_turns(self) -> list[dict]:
        return self._payload["transcript_turns"]

    @property
    def world_fixture(self) -> str | None:
        return self._payload.get("world_fixture")

    @property
    def case_world(self) -> dict:
        world_fixture = self.world_fixture
        if world_fixture is None:
            # The one documented exception -- see module docstring.
            return self._payload["case_world"]
        payload = json.loads((_PLANNER_FIXTURES_DIR / f"{world_fixture}.json").read_text(encoding="utf-8"))
        return payload["case_world"]


# ==============================================================================
# Case-specific checks. Each takes the real `AnswerEvaluation` a future
# `evaluate_answer` call would return (story 4.2) -- unexercised until then,
# per this story's acceptance criterion ("the suite is deliberately RED").
# ==============================================================================


def _check_karthik_live_airbnb(result: AnswerEvaluation) -> None:
    """The real corpus (PHASE-4-SPEC.md 4.1's named fixture). Karthik's own
    read of this interview, recorded in the phase spec's dimension_coverage
    table (business_model_fluency 4, decision_quality 4, structural_clarity
    1, market_accuracy 0, point_of_view 0): three dimensions evidenced, two
    not. `not_assessed` must be EXACTLY the two that got zero probe
    coverage -- not a superset, not a subset -- since this is the one
    fixture in the suite with a Karthik-verified ground truth to hold the
    agent to exactly.
    """
    assert set(result.not_assessed) == {"market_accuracy", "point_of_view"}, (
        f"karthik_live_airbnb: expected not_assessed == "
        f"{{'market_accuracy', 'point_of_view'}}, got {result.not_assessed!r}"
    )
    scored = {ds.dimension for ds in result.dimension_scores}
    assert scored == {"business_model_fluency", "decision_quality", "structural_clarity"}, (
        f"karthik_live_airbnb: expected exactly business_model_fluency, "
        f"decision_quality, structural_clarity scored, got {sorted(scored)}"
    )


def _check_apm_full_coverage(result: AnswerEvaluation) -> None:
    """Every dimension has something to point evidence_quote at (see the
    fixture's own note) -- the counterweight to the narrow/extreme fixtures
    below. not_assessed must be empty, and all five dimensions scored."""
    assert result.not_assessed == [], (
        f"apm_consumer_world_full_coverage: expected not_assessed == [], "
        f"got {result.not_assessed!r}"
    )
    scored = {ds.dimension for ds in result.dimension_scores}
    assert len(scored) == 5, (
        f"apm_consumer_world_full_coverage: expected all 5 dimensions scored, "
        f"got {sorted(scored)}"
    )


def _check_pm_b2b_narrow_coverage(result: AnswerEvaluation) -> None:
    """See the fixture's own note: a clear decision with real revenue
    figures, but no competitor named, no signposting, no defended stance."""
    assert set(result.not_assessed) == {"market_accuracy", "point_of_view", "structural_clarity"}, (
        f"pm_b2b_world_narrow_coverage: expected not_assessed == "
        f"{{'market_accuracy', 'point_of_view', 'structural_clarity'}}, "
        f"got {result.not_assessed!r}"
    )


def _check_senior_pm_platform_level_pair(result: AnswerEvaluation) -> None:
    """Shared check for BOTH halves of the level pair (PM and GPM) -- see
    both fixtures' notes. Coverage must be identical at both levels; only
    the SCORE is expected to differ (PRD §7's anchor-shift rule), and
    comparing the actual scores across the pair is test_golden.py's job
    (story 4.2, live), not this offline check's."""
    assert set(result.not_assessed) == {"business_model_fluency"}, (
        f"senior_pm_platform_world_level_pair: expected not_assessed == "
        f"{{'business_model_fluency'}}, got {result.not_assessed!r}"
    )


def _check_gpm_extreme_narrow(result: AnswerEvaluation) -> None:
    """See the fixture's own note: a one-line decision with nothing else to
    score. Only decision_quality should have evidence -- everything else is
    silence, not a low score standing in for silence."""
    assert set(result.not_assessed) == {
        "business_model_fluency",
        "market_accuracy",
        "structural_clarity",
        "point_of_view",
    }, (
        f"gpm_portfolio_world_extreme_narrow: expected four of five "
        f"not_assessed, got {result.not_assessed!r}"
    )
    scored = {ds.dimension for ds in result.dimension_scores}
    assert scored == {"decision_quality"}, (
        f"gpm_portfolio_world_extreme_narrow: expected only decision_quality "
        f"scored, got {sorted(scored)}"
    )


def _check_sparse_framework_narration(result: AnswerEvaluation) -> None:
    """See the fixture's own note: three frameworks named, none applied.
    framework_narration must be True, and not_assessed must be AT LEAST the
    four dimensions with nothing but framework labels behind them --
    structural_clarity is left to the real evaluator's judgment (superset
    check, not an exact-set check, unlike every other fixture above)."""
    assert result.framework_narration is True, (
        "sparse_world_framework_narration: expected framework_narration=True "
        "-- three named frameworks (RICE, build-versus-buy, a 2x2 matrix), "
        "none applied to Palewell's own numbers"
    )
    expected_minimum = {"business_model_fluency", "market_accuracy", "decision_quality", "point_of_view"}
    assert expected_minimum <= set(result.not_assessed), (
        f"sparse_world_framework_narration: expected not_assessed to include "
        f"at least {sorted(expected_minimum)}, got {result.not_assessed!r}"
    )


CASES: tuple[GoldenCase, ...] = (
    GoldenCase(
        fixture="karthik_live_airbnb_senior_pm",
        description="The real corpus: one question, eight probes -- three dimensions evidenced, two not",
        check=_check_karthik_live_airbnb,
    ),
    GoldenCase(
        fixture="apm_consumer_world_full_coverage",
        description="A dense answer touching all five dimensions -> not_assessed is empty",
        check=_check_apm_full_coverage,
    ),
    GoldenCase(
        fixture="pm_b2b_world_narrow_coverage",
        description="A clear decision with revenue figures, but no market read, structure, or stance",
        check=_check_pm_b2b_narrow_coverage,
    ),
    GoldenCase(
        fixture="senior_pm_platform_world_level_pair_pm",
        description="Level-pair fixture (PM half) -- same transcript as the GPM half, for anchor comparison",
        check=_check_senior_pm_platform_level_pair,
    ),
    GoldenCase(
        fixture="senior_pm_platform_world_level_pair_gpm",
        description="Level-pair fixture (GPM half) -- same transcript as the PM half, for anchor comparison",
        check=_check_senior_pm_platform_level_pair,
    ),
    GoldenCase(
        fixture="gpm_portfolio_world_extreme_narrow",
        description="A one-line decision with nothing else -> only decision_quality has evidence",
        check=_check_gpm_extreme_narrow,
    ),
    GoldenCase(
        fixture="sparse_world_framework_narration",
        description="Three frameworks named, none applied -> framework_narration=True",
        check=_check_sparse_framework_narration,
    ),
)
