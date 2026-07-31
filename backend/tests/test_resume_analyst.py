"""Phase 1 story 1.3 acceptance test, per PHASE-1-SPEC.md's Automated tests
table: output validates against the schema, `assessed_level` is one of the
four values, and `low_confidence_fields` populates on an ambiguous resume.

Reuses the golden `06_founder_no_pm_title` fixture rather than inventing a
ninth resume, per the brief for story 1.3a. "Founder, never called a PM" is
named explicitly in AGENT-RESUME-ANALYST-SPEC.md §3 as a non-linear-background
trigger for `low_confidence_fields`, so it is the fixture built for exactly
this assertion. The golden suite (`tests/golden/resume_analyst/`) is the real
regression suite for this agent; this file stays small on purpose.

`app.agents.resume_analyst` does not exist yet as this file is written. The
import is lazy (inside the session-scoped `analyse_resume` fixture, and
inside the one test that also needs the `ResumeAnalysis` type), for the same
reason as `tests/golden/resume_analyst/test_golden.py`: a module-level import
here would make `pytest tests -m "not live"` error during collection for this
file, not merely deselect its tests.
"""
from __future__ import annotations

import pytest

from tests.golden.resume_analyst.cases import FIXTURES_DIR

pytestmark = pytest.mark.live

FOUNDER_FIXTURE = FIXTURES_DIR / "06_founder_no_pm_title.txt"


@pytest.fixture(scope="session")
def analyse_resume():
    from app.agents.resume_analyst import analyse_resume as fn

    return fn


async def test_schema_level_and_low_confidence_on_an_ambiguous_resume(analyse_resume) -> None:
    from app.agents.resume_analyst import ResumeAnalysis

    result = await analyse_resume(FOUNDER_FIXTURE.read_text(encoding="utf-8"), role="deep")

    assert isinstance(result, ResumeAnalysis)
    assert result.assessed_level in {"APM", "PM", "Senior PM", "GPM"}
    assert result.low_confidence_fields, (
        "06_founder_no_pm_title is the non-linear-background trigger from "
        "AGENT-RESUME-ANALYST-SPEC.md §3 (founder, never called a PM); an "
        f"empty low_confidence_fields here is a real failure, got {result.low_confidence_fields}"
    )
