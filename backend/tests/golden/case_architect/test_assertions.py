"""Offline tests for the checkers in `assertions.py`. No network, no marker,
no import of `app.agents.case_architect` -- collects and runs under
`pytest tests -m "not live"` today, before that agent exists.

Precedent (CLAUDE.md / DEV-STATE, story 0.6, 1.3a, 1.5): a denial assertion
is not trusted until it has been shown to FAIL against input it should
reject. Every checker below gets both directions -- accepts the honest
value, rejects the dishonest one named in AGENT-CASE-ARCHITECT-SPEC.md §5's
positive-control table -- plus a guard against the specific failure mode
story 1.3a taught this project: a checker that returns "nothing wrong" on
an empty or missing input, which lets an agent that produced NOTHING pass
the check vacuously.
"""
from __future__ import annotations

import pytest

from tests.golden.case_architect.assertions import (
    banned_round_numbers,
    blank_or_short_fields,
    contains_banned_register_name,
    contains_placeholder_token,
    count_out_of_range,
    implied_acv_implausible,
    is_round_dollar_amount,
    organic_ratio_below_floor,
    parse_dollar_amount,
    stage_employee_mismatch,
)
from tests.golden.case_architect.cases import CASES, FOUR_LEVELS

# ==============================================================================
# Row: "No fake-round numbers in any numeric field"
# Positive control (spec §5): a world with 50.0% growth and $1M ARR.
# ==============================================================================


def test_banned_round_numbers_accepts_an_organic_world() -> None:
    percentages = {
        "market.growth_rate_pct": 31.4,
        "metrics.yoy_growth_pct": 22.7,
        "metrics.gross_margin_pct": 71.3,
        "metrics.monthly_churn_pct": 2.9,
    }
    dollar_amounts = {"market.size_usd": "$3.2B", "metrics.arr_usd": "$4.7M"}
    assert banned_round_numbers(percentages, dollar_amounts) == []


def test_banned_round_numbers_rejects_the_positive_control() -> None:
    """The exact positive control from spec §5's table: 50.0% growth, $1M ARR."""
    percentages = {"metrics.yoy_growth_pct": 50.0}
    dollar_amounts = {"metrics.arr_usd": "$1M"}
    violations = banned_round_numbers(percentages, dollar_amounts)
    assert "metrics.yoy_growth_pct=50.0" in violations
    assert "metrics.arr_usd=$1M" in violations


def test_20_percent_gross_margin_is_not_banned() -> None:
    """Spec §8's explicit caution: 20% may be a legitimate gross margin and
    must not be flagged by a blunt round-number rule. Pins the banned set's
    boundary rather than trusting it does the right thing by construction."""
    assert banned_round_numbers({"metrics.gross_margin_pct": 20.0}, {}) == []


def test_is_round_dollar_amount_true_for_one_million_variants() -> None:
    assert is_round_dollar_amount("$1M") is True
    assert is_round_dollar_amount("$1,000,000") is True


def test_is_round_dollar_amount_false_for_an_organic_value() -> None:
    assert is_round_dollar_amount("$4.7M") is False
    assert is_round_dollar_amount("$3.2B") is False


def test_is_round_dollar_amount_raises_on_unparseable_input() -> None:
    """A checker that silently returned False on garbage input would let a
    malformed field slip past the round-number check unnoticed."""
    with pytest.raises(ValueError):
        is_round_dollar_amount("three point two billion dollars")


@pytest.mark.parametrize("bad", ["", "N/A", "unknown", "TBD", "$18.6 million"])
def test_banned_round_numbers_reports_unparseable_amounts_instead_of_raising(bad) -> None:
    """`is_round_dollar_amount` raises on garbage, deliberately, and the test
    above pins that. But `arr_usd` and `size_usd` are NOT in test_golden's
    vacuity-floor field list -- they are figures, not prose -- so these five
    entirely plausible model outputs reach the checker unguarded.

    Letting the raw ValueError escape still fails the case, so the gate held
    either way. It failed with a message that reads as a broken harness rather
    than a malformed field, and that distinction decides whether the next
    person fixes the prompt or relaxes the assertion. Found by a from-scratch
    probe on 2026-08-02, not by this suite.
    """
    violations = banned_round_numbers({"metrics.gross_margin_pct": 71.3}, {"metrics.arr_usd": bad})
    assert violations, f"{bad!r} produced no violation at all"
    assert "not a parseable dollar amount" in violations[0], violations


def test_organic_ratio_below_floor_accepts_mostly_decimal_percentages() -> None:
    assert organic_ratio_below_floor({"a": 31.4, "b": 22.7, "c": 9.0}) is False


def test_organic_ratio_below_floor_rejects_mostly_round_percentages() -> None:
    """None of these individually hit `_BANNED_ROUND_PERCENTAGES`, so this
    world would sail past `banned_round_numbers` -- the exact gap
    `organic_ratio_below_floor` exists to close: 10.0%, 30.0%, 90.0% reads
    just as fabricated in aggregate as a lone 50.0% does alone."""
    assert organic_ratio_below_floor({"a": 10.0, "b": 30.0, "c": 90.0}) is True


def test_organic_ratio_below_floor_vacuously_fails_on_no_percentages() -> None:
    """A world with nothing to check has not earned a pass -- mirrors
    `empty_quote_lists`'s precedent of treating "nothing to evaluate" as a
    failure, not a vacuous success."""
    assert organic_ratio_below_floor({}) is True


# ==============================================================================
# Row: "No banned-register names"
# Positive control (spec §5): a world whose company is "Acme" or a person is
# "John Doe".
# ==============================================================================


def test_contains_banned_register_name_accepts_organic_names() -> None:
    assert contains_banned_register_name("Verdant Ledger", "Northline Analytics") is None


def test_contains_banned_register_name_rejects_acme() -> None:
    assert contains_banned_register_name("Acme", "Verdant Ledger") == "Acme"


def test_contains_banned_register_name_rejects_john_doe() -> None:
    assert contains_banned_register_name("John Doe", "Verdant Ledger") == "John Doe"


def test_contains_banned_register_name_is_case_insensitive() -> None:
    assert contains_banned_register_name("ACME CORP") == "ACME CORP"


def test_banned_name_tokens_do_not_include_a_plausible_organic_name() -> None:
    """Guards the register list itself: it must be a small explicit
    blacklist, not something broad enough to reject a real-sounding name."""
    assert contains_banned_register_name("Meridian Analytics") is None
    assert contains_banned_register_name("Priya Natarajan") is None


# ==============================================================================
# Rows: "supporting_facts has 8-15 entries" / "competitors has 2-4 entries" /
# "options has 2-3 entries" -- all built on `count_out_of_range`.
# ==============================================================================


def test_count_out_of_range_accepts_a_value_within_bounds() -> None:
    assert count_out_of_range([1, 2, 3], 2, 4) is False


def test_count_out_of_range_accepts_the_exact_boundaries() -> None:
    """Boundary check, not merely "somewhere in the middle" -- a degenerate
    off-by-one implementation would slip past a looser test."""
    assert count_out_of_range([1, 2], 2, 4) is False
    assert count_out_of_range([1, 2, 3, 4], 2, 4) is False


def test_count_out_of_range_rejects_just_below_and_just_above_bounds() -> None:
    assert count_out_of_range([1], 2, 4) is True
    assert count_out_of_range([1, 2, 3, 4, 5], 2, 4) is True


def test_supporting_facts_count_accepts_eight_to_fifteen() -> None:
    assert count_out_of_range([f"fact {i}" for i in range(8)], 8, 15) is False
    assert count_out_of_range([f"fact {i}" for i in range(15)], 8, 15) is False


def test_supporting_facts_count_rejects_the_positive_control() -> None:
    """Spec §5's positive control: a world with 2 facts, and one with 40."""
    assert count_out_of_range([f"fact {i}" for i in range(2)], 8, 15) is True
    assert count_out_of_range([f"fact {i}" for i in range(40)], 8, 15) is True


def test_competitors_count_accepts_two_to_four() -> None:
    assert count_out_of_range(["a", "b"], 2, 4) is False
    assert count_out_of_range(["a", "b", "c", "d"], 2, 4) is False


def test_competitors_count_rejects_the_positive_control() -> None:
    """Spec §5's positive control: a world with 0 competitors."""
    assert count_out_of_range([], 2, 4) is True


def test_options_count_accepts_two_to_three() -> None:
    assert count_out_of_range(["expand", "hold"], 2, 3) is False
    assert count_out_of_range(["expand", "hold", "retreat"], 2, 3) is False


def test_options_count_rejects_the_positive_control() -> None:
    """Spec §5's positive control: a world with 1 option, which has no
    tension by construction -- a single option cannot be "one of several
    defensible directions."""
    assert count_out_of_range(["expand"], 2, 3) is True


# ==============================================================================
# Row: "Internal consistency" -- the two cheapest checks per spec §5:
# stage-vs-employees and implied ACV.
# Positive control (spec §5): a world whose numbers contradict each other.
# ==============================================================================


def test_stage_employee_mismatch_accepts_plausible_pairs() -> None:
    assert stage_employee_mismatch("seed", 12) is False
    assert stage_employee_mismatch("public", 4200) is False


def test_stage_employee_mismatch_rejects_seed_with_900_employees() -> None:
    """Spec §5's named example, first half."""
    assert stage_employee_mismatch("seed", 900) is True


def test_stage_employee_mismatch_rejects_public_with_11_employees() -> None:
    """Spec §5's named example, second half."""
    assert stage_employee_mismatch("public", 11) is True


def test_stage_employee_mismatch_treats_an_unknown_stage_as_unconstrained() -> None:
    """Documents the deliberate choice in `assertions.py`: an unrecognised
    stage string does not raise here, because validating `stage` against the
    schema's Literal is `CaseWorld`'s job, not this plausibility check's."""
    assert stage_employee_mismatch("not_a_real_stage", 5) is False


def test_parse_dollar_amount_handles_suffixes_and_commas() -> None:
    assert parse_dollar_amount("$4.7M") == pytest.approx(4_700_000)
    assert parse_dollar_amount("$3.2B") == pytest.approx(3_200_000_000)
    assert parse_dollar_amount("$1,000,000") == pytest.approx(1_000_000)
    assert parse_dollar_amount("$250K") == pytest.approx(250_000)


def test_parse_dollar_amount_raises_rather_than_silently_returning_zero() -> None:
    """A silent 0.0 on bad input would make `implied_acv_implausible` always
    report an implausible (near-zero) ACV, which looks like a working
    checker but is actually failing everything for the wrong reason."""
    with pytest.raises(ValueError):
        parse_dollar_amount("a few million dollars")


def test_implied_acv_implausible_accepts_a_plausible_business() -> None:
    # $4.7M / 340 customers ~= $13.8k ACV: ordinary for a B2B SaaS business.
    assert implied_acv_implausible("$4.7M", 340) is False


def test_implied_acv_implausible_rejects_the_positive_control() -> None:
    """Spec §5's exact example: a seed company with 2 customers and $40M
    ARR implies a $20M ACV, which is not a business."""
    assert implied_acv_implausible("$40M", 2) is True


def test_contains_placeholder_token_catches_the_observed_leak() -> None:
    """Positive control is the exact string a live run put into
    supporting_facts on 2026-08-04, which is candidate-facing copy."""
    leaked = contains_placeholder_token(
        "The feature X would increase onboarding completion by 3.1%."
    )
    assert leaked is not None
    assert contains_placeholder_token("We should ship Product A before Q3.") is not None
    assert contains_placeholder_token("Competitor B wins on price.") is not None


def test_contains_placeholder_token_does_not_fire_on_real_copy() -> None:
    """A check that flags ordinary sentences would be relaxed away, so the
    word boundary and the capital letter both have to matter. "Series A" is
    the trap: a real funding stage, not a placeholder."""
    assert contains_placeholder_token("Guest checkout lifts completion by 3.1%.") is None
    assert contains_placeholder_token("The company raised a Series A in 2021.") is None
    assert contains_placeholder_token("Feature parity with Northline is two quarters out.") is None
    assert contains_placeholder_token("") is None


def test_implied_acv_implausible_accepts_consumer_scale_arpu() -> None:
    """Regression, 2026-08-04: the blind $50 floor was a B2B ACV assumption
    and it failed the `apm_consumer` golden case twice on worlds that were
    right -- $12.3M over 400,000 users ($30.75 ARPU), then $12.5M over
    3,200,000 ($3.91). Spec §5 conditions plausibility on "stage and market";
    these pin the market half so the floor cannot quietly drift back up."""
    assert implied_acv_implausible("$12.3M", 400_000) is False
    assert implied_acv_implausible("$12.5M", 3_200_000) is False


def test_implied_acv_implausible_keeps_the_b2b_floor() -> None:
    """The consumer band must not weaken B2B, which is the whole reason this
    is conditioned on customer_count rather than lowered. 340 customers is
    below consumer scale, so $2.9k ARR over them ($8.53 each) stays a
    failure -- it would pass under a blanket $1 floor."""
    assert implied_acv_implausible("$2.9K", 340) is True


def test_implied_acv_implausible_still_rejects_cents_per_user() -> None:
    """Even at consumer scale the floor must catch what it exists for: an ARR
    in the millions implying a fraction of a dollar per user."""
    assert implied_acv_implausible("$12.3M", 40_000_000) is True


def test_implied_acv_implausible_rejects_zero_customers() -> None:
    """Division by a non-positive customer count is undefined, not merely
    out of range -- must not raise ZeroDivisionError up through a golden
    test and must not be silently treated as plausible."""
    assert implied_acv_implausible("$4.7M", 0) is True


# ==============================================================================
# Row: "Vacuity floor -- every string field non-empty and above a minimum
# length"
# Positive control (spec §5): a world of empty strings and empty lists.
# ==============================================================================


def test_blank_or_short_fields_accepts_a_substantive_world() -> None:
    fields = {
        "company.name": "Verdant Ledger",
        "situation.prompt": "Our enterprise tier is growing while our SMB tier churns.",
    }
    assert blank_or_short_fields(fields) == []


def test_blank_or_short_fields_rejects_empty_strings() -> None:
    fields = {"company.name": "", "situation.prompt": "   "}
    assert blank_or_short_fields(fields) == ["company.name", "situation.prompt"]


def test_blank_or_short_fields_rejects_a_short_string_below_the_floor() -> None:
    assert blank_or_short_fields({"situation.tension": "hard"}, min_len=10) == ["situation.tension"]


def test_full_assertion_battery_rejects_a_vacuous_case_world() -> None:
    """The direct lesson of story 1.3a, applied to this agent: a `CaseWorld`
    of empty strings and empty lists must FAIL the suite, not pass by having
    nothing to object to. Modeled as a plain dict, since no `CaseWorld`
    class exists yet (story 2.3) -- this test exercises the same checker
    calls `test_golden.py`'s universal assertions make, against a
    deliberately vacuous stand-in, and proves every one of them objects.
    """
    vacuous_world = {
        "company": {"name": "", "one_line": "", "stage": "seed", "employees": 0},
        "market": {"description": "", "size_usd": "", "growth_rate_pct": 0.0, "competitors": []},
        "metrics": {
            "arr_usd": "",
            "yoy_growth_pct": 0.0,
            "gross_margin_pct": 0.0,
            "monthly_churn_pct": 0.0,
            "customer_count": 0,
        },
        "situation": {
            "prompt": "",
            "tension": "",
            "options": [],
            "constraints": [],
            "leadership_belief": "",
        },
        "supporting_facts": [],
    }

    string_fields = {
        "company.name": vacuous_world["company"]["name"],
        "company.one_line": vacuous_world["company"]["one_line"],
        "market.description": vacuous_world["market"]["description"],
        "situation.prompt": vacuous_world["situation"]["prompt"],
        "situation.tension": vacuous_world["situation"]["tension"],
        "situation.leadership_belief": vacuous_world["situation"]["leadership_belief"],
    }
    empty = blank_or_short_fields(string_fields)
    assert set(empty) == set(string_fields), f"vacuity floor did not catch every blank field: {empty}"

    assert count_out_of_range(vacuous_world["supporting_facts"], 8, 15) is True
    assert count_out_of_range(vacuous_world["market"]["competitors"], 2, 4) is True
    assert count_out_of_range(vacuous_world["situation"]["options"], 2, 3) is True

    # An all-zero world also fails internal consistency, not just vacuity --
    # 0 employees at "seed" is inside the wide plausible range chosen above,
    # so this specifically checks the ACV path, where 0 customers is
    # unconditionally implausible regardless of the (also zero) ARR.
    assert implied_acv_implausible(
        vacuous_world["metrics"]["arr_usd"] or "$0", vacuous_world["metrics"]["customer_count"]
    ) is True


# ==============================================================================
# Vacuity guards on the case table itself
# ==============================================================================


def test_all_four_levels_represented_across_cases() -> None:
    levels = {c.assessed_level for c in CASES}
    assert levels == FOUR_LEVELS, (
        f"golden cases must span all four levels per spec §5 / PHASE-2-SPEC.md 2.1: "
        f"got {levels}"
    )


def test_every_case_fixture_file_exists_and_has_the_expected_shape() -> None:
    """Guards against a typo'd fixture filename, or a candidate_profile that
    has drifted from `CandidateProfile`'s seven fields, either of which
    would otherwise only surface as a confusing error deep inside a live,
    expensive test run."""
    expected_fields = {
        "years_pm_experience",
        "domains",
        "product_types",
        "company_contexts",
        "scope_evidence",
        "notable_outcomes",
        "people_leadership",
    }
    for case in CASES:
        profile = case.candidate_profile
        assert set(profile.keys()) == expected_fields, (
            f"{case.id}: candidate_profile fields drifted from CandidateProfile: "
            f"{set(profile.keys())}"
        )
        assert case.assessed_level in FOUR_LEVELS, f"{case.id}: {case.assessed_level!r}"


def test_seven_cases_defined() -> None:
    """Pins the count named in the brief -- a fixture silently dropped from
    `CASES` (but left on disk) would otherwise pass every other check here."""
    assert len(CASES) == 7, [c.id for c in CASES]
