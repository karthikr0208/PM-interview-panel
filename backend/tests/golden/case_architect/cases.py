"""Declarative case table for the Case Architect golden suite.

**Fixture storage: JSON, not Python literals, under `fixtures/`.** Two
reasons, both concrete:

1. It mirrors resume_analyst's separation of content from structure --
   `cases.py` there stays a table of metadata and `check` callables, never a
   wall of resume text; the same split here keeps `cases.py` a table of
   metadata and `check` callables, never a wall of nested dict literals for
   seven `candidate_profile`s.
2. A JSON fixture can be read, diffed, and edited without touching Python,
   and importing it costs nothing -- `json.loads` on a stdlib type, not a
   `CandidateProfile` construction. `resume_analyst.CandidateProfile` exists
   already (story 1.2) and this agent's input is specified to mirror it
   field-for-field, but importing that model here would make this package's
   importability depend on `app.agents.resume_analyst` staying stable, for
   no benefit -- the golden harness only needs dicts, since
   `generate_case_world`'s signature takes `candidate_profile: dict`, not a
   `CandidateProfile` instance (spec §1).

Each fixture file is `{"assessed_level": str, "candidate_profile": dict}`,
with `candidate_profile` matching `CandidateProfile`'s seven fields exactly:
`years_pm_experience`, `domains`, `product_types`, `company_contexts`,
`scope_evidence`, `notable_outcomes`, `people_leadership`.

Deliberately does not import `app.agents.case_architect` (or a `CaseWorld`
type that does not exist yet): this module is imported at collection time by
both `test_golden.py` and the fully offline `test_assertions.py`, and must
stay importable while that agent module does not exist (story 2.3). `check`
callables are typed loosely (`Any`) for the same reason -- they only need
attribute access on whatever `generate_case_world` eventually returns, per
spec §2's schema sketch.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

FOUR_LEVELS = {"APM", "PM", "Senior PM", "GPM"}


@dataclass(frozen=True)
class GoldenCase:
    fixture: str  # filename stem under fixtures/ (no .json)
    description: str  # spec §5's one-line summary, for readable test output
    check: Callable[[Any], None]  # case-specific assertions; raises AssertionError on failure

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
    def candidate_profile(self) -> dict:
        return self._payload["candidate_profile"]


# Keyword sets used by more than one case-specific check below. Small and
# explicit, matching spec §3's scope-by-level table -- not an attempt at a
# general "detect scope" NLP heuristic. These catch the cheap, unambiguous
# failure (portfolio language leaking into an APM's prompt, or the reverse);
# the full scope judgment is the phase gate's job (PHASE-2-SPEC.md §4).
_PORTFOLIO_LANGUAGE = ("portfolio", "across our products", "multiple products", "business unit")
_SINGLE_FEATURE_LANGUAGE = ("this feature", "this screen", "this flow", "this surface")


def _check_apm_consumer(result: Any) -> None:
    """Spec §3: an APM's situation is one feature or surface, with a clear
    owner above -- not multiple products or a portfolio-level outcome."""
    prompt_lower = result.situation.prompt.lower()
    leaked = [w for w in _PORTFOLIO_LANGUAGE if w in prompt_lower]
    assert not leaked, (
        f"apm_consumer: situation reads portfolio-scale, not single-feature: "
        f"{leaked} in {result.situation.prompt!r}"
    )


def _check_pm_b2b_saas(result: Any) -> None:
    """Spec §3: a PM's situation is one product area, end to end -- neither
    a single narrow feature slice (APM's scope) nor a portfolio (GPM's)."""
    prompt_lower = result.situation.prompt.lower()
    portfolio_leak = [w for w in _PORTFOLIO_LANGUAGE if w in prompt_lower]
    assert not portfolio_leak, (
        f"pm_b2b_saas: situation reads portfolio-scale, not one product area: "
        f"{portfolio_leak} in {result.situation.prompt!r}"
    )


def _check_senior_pm_platform(result: Any) -> None:
    """Spec §3: a Senior PM's situation carries real ambiguity across a
    product line or domain -- narrower than GPM, but not a bounded single
    feature choice either. `options` genuinely competing (no single option
    that dominates on its face) is a human judgment at the phase gate; this
    checks the mechanical floor -- more than one option, each substantive
    enough to state, which the universal battery's count check already
    partly covers. Kept intentionally thin here to avoid duplicating it."""
    assert len(result.situation.tension) >= 20, (
        f"senior_pm_platform: tension reads too thin for real ambiguity: "
        f"{result.situation.tension!r}"
    )


def _check_gpm_portfolio(result: Any) -> None:
    """Spec §3: a GPM's situation spans multiple products and names a
    business outcome (revenue, headcount, market position), not a single
    surface's metric."""
    prompt_lower = result.situation.prompt.lower()
    single_feature_leak = [w for w in _SINGLE_FEATURE_LANGUAGE if w in prompt_lower]
    assert not single_feature_leak, (
        f"gpm_portfolio: situation reads single-feature, not portfolio-scale: "
        f"{single_feature_leak} in {result.situation.prompt!r}"
    )


def _check_sparse_profile(result: Any) -> None:
    """Spec §5 fixture 5: the point of this fixture is that an
    under-informed profile must still produce a complete, consistent world.
    Deliberately lenient on WHAT the world contains -- there is nothing in
    an almost-empty profile to check the world's content against -- but the
    full universal assertion battery in `test_golden.py` still runs
    unconditionally for this case, which is where "complete and consistent"
    is actually enforced. This callable exists to document that choice, not
    to add a second layer of checking."""
    assert result.situation.prompt, "sparse_profile: empty situation prompt"


def _check_fintech_domain(result: Any) -> None:
    """Spec §5 fixture 6: domain is recognisably fintech, and critically,
    the generated company is NOT the candidate's actual (fixture-fabricated)
    employer, "Ledgerline Financial" -- string inequality is enough per the
    brief; this is not a semantic-similarity check."""
    assert result.company.name != "Ledgerline Financial", (
        f"fintech_domain: generated company reuses the candidate's fabricated "
        f"employer name verbatim: {result.company.name!r}"
    )
    fintech_terms = ("credit", "lend", "loan", "underwrit", "payment", "risk", "bank", "financ")
    haystack = f"{result.company.one_line} {result.market.description}".lower()
    assert any(term in haystack for term in fintech_terms), (
        f"fintech_domain: neither company.one_line nor market.description reads as "
        f"fintech: {result.company.one_line!r} / {result.market.description!r}"
    )


def _check_career_changer(result: Any) -> None:
    """Spec §5 fixture 7: domain should not assume PM-native vocabulary,
    since the profile shows an engineering background transitioning into
    product. Mechanically, this checks that the situation prompt is phrased
    as a decision (a "what would you do" framing), not as internal PM
    jargon a first-year engineer-turned-PM would not yet have absorbed."""
    jargon_terms = ("north star metric", "okrs", "jtbd", "rice score")
    prompt_lower = result.situation.prompt.lower()
    leaked = [t for t in jargon_terms if t in prompt_lower]
    assert not leaked, (
        f"career_changer: situation assumes PM-native jargon: {leaked} in "
        f"{result.situation.prompt!r}"
    )


CASES: tuple[GoldenCase, ...] = (
    GoldenCase(
        fixture="apm_consumer",
        description="APM, consumer mobile profile -> single-feature scope situation",
        check=_check_apm_consumer,
    ),
    GoldenCase(
        fixture="pm_b2b_saas",
        description="PM, B2B SaaS profile -> one product area end to end",
        check=_check_pm_b2b_saas,
    ),
    GoldenCase(
        fixture="senior_pm_platform",
        description="Senior PM, platform/infra profile -> real ambiguity, not a feature choice",
        check=_check_senior_pm_platform,
    ),
    GoldenCase(
        fixture="gpm_portfolio",
        description="GPM, multi-product profile -> spans products, names a business outcome",
        check=_check_gpm_portfolio,
    ),
    GoldenCase(
        fixture="sparse_profile",
        description="PM, almost-empty profile -> still a complete, consistent world",
        check=_check_sparse_profile,
    ),
    GoldenCase(
        fixture="fintech_domain",
        description="Senior PM, fintech profile -> recognisably fintech, not the fake employer",
        check=_check_fintech_domain,
    ),
    GoldenCase(
        fixture="career_changer",
        description="PM, engineer-in-transition profile -> no PM-native jargon assumed",
        check=_check_career_changer,
    ),
)
