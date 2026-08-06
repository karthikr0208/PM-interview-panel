"""The eight curated, real-company case worlds (PHASE-3.5-SPEC.md 3.5.2),
which replace the Case Architect's generation, and `select_case_world`'s
deterministic pick among them.

Offline only: no network, no LLM, no database. `app/cases/<slug>.json` are
checked-in fixtures read straight off disk, and `CaseWorld` validation is a
pure Pydantic call -- nothing here needs `-m live`.

Reuses the Case Architect's own golden assertions
(`tests/golden/case_architect/assertions.py`) rather than duplicating them:
per AGENT-PLANNER-SPEC.md §5, a hand-built world a human considers good
passing those assertions is a positive control on the assertions
themselves, not a separate battery. Also reuses the Planner's own
`no_dash_variants` (`tests/golden/planner/assertions.py`) for the em-dash /
en-dash ban rather than rewriting it, per the brief for this story.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.agents.case_architect import CaseWorld
from app.cases import ALL_SLUGS, select_case_world
from app.graph.build import _make_generate_case_world
from app.questions.shapes import CATEGORIES, select_shape_for_world
from tests.golden.case_architect.assertions import (
    banned_round_numbers,
    blank_or_short_fields,
    contains_banned_register_name,
    contains_placeholder_token,
    count_out_of_range,
    implied_acv_implausible,
    organic_ratio_below_floor,
    stage_employee_mismatch,
)
from tests.golden.planner.assertions import no_dash_variants, world_haystack

_CASES_DIR = Path(__file__).resolve().parent.parent / "app" / "cases"

FOUR_LEVELS = ("APM", "PM", "Senior PM", "GPM")

# Real, genuinely-round public milestones that would otherwise fail
# `banned_round_numbers`: the roundness IS the headline fact for these three
# (Cursor's "$100M ARR", OpenAI's and Anthropic's reported run-rates), not a
# model reaching for a lazy number -- but the string is indistinguishable
# from a generative failure by inspection alone.
#
# Waived HERE, at the curated-worlds call site, keyed by (slug, field) --
# deliberately NOT inside the shared `is_round_dollar_amount` in
# tests/golden/case_architect/assertions.py. An earlier version of this
# exemption lived there as a global allowlist, and independent re-verification
# caught that it silently disarmed the check for EVERY caller, including the
# Case Architect's own live generation golden suite, whose entire job is
# catching a model that invents "$100M" for a fictional company. Scoping it
# to three named (slug, field) pairs means it can never cover a generated
# world, and a reader can see exactly which numbers were waived and why.
_KNOWN_REAL_ROUND_AMOUNTS: dict[tuple[str, str], tuple[str, str]] = {
    ("cursor", "metrics.arr_usd"): (
        "$100M",
        "Cursor/Anysphere ARR milestone, widely reported ~mid-2025 as one of "
        "the fastest SaaS companies ever to reach it -- the roundness is the "
        "reported fact, not an invented figure.",
    ),
    ("openai", "metrics.arr_usd"): (
        "$10B",
        "OpenAI's reported annualized revenue run-rate, ~mid-2025.",
    ),
    ("anthropic", "metrics.arr_usd"): (
        "$3B",
        "Anthropic's reported annualized revenue run-rate, ~mid-2025.",
    ),
}


def test_is_round_dollar_amount_has_no_global_allowlist() -> None:
    """Regression guard: the three real figures above must still read as
    round when the shared checker is called directly, unscoped. If this ever
    goes False, the exemption has leaked back into the shared function and
    silently disarmed the live generation golden suite's catch for a model
    inventing "$100M" -- exactly the failure independent re-verification
    caught on 2026-08-06."""
    from tests.golden.case_architect.assertions import is_round_dollar_amount

    for value, _slug in (("$100M", "cursor"), ("$10B", "openai"), ("$3B", "anthropic")):
        assert is_round_dollar_amount(value) is True, (
            f"{value!r} must still be flagged round by the unscoped shared checker"
        )


def _load_raw(slug: str) -> dict:
    return json.loads((_CASES_DIR / f"{slug}.json").read_text(encoding="utf-8"))


def _load_world(slug: str) -> CaseWorld:
    return CaseWorld.model_validate(_load_raw(slug))


# ==============================================================================
# Box 1 (brief): all eight worlds exist, load, and validate.
# ==============================================================================


def test_eight_slugs_defined() -> None:
    """Pins the count named in the brief -- a fixture silently dropped from
    disk (or from ALL_SLUGS) would otherwise pass every other check here,
    the same vacuity-floor lesson the golden suites already apply to their
    own case tables."""
    assert len(ALL_SLUGS) == 8, ALL_SLUGS
    assert set(ALL_SLUGS) == {
        "reddit",
        "duolingo",
        "youtube",
        "airbnb",
        "figma",
        "cursor",
        "openai",
        "anthropic",
    }


@pytest.mark.parametrize("slug", ALL_SLUGS)
def test_world_file_exists_and_validates(slug: str) -> None:
    world = _load_world(slug)
    assert isinstance(world, CaseWorld)


# ==============================================================================
# Box 2 (brief): every world passes the Case Architect's own universal
# assertions -- the same battery test_golden.py runs against a generated
# world, applied here as a positive control on the assertions themselves.
# ==============================================================================


@pytest.mark.parametrize("slug", ALL_SLUGS)
def test_world_passes_universal_assertions(slug: str) -> None:
    result = _load_world(slug)

    # company.name is checked separately, with a much lower floor. The
    # default min_len=10 was tuned for the Case Architect's own two-word
    # generated names ("Verdant Ledger"); every one of these eight REAL
    # company names ("Reddit", "Figma", "OpenAI") is a single, short, real
    # word, and min_len=10 would reject the true name for being exactly what
    # it is. Widened at the call site rather than in the shared
    # blank_or_short_fields helper -- min_len is already a parameter there,
    # so this is supplying a smaller one for a field that legitimately needs
    # it, not loosening the check for the prose fields, which keep the
    # original floor.
    empty_name = blank_or_short_fields({"company.name": result.company.name}, min_len=3)
    assert not empty_name, f"{slug}: company.name empty or near-empty: {result.company.name!r}"

    string_fields = {
        "company.one_line": result.company.one_line,
        "market.description": result.market.description,
        "situation.prompt": result.situation.prompt,
        "situation.tension": result.situation.tension,
        "situation.leadership_belief": result.situation.leadership_belief,
    }
    empty = blank_or_short_fields(string_fields)
    assert not empty, f"{slug}: vacuity floor -- fields empty or near-empty: {empty}"

    assert not count_out_of_range(result.supporting_facts, 8, 15), (
        f"{slug}: supporting_facts has {len(result.supporting_facts)} entries, want 8-15"
    )
    assert not count_out_of_range(result.market.competitors, 2, 4), (
        f"{slug}: competitors has {len(result.market.competitors)}, want 2-4"
    )
    assert not count_out_of_range(result.situation.options, 2, 3), (
        f"{slug}: options has {len(result.situation.options)}, want 2-3"
    )

    percentages = {
        "market.growth_rate_pct": result.market.growth_rate_pct,
        "metrics.yoy_growth_pct": result.metrics.yoy_growth_pct,
        "metrics.gross_margin_pct": result.metrics.gross_margin_pct,
        "metrics.monthly_churn_pct": result.metrics.monthly_churn_pct,
    }
    dollar_amounts = {
        "market.size_usd": result.market.size_usd,
        "metrics.arr_usd": result.metrics.arr_usd,
    }
    round_violations = banned_round_numbers(percentages, dollar_amounts)

    # Waive exactly the named (slug, field) exemptions above, and only after
    # confirming each one was ACTUALLY caught -- the positive control that
    # proves the exemption is waiving a real hit, not silently matching
    # nothing (the same vacuity-floor shape this project's other denial
    # assertions require).
    for (exempt_slug, field), (value, _citation) in _KNOWN_REAL_ROUND_AMOUNTS.items():
        if exempt_slug != slug:
            continue
        actual = dollar_amounts.get(field)
        assert actual == value, (
            f"{slug}: exemption for {field} expects {value!r}, fixture has {actual!r} -- "
            "the exemption no longer matches the data it was written for"
        )
        violation = f"{field}={value}"
        assert violation in round_violations, (
            f"{slug}: expected {violation!r} to be caught by banned_round_numbers before "
            "waiving it -- an exemption that matches nothing proves nothing"
        )
        round_violations.remove(violation)

    assert not round_violations, f"{slug}: fake-round number(s): {round_violations}"
    assert not organic_ratio_below_floor(percentages), (
        f"{slug}: too many round-looking percentages across the world: {percentages}"
    )

    names_and_text = (
        [result.company.name]
        + [c.name for c in result.market.competitors]
        + list(result.supporting_facts)
        + [result.situation.leadership_belief]
    )
    leaked = contains_banned_register_name(*names_and_text)
    assert leaked is None, f"{slug}: banned-register name leaked: {leaked!r}"

    placeholder = contains_placeholder_token(
        *result.supporting_facts,
        result.situation.prompt,
        result.situation.tension,
        result.situation.leadership_belief,
        *result.situation.options,
    )
    assert placeholder is None, f"{slug}: algebra placeholder in candidate-facing copy: {placeholder!r}"

    assert not stage_employee_mismatch(result.company.stage, result.company.employees), (
        f"{slug}: {result.company.employees} employees implausible for stage {result.company.stage!r}"
    )
    assert not implied_acv_implausible(result.metrics.arr_usd, result.metrics.customer_count), (
        f"{slug}: implied ACV implausible: arr={result.metrics.arr_usd} "
        f"customers={result.metrics.customer_count}"
    )


# ==============================================================================
# Box 3 (brief): every world carries a non-empty as_of.
# ==============================================================================


@pytest.mark.parametrize("slug", ALL_SLUGS)
def test_world_carries_nonempty_as_of(slug: str) -> None:
    world = _load_world(slug)
    assert world.as_of and world.as_of.strip(), f"{slug}: as_of is empty"


# ==============================================================================
# Box 4 (brief): no em-dashes or en-dashes anywhere -- these strings reach a
# candidate. Reuses the Planner's own no_dash_variants rather than rewriting
# it.
# ==============================================================================


@pytest.mark.parametrize("slug", ALL_SLUGS)
def test_world_has_no_dash_variants(slug: str) -> None:
    world = _load_world(slug)
    haystack = world_haystack(world.model_dump()) + " \n " + world.as_of
    assert no_dash_variants(haystack), f"{slug}: em-dash or en-dash found in world text"


def test_the_dash_check_would_actually_fire() -> None:
    """Guards the guard, same reasoning as test_user_facing_copy.py's own
    'finds real user-facing copy' checks: a haystack builder that silently
    matched nothing would make the test above pass vacuously."""
    assert not no_dash_variants("a real problem, not a fake one—see above")
    assert not no_dash_variants("2020–2024 growth")


# ==============================================================================
# Box 4b (PHASE-3.5-SPEC.md 3.5.3): every curated world carries
# `suits_categories`, 2-3 entries, each one of the Planner's four canonical
# categories -- a typo'd or empty category list would silently fall back to
# the full category set (`select_category`'s documented behaviour for the
# untouched generative path) rather than failing loudly, so this is asserted
# here rather than trusted by construction.
# ==============================================================================


@pytest.mark.parametrize("slug", ALL_SLUGS)
def test_world_carries_suits_categories(slug: str) -> None:
    world = _load_world(slug)
    assert world.suits_categories, f"{slug}: suits_categories is empty"
    assert not count_out_of_range(world.suits_categories, 2, 3), (
        f"{slug}: suits_categories has {len(world.suits_categories)} entries, want 2-3"
    )
    unknown = set(world.suits_categories) - set(CATEGORIES)
    assert not unknown, f"{slug}: suits_categories names unknown categor{'y' if len(unknown)==1 else 'ies'} {unknown} (want a subset of {CATEGORIES})"


# ==============================================================================
# Box 5 (brief): select_case_world is deterministic.
# ==============================================================================


def test_select_case_world_is_deterministic() -> None:
    profile = {
        "years_pm_experience": 3.2,
        "domains": ["consumer", "marketplaces"],
        "product_types": ["mobile app"],
    }
    first = select_case_world("PM", profile)
    second = select_case_world("PM", profile)
    assert first.company.name == second.company.name
    assert first == second


def test_select_case_world_is_deterministic_across_several_profiles() -> None:
    """Same property, several different profiles -- not just one lucky
    input. Each profile's own repeat call must agree with itself."""
    profiles = [
        {},
        {"domains": ["fintech"]},
        {"years_pm_experience": 7.5, "notable_outcomes": ["shipped a payments product"]},
    ]
    for level in FOUR_LEVELS:
        for profile in profiles:
            first = select_case_world(level, profile)
            second = select_case_world(level, profile)
            assert first == second, f"non-deterministic pick for level={level!r} profile={profile!r}"


# ==============================================================================
# Box 6 (brief): every level resolves to a world.
# ==============================================================================


@pytest.mark.parametrize("level", FOUR_LEVELS)
def test_every_level_resolves_to_a_world(level: str) -> None:
    world = select_case_world(level, {"years_pm_experience": 2.0})
    assert isinstance(world, CaseWorld)
    assert world.company.name


def test_an_unrecognised_level_falls_back_rather_than_raising() -> None:
    """select_case_world's own documented contract: it must never be the
    reason an interview cannot start."""
    world = select_case_world("not_a_real_level", {})
    assert isinstance(world, CaseWorld)


# ==============================================================================
# Box 7 (story 3.5.4's own brief): the `generate_case_world` NODE
# (`app.graph.build._make_generate_case_world`), not just the pure selector
# above. This is the wiring the rest of this file never touched -- until
# 3.5.4 the node still awaited the generative Case Architect, so everything
# above was dead code in production and `suits_categories` was always empty
# at runtime. Offline: `rest_insert` is monkeypatched, so no database and no
# network; nothing here calls an LLM.
# ==============================================================================

_CURATED_COMPANY_NAMES = {
    "Reddit",
    "Duolingo",
    "YouTube",
    "Airbnb",
    "Figma",
    "Cursor",
    "OpenAI",
    "Anthropic",
}


@pytest.fixture
def recorded_inserts(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict]]:
    """Stubs `app.graph.build.rest_insert` (the binding the node actually
    calls, per the module's own `from app.supabase_client import
    rest_insert`) and records every call, so the node's three side effects
    can be asserted on without a database."""
    calls: list[tuple[str, dict]] = []

    async def _fake_rest_insert(table: str, payload: dict) -> dict:
        calls.append((table, payload))
        return {**payload, "id": "stub-id"}

    monkeypatch.setattr("app.graph.build.rest_insert", _fake_rest_insert)
    return calls


async def test_node_produces_a_curated_world_with_no_generative_call(
    recorded_inserts: list[tuple[str, dict]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The property that was silently false in production: the node's
    output carries a curated company AND a non-empty `suits_categories`,
    and the generative Case Architect is never invoked to get there.

    Patches `app.graph.build._generate_case_world` -- the exact binding
    name the pre-3.5.4 node called (`from app.agents.case_architect import
    generate_case_world as _generate_case_world`) -- to explode, with
    `raising=False` because that name no longer exists on the module after
    this story's change. `raising=False` still catches a regression: if a
    future edit reintroduces the import AND the call, it recreates this
    exact attribute in this exact module, which is what the call site would
    resolve at call time regardless of how it got bound. Patching
    `app.agents.case_architect.generate_case_world` directly would NOT
    catch that regression -- a `from X import Y as Z` binds its own
    reference at import time, so patching the source module's attribute
    afterward leaves an already-imported alias untouched. That gap is
    exactly the kind of vacuous-pass the brief warns about.
    """

    async def _explode(*args, **kwargs):
        raise AssertionError(
            "the generative Case Architect was called -- story 3.5.4's node "
            "must use the deterministic curated selector instead"
        )

    monkeypatch.setattr("app.graph.build._generate_case_world", _explode, raising=False)

    node = _make_generate_case_world()
    state = {
        "session_id": "11111111-1111-1111-1111-111111111111",
        "assessed_level": "PM",
        "candidate_profile": {"years_pm_experience": 3.2, "domains": ["consumer"]},
    }

    result = await node(state)

    world_dict = result["case_world"]
    assert world_dict["company"]["name"] in _CURATED_COMPANY_NAMES, world_dict["company"]
    assert world_dict["suits_categories"], "suits_categories is empty -- category scoping cannot engage"


async def test_node_output_feeds_a_shape_whose_category_the_world_declares(
    recorded_inserts: list[tuple[str, dict]]
) -> None:
    """End-to-end proof that category scoping (story 3.5.3) now actually
    engages: the world this node hands downstream, fed straight into
    `select_shape_for_world`, resolves to a shape whose category is one the
    world itself declares in `suits_categories` -- not just any of the four
    canonical categories."""
    node = _make_generate_case_world()
    state = {
        "session_id": "22222222-2222-2222-2222-222222222222",
        "assessed_level": "GPM",
        "candidate_profile": {"years_pm_experience": 9.0, "domains": ["ai"]},
    }

    result = await node(state)
    world_dict = result["case_world"]

    shape = select_shape_for_world("GPM", world_dict["suits_categories"])
    assert shape.category in world_dict["suits_categories"], (
        f"selected shape category {shape.category!r} is not one of the world's own "
        f"suits_categories {world_dict['suits_categories']!r}"
    )


async def test_node_writes_all_three_recorded_side_effects(
    recorded_inserts: list[tuple[str, dict]]
) -> None:
    """The `started` agent_events row, the `case_worlds` audit insert, and
    the `done` agent_events row -- unchanged by the swap from the generative
    call to the curated selector, per the brief. A regression that dropped
    one silently would break the orchestration column in the UI, which
    reads these rows."""
    node = _make_generate_case_world()
    state = {
        "session_id": "33333333-3333-3333-3333-333333333333",
        "assessed_level": "APM",
        "candidate_profile": {},
    }

    await node(state)

    tables = [table for table, _ in recorded_inserts]
    assert tables.count("case_worlds") == 1, tables
    assert tables == ["agent_events", "case_worlds", "agent_events"], tables

    started_payload = recorded_inserts[0][1]
    case_world_payload = recorded_inserts[1][1]
    done_payload = recorded_inserts[2][1]

    assert started_payload["status"] == "started"
    assert started_payload["agent"] == "case_architect"
    assert case_world_payload["session_id"] == state["session_id"]
    assert case_world_payload["world"]["company"]["name"] in _CURATED_COMPANY_NAMES
    assert done_payload["status"] == "done"
    assert done_payload["agent"] == "case_architect"
    assert "duration_ms" in done_payload
