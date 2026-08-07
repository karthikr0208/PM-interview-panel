"""Offline tests for the checkers in `assertions.py`. No network, no marker,
no import of `app.agents.planner` -- collects and runs under `pytest tests
-m "not live"` today, before that agent exists.

Precedent (CLAUDE.md / DEV-STATE, story 0.6, 1.3a, 1.5, 2.2): a denial
assertion is not trusted until it has been shown to FAIL against input it
should reject. Every checker below gets both directions -- accepts the
honest value, rejects the dishonest one named in AGENT-PLANNER-SPEC.md §5's
positive-control table -- plus a guard against story 1.3a's failure mode: a
checker that returns "nothing wrong" on an empty or missing input, which
lets an agent that produced NOTHING pass the check vacuously.

Three sections carry the brief's named traps specifically:
  - "NAMED TRAP 2" -- the vacuity floor on `grounded_in`, doubly emphasized
    because it is this suite's most important assertion.
  - "NAMED TRAP 3" -- the cross-world genericness control, built from
    hand-written plans since no agent exists yet to generate real ones.
  - "Positive control on case_architect's assertions" -- every hand-written
    fixture here must pass that suite's universal battery.
"""
from __future__ import annotations

import json

import pytest

from app.questions.shapes import (
    CATEGORIES,
    SHAPE_BANK,
    select_category,
    select_shape,
    select_shape_for_world,
    shapes_by_category,
)
from tests.golden.case_architect import assertions as ca_assertions
from tests.golden.planner.assertions import (
    RUBRIC_DIMENSIONS,
    blank_or_short_fields,
    contains_banned_register_name,
    contains_fake_round_number,
    count_out_of_range,
    decorative_statistic,
    empty_grounded_in,
    is_generic_question,
    is_recitation_shaped,
    matches_no_shape,
    missing_dimension_coverage,
    missing_grounding,
    no_dash_variants,
    probe_angle_violations,
    total_minutes_mismatch,
    world_haystack,
    world_specific_terms,
)
from tests.golden.planner.cases import CASES, FIXTURES_DIR, FOUR_LEVELS

# ==============================================================================
# Load the five hand-written case worlds once, for reuse across this file.
# ==============================================================================


def _load_world(fixture_name: str) -> dict:
    payload = json.loads((FIXTURES_DIR / f"{fixture_name}.json").read_text(encoding="utf-8"))
    return payload["case_world"]


APM_WORLD = _load_world("apm_consumer_world")
GPM_WORLD = _load_world("gpm_portfolio_world")
SPARSE_WORLD = _load_world("sparse_world")


# ==============================================================================
# Positive control on case_architect's assertions (brief requirement #6):
# every hand-written case world here MUST pass that suite's own universal
# battery. This is free, needs no LLM, and buys two things per the brief:
# proof these fixtures are realistic input, and a positive control on story
# 2.2's assertions themselves -- a world a human considers good should pass
# them, or one of the two suites is wrong.
# ==============================================================================


def _run_case_architect_universal_battery(world: dict) -> None:
    """Reproduces exactly the universal-assertion sequence
    `case_architect/test_golden.py::test_golden_case` runs against a live
    `CaseWorld`, against our raw fixture dicts instead. Safe to do offline:
    case_architect's own `assertions.py` docstring states its checkers take
    primitives, never the pydantic model, specifically so they can be
    exercised this way."""
    company = world["company"]
    market = world["market"]
    metrics = world["metrics"]
    situation = world["situation"]
    supporting_facts = world["supporting_facts"]

    string_fields = {
        "company.name": company["name"],
        "company.one_line": company["one_line"],
        "market.description": market["description"],
        "situation.prompt": situation["prompt"],
        "situation.tension": situation["tension"],
        "situation.leadership_belief": situation["leadership_belief"],
    }
    empty = ca_assertions.blank_or_short_fields(string_fields)
    assert not empty, f"vacuity floor: {empty}"

    assert supporting_facts, "supporting_facts is empty"
    assert not ca_assertions.count_out_of_range(supporting_facts, 8, 15), (
        f"supporting_facts has {len(supporting_facts)} entries, want 8-15"
    )
    assert not ca_assertions.count_out_of_range(market["competitors"], 2, 4), (
        f"competitors has {len(market['competitors'])}, want 2-4"
    )
    assert not ca_assertions.count_out_of_range(situation["options"], 2, 3), (
        f"options has {len(situation['options'])}, want 2-3"
    )

    percentages = {
        "market.growth_rate_pct": market["growth_rate_pct"],
        "metrics.yoy_growth_pct": metrics["yoy_growth_pct"],
        "metrics.gross_margin_pct": metrics["gross_margin_pct"],
        "metrics.monthly_churn_pct": metrics["monthly_churn_pct"],
    }
    dollar_amounts = {
        "market.size_usd": market["size_usd"],
        "metrics.arr_usd": metrics["arr_usd"],
    }
    round_violations = ca_assertions.banned_round_numbers(percentages, dollar_amounts)
    assert not round_violations, f"fake-round number(s): {round_violations}"
    assert not ca_assertions.organic_ratio_below_floor(percentages), (
        f"too many round-looking percentages across the world: {percentages}"
    )

    names_and_text = (
        [company["name"]]
        + [c["name"] for c in market["competitors"]]
        + list(supporting_facts)
        + [situation["leadership_belief"]]
    )
    leaked = ca_assertions.contains_banned_register_name(*names_and_text)
    assert leaked is None, f"banned-register name leaked: {leaked!r}"

    assert not ca_assertions.stage_employee_mismatch(company["stage"], company["employees"]), (
        f"{company['employees']} employees implausible for stage {company['stage']!r}"
    )
    assert not ca_assertions.implied_acv_implausible(
        metrics["arr_usd"], metrics["customer_count"]
    ), f"implied ACV implausible: arr={metrics['arr_usd']} customers={metrics['customer_count']}"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
def test_fixture_case_world_passes_case_architect_universal_assertions(case) -> None:
    """The brief's requirement #6, and spec §5's requirement 2: every
    hand-written world here must pass case_architect's own universal
    battery, proving these are realistic Case Architect *output* and giving
    story 2.2's assertions a positive control from an independent author."""
    _run_case_architect_universal_battery(case.case_world)


def test_all_five_case_world_fixtures_exist_and_have_the_expected_top_level_shape() -> None:
    """Guards against a typo'd fixture filename or a case_world missing a
    required top-level key, either of which would otherwise only surface as
    a confusing error deep inside a live, expensive test run."""
    expected_keys = {"company", "market", "metrics", "situation", "supporting_facts"}
    for case in CASES:
        assert set(case.case_world.keys()) == expected_keys, case.id
        assert case.assessed_level in FOUR_LEVELS, f"{case.id}: {case.assessed_level!r}"


def test_five_cases_defined() -> None:
    """Pins the count named in the brief -- a fixture silently dropped from
    `CASES` (but left on disk) would otherwise pass every other check here."""
    assert len(CASES) == 5, [c.id for c in CASES]


# ==============================================================================
# NAMED TRAP 2 -- the vacuity floor on `grounded_in`, doubly emphasized.
# Story 1.3a: `missing_verbatim_quotes([])` returned `[]`, so an agent that
# quoted NOTHING passed the suite's most important assertion on all eight
# cases. The Planner's equivalent is worse per the brief: `grounded_in`
# empty passes the membership check vacuously, since there is nothing to
# look up. Both directions demonstrated below, plus the floor that must
# catch it BEFORE the membership check runs.
# ==============================================================================


def test_missing_grounding_is_vacuously_empty_on_an_empty_grounded_in_list() -> None:
    """Demonstrates the trap exists, so the floor below is not decorative:
    an empty `grounded_in` list has nothing to fail to find, and
    `missing_grounding` correctly (and dangerously) reports no problem."""
    assert missing_grounding([], APM_WORLD) == []


def test_empty_grounded_in_catches_what_missing_grounding_cannot() -> None:
    """The floor that must run BEFORE `missing_grounding`, per spec §5/§7.
    A question with an empty `grounded_in` list is flagged here even though
    it would sail through the membership check above."""
    questions = [
        {"idx": 1, "grounded_in": ["Ferngrove Media"]},
        {"idx": 2, "grounded_in": []},
        {"idx": 3, "grounded_in": None},
    ]
    assert empty_grounded_in(questions) == [2, 3]


def test_missing_grounding_accepts_an_entry_that_exists_in_the_world() -> None:
    """Positive control, accept direction: a real entity from the world."""
    assert missing_grounding(["Ferngrove Media"], APM_WORLD) == []
    assert missing_grounding(["Whisk & Co"], APM_WORLD) == []
    # A fact string, quoted verbatim, also grounds successfully.
    assert missing_grounding(
        ["Day-2 return rate for new signups is 11.3%, versus 19.0% for users "
         "who follow at least three creators in their first session."],
        APM_WORLD,
    ) == []


def test_missing_grounding_rejects_the_positive_control() -> None:
    """The brief's exact positive control (also spec §2's own example): a
    question grounded in "Northwind Logistics" when no such entity exists
    in the world."""
    result = missing_grounding(["Northwind Logistics"], APM_WORLD)
    assert result == ["Northwind Logistics"]


def test_missing_grounding_rejects_a_fabricated_entry_alongside_a_real_one() -> None:
    """A grounded_in list with one real entry and one fabricated entry must
    report only the fabricated one -- proves the check is per-entry, not
    all-or-nothing."""
    result = missing_grounding(["Ferngrove Media", "Northwind Logistics"], APM_WORLD)
    assert result == ["Northwind Logistics"]


def test_world_haystack_includes_nested_competitor_and_metric_values() -> None:
    """Guards the flattening walk itself: a grounded_in entry that only
    exists nested inside `market.competitors` or as a numeric `metrics`
    value must still be findable, not just top-level string fields."""
    haystack = world_haystack(APM_WORLD)
    assert "Skillet Social" in haystack  # nested competitor name
    assert "41.2" in haystack  # metrics.yoy_growth_pct, a float
    assert "41000" in haystack  # metrics.customer_count, an int


def test_a_question_shaped_object_of_empty_strings_and_empty_lists_fails_the_full_battery() -> None:
    """Direct analogue of case_architect's identical test: a
    `QuestionPlan`-shaped object of empty strings and empty lists must FAIL
    the suite, not pass by having nothing to object to. Modeled as plain
    dicts, since no `QuestionPlan` class exists yet (story 2.6)."""
    vacuous_questions = [
        {
            "idx": 1,
            "question": "",
            "intent": "",
            "primary_dimension": "decision_quality",
            "probe_angles": [],
            "grounded_in": [],
            "minutes": 0,
        }
    ]

    assert empty_grounded_in(vacuous_questions) == [1]

    string_fields = {"question[1].question": vacuous_questions[0]["question"]}
    assert blank_or_short_fields(string_fields, min_len=15) == ["question[1].question"]

    assert count_out_of_range(vacuous_questions, 5, 7) is True  # only 1 question

    assert probe_angle_violations(vacuous_questions) == [1]  # 0 probe_angles

    missing_dims = missing_dimension_coverage(vacuous_questions)
    assert missing_dims == RUBRIC_DIMENSIONS - {"decision_quality"}

    assert total_minutes_mismatch(30, vacuous_questions) is True  # 30 != sum([0])


# ==============================================================================
# NAMED TRAP 3 -- the cross-world genericness control, spec §5's "single
# most valuable test in this suite". No agent exists to generate real
# plans, so this is built entirely from hand-written plans.
# ==============================================================================

# A good-faith plan hand-written FOR apm_consumer_world: every question
# names a proper noun or figure from that world, and grounded_in points at
# real entries in it. Deliberately covers all five RUBRIC_DIMENSIONS and
# stays within the 5-7 question / <=45 minute bounds, so this plan is also
# reused below to demonstrate the universal battery accepting a genuinely
# good plan (not just rejecting bad ones).
GOOD_PLAN_FOR_APM_WORLD = [
    {
        "idx": 1,
        "question": (
            "Ferngrove Media's day-2 return rate for new signups is 11.3%, well below "
            "the 19.0% rate for users who follow three creators in their first session. "
            "How would you decide whether to push new users toward following creators "
            "immediately, given the constraints the company is under this quarter?"
        ),
        "intent": "Tests whether the candidate reasons from the retention gap to a concrete decision.",
        "primary_dimension": "decision_quality",
        "probe_angles": [
            "What would change your mind if the forced-follow test looked like the prior one?",
            "How would you sequence this against the Whisk & Co launch deadline?",
        ],
        "grounded_in": ["Ferngrove Media", "11.3%", "19.0%"],
        "minutes": 8,
    },
    {
        "idx": 2,
        "question": (
            "Ferngrove's subscription business runs at 76.5% gross margin. Walk me "
            "through how the retention fix you proposed would move the underlying "
            "revenue mechanics, not just the day-2 metric."
        ),
        "intent": "Tests whether revenue mechanics are load-bearing in the recommendation.",
        "primary_dimension": "business_model_fluency",
        "probe_angles": [
            "Where does the $18.3M in ARR actually come from at the cohort level?",
            "What happens to gross margin if churn among the 41,000 subscribers rises?",
        ],
        "grounded_in": ["76.5%", "$18.3M"],
        "minutes": 7,
    },
    {
        "idx": 3,
        "question": (
            "Skillet Social has roughly ten times Ferngrove's daily active users, and "
            "Tablescape is pulling top creators away with better payouts. How does the "
            "competitive picture change your recommendation, if at all?"
        ),
        "intent": "Tests whether the candidate reads the competitive structure accurately.",
        "primary_dimension": "market_accuracy",
        "probe_angles": [
            "Why doesn't Skillet Social's scale make this moot?",
            "What would Tablescape do in response to your plan?",
        ],
        "grounded_in": ["Skillet Social", "Tablescape"],
        "minutes": 7,
    },
    {
        "idx": 4,
        "question": (
            "Structure your recommendation for Ferngrove Media's onboarding redesign "
            "as if you were presenting it to the exec team in five minutes."
        ),
        "intent": "Tests whether the answer is signposted and adapts structure to the prompt.",
        "primary_dimension": "structural_clarity",
        "probe_angles": [
            "What's the one thing you'd cut if you only had two minutes?",
            "How would you signal confidence versus uncertainty in that structure?",
        ],
        "grounded_in": ["Ferngrove Media"],
        "minutes": 6,
    },
    {
        "idx": 5,
        "question": (
            "Ferngrove Media's exec team believes this is a content-discovery problem, "
            "not a social-graph problem. Do you agree, and what is your thesis?"
        ),
        "intent": "Tests whether the candidate has a defensible point of view and can sharpen it under pushback.",
        "primary_dimension": "point_of_view",
        "probe_angles": [
            "What evidence would change your thesis?",
            "If leadership pushes back, how do you hold or revise your position?",
        ],
        "grounded_in": [
            "The exec team believes the drop in day-2 return is a content-discovery "
            "problem, not a social-graph problem, and wants ranking improvements "
            "prioritized."
        ],
        "minutes": 6,
    },
]

GOOD_PLAN_TOTAL_MINUTES = sum(q["minutes"] for q in GOOD_PLAN_FOR_APM_WORLD)  # 34


def test_good_plan_passes_grounding_against_its_own_world() -> None:
    for q in GOOD_PLAN_FOR_APM_WORLD:
        assert missing_grounding(q["grounded_in"], APM_WORLD) == [], q["idx"]


def test_good_plan_is_not_generic_against_its_own_world() -> None:
    for q in GOOD_PLAN_FOR_APM_WORLD:
        assert not is_generic_question(q["question"], APM_WORLD), q["idx"]


def test_good_plan_covers_all_five_rubric_dimensions() -> None:
    assert missing_dimension_coverage(GOOD_PLAN_FOR_APM_WORLD) == set()


def test_good_plan_passes_structural_bounds() -> None:
    assert count_out_of_range(GOOD_PLAN_FOR_APM_WORLD, 5, 7) is False
    assert probe_angle_violations(GOOD_PLAN_FOR_APM_WORLD) == []
    assert total_minutes_mismatch(GOOD_PLAN_TOTAL_MINUTES, GOOD_PLAN_FOR_APM_WORLD) is False
    assert GOOD_PLAN_TOTAL_MINUTES <= 45


def test_good_plan_has_no_dash_or_banned_content() -> None:
    for q in GOOD_PLAN_FOR_APM_WORLD:
        assert no_dash_variants(q["question"]), q["idx"]
        assert contains_fake_round_number(q["question"]) is None, q["idx"]
        assert contains_banned_register_name(q["question"]) is None, q["idx"]


def test_good_plan_FAILS_grounding_against_a_different_world() -> None:
    """NAMED TRAP 3, the core of it. spec §5: "the cross-world control ...
    is the single most valuable test in this suite." A plan hand-written
    for apm_consumer_world references entities (Ferngrove Media, Skillet
    Social, Tablescape, the exec-team belief quote) that do not exist in
    gpm_portfolio_world. Checked against the wrong world, grounding MUST
    fail -- a plan that passes against a world it was not written for is
    generic by definition, per the spec's own framing.
    """
    failures = 0
    for q in GOOD_PLAN_FOR_APM_WORLD:
        missing = missing_grounding(q["grounded_in"], GPM_WORLD)
        if missing:
            failures += 1
    assert failures == len(GOOD_PLAN_FOR_APM_WORLD), (
        f"expected every question's grounding to fail against the wrong world, "
        f"but only {failures}/{len(GOOD_PLAN_FOR_APM_WORLD)} did -- a plan that "
        f"partially grounds against an unrelated world is still too generic"
    )


def test_good_plan_questions_ARE_generic_when_read_as_about_a_different_world() -> None:
    """Complements the grounding failure above with the genericness check:
    none of the world-specific terms these questions cite (Ferngrove,
    Skillet Social, 76.5%, ...) appear anywhere in gpm_portfolio_world's own
    term list, so from that world's perspective these questions name
    nothing recognisable either."""
    gpm_terms = set(world_specific_terms(GPM_WORLD))
    apm_terms_cited = set()
    for q in GOOD_PLAN_FOR_APM_WORLD:
        apm_terms_cited.update(q["grounded_in"])
    assert gpm_terms.isdisjoint(apm_terms_cited), (
        f"unexpected overlap between the two worlds' terms: "
        f"{gpm_terms & apm_terms_cited}"
    )


# A deliberately generic plan: every question would fit any product case
# unchanged. grounded_in is intentionally left NON-empty (pointing at real
# apm_consumer_world facts) so this plan does NOT trip the vacuity floor or
# the membership check -- isolating exactly the failure mode the
# genericness assertion exists to catch, independent of grounding.
GENERIC_PLAN_FOR_APM_WORLD = [
    {
        "idx": 1,
        "question": "What would you do next?",
        "intent": "n/a",
        "primary_dimension": "decision_quality",
        "probe_angles": ["Why?", "What else?"],
        "grounded_in": ["Ferngrove Media"],
        "minutes": 6,
    },
    {
        "idx": 2,
        "question": "How would you prioritize between these options?",
        "intent": "n/a",
        "primary_dimension": "structural_clarity",
        "probe_angles": ["What's your framework?", "What would you cut first?"],
        "grounded_in": ["Whisk & Co"],
        "minutes": 6,
    },
    {
        "idx": 3,
        "question": "Walk me through your thinking on this.",
        "intent": "n/a",
        "primary_dimension": "point_of_view",
        "probe_angles": ["Why that order?", "What's your biggest risk?"],
        "grounded_in": ["Tablescape"],
        "minutes": 6,
    },
]


def test_generic_plan_grounds_successfully_but_reads_as_generic() -> None:
    """Proves the genericness check is doing real work and is not just a
    restatement of the grounding check: this plan's grounded_in entries are
    all real (grounding passes), yet every question's TEXT names nothing
    from the world (genericness must fail). If genericness only ever failed
    alongside grounding, it would be redundant."""
    for q in GENERIC_PLAN_FOR_APM_WORLD:
        assert missing_grounding(q["grounded_in"], APM_WORLD) == [], q["idx"]
        assert is_generic_question(q["question"], APM_WORLD), (
            f"question {q['idx']} should read as generic: {q['question']!r}"
        )


# ==============================================================================
# Assertion-by-assertion accept/reject pairs, spec §5's table.
# ==============================================================================

# --- Row: grounding (covered above under NAMED TRAP 2) -----------------------

# --- Row: all five rubric dimensions covered ----------------------------------


def test_missing_dimension_coverage_accepts_full_coverage() -> None:
    assert missing_dimension_coverage(GOOD_PLAN_FOR_APM_WORLD) == set()


def test_missing_dimension_coverage_rejects_the_positive_control() -> None:
    """Spec §5's positive control: a plan whose questions are all
    decision_quality."""
    all_decision_quality = [{"idx": i, "primary_dimension": "decision_quality"} for i in range(5)]
    missing = missing_dimension_coverage(all_decision_quality)
    assert missing == RUBRIC_DIMENSIONS - {"decision_quality"}
    assert len(missing) == 4


# --- Row: 5-7 questions --------------------------------------------------------


def test_count_out_of_range_accepts_five_to_seven_questions() -> None:
    assert count_out_of_range([{}] * 5, 5, 7) is False
    assert count_out_of_range([{}] * 7, 5, 7) is False


def test_count_out_of_range_rejects_the_positive_control() -> None:
    """Spec §5's positive control: a plan of 1 question, and one of 20."""
    assert count_out_of_range([{}] * 1, 5, 7) is True
    assert count_out_of_range([{}] * 20, 5, 7) is True


# --- Row: 2-3 probe_angles per question ----------------------------------------


def test_probe_angle_violations_accepts_two_or_three() -> None:
    questions = [
        {"idx": 1, "probe_angles": ["a", "b"]},
        {"idx": 2, "probe_angles": ["a", "b", "c"]},
    ]
    assert probe_angle_violations(questions) == []


def test_probe_angle_violations_rejects_the_positive_control() -> None:
    """Spec §5's positive control: a question with none."""
    questions = [{"idx": 1, "probe_angles": []}]
    assert probe_angle_violations(questions) == [1]


def test_probe_angle_violations_rejects_too_many_as_well() -> None:
    """The row says "2-3", both boundaries -- pins the upper bound too, not
    just the named zero-angle control."""
    questions = [{"idx": 1, "probe_angles": ["a", "b", "c", "d"]}]
    assert probe_angle_violations(questions) == [1]


# --- Row: total_minutes <= 45 and matches the sum of `minutes` ---------------


def test_total_minutes_mismatch_accepts_a_consistent_plan_under_45() -> None:
    questions = [{"minutes": 10}, {"minutes": 15}, {"minutes": 10}]
    assert total_minutes_mismatch(35, questions) is False


def test_total_minutes_mismatch_rejects_the_positive_control() -> None:
    """Spec §5's positive control: a plan claiming 30 whose questions sum
    to 70."""
    questions = [{"minutes": 35}, {"minutes": 35}]
    assert total_minutes_mismatch(30, questions) is True


def test_total_minutes_mismatch_rejects_a_consistent_but_over_45_plan() -> None:
    """Consistent (matches the sum) is not sufficient on its own -- the
    45-minute interview-length ceiling (PRD §1) must independently reject a
    plan that is internally consistent but simply too long."""
    questions = [{"minutes": 25}, {"minutes": 25}]
    assert total_minutes_mismatch(50, questions) is True


# --- Row: no em-dashes in any `question` string --------------------------------


def test_no_dash_variants_accepts_plain_punctuation() -> None:
    assert no_dash_variants("What would you do, and why - be specific.") is True


def test_no_dash_variants_rejects_the_positive_control() -> None:
    """Spec §5's positive control: a question containing one."""
    assert no_dash_variants("What would you do—and why?") is False
    assert no_dash_variants("What would you do–next?") is False


def test_no_dash_variants_rejects_the_other_two_aside_range_dashes() -> None:
    """Widened 2026-08-06: `_DASH_VARIANTS` grew from {em, en} to all four
    aside/range dashes. Figure dash and horizontal bar are the two the
    original two-character set was blind to."""
    assert no_dash_variants("What would you do‒and why?") is False
    assert no_dash_variants("What would you do―next?") is False


def test_no_dash_variants_accepts_hyphen_like_characters() -> None:
    """Deliberately NOT widened to the three hyphen-like characters (hyphen,
    non-breaking hyphen, minus sign): those normalise to an ASCII hyphen at
    the frontend render boundary (`stripDashes`), so flagging them here
    would fail a golden case over text that reaches the candidate
    correctly. See this module's `_DASH_VARIANTS` comment."""
    assert no_dash_variants("state‐of‐the‐art") is True
    assert no_dash_variants("well‑known") is True
    assert no_dash_variants("the delta was −5 points") is True


# --- Row: no fake-round numbers, no banned-register names ----------------------


def test_contains_fake_round_number_accepts_an_organic_figure() -> None:
    assert contains_fake_round_number("Given that 11.3% of users return on day 2...") is None
    assert contains_fake_round_number("With a 20% gross margin...") is None


def test_contains_fake_round_number_rejects_the_positive_control() -> None:
    """Spec §5's positive control: a question citing "50% of customers"."""
    assert contains_fake_round_number("Roughly 50% of customers churn...") == "50%"


def test_contains_banned_register_name_accepts_an_organic_name() -> None:
    assert contains_banned_register_name("How would Ferngrove Media respond?") is None


def test_contains_banned_register_name_rejects_a_banned_token() -> None:
    assert contains_banned_register_name("How would Acme respond to this?") == "acme"


# --- Row: genericness (also covered under NAMED TRAP 3) -----------------------


def test_is_generic_question_accepts_a_world_specific_question() -> None:
    assert (
        is_generic_question("How should Ferngrove Media respond to Skillet Social?", APM_WORLD)
        is False
    )


def test_is_generic_question_accepts_the_company_short_form() -> None:
    """Regression, 2026-08-04. `deep` produced "what are the key strengths
    and weaknesses of Ferngrove's business model?" against a world whose
    company is "Ferngrove Media", and the full-string check called it
    generic. A question naming the company in the possessive short form is
    unambiguously about this world -- that was the check under-measuring."""
    assert (
        is_generic_question("What are the weaknesses of Ferngrove's business model?", APM_WORLD)
        is False
    )


def test_world_specific_terms_excludes_short_first_words() -> None:
    """The short-form acceptance must not admit common prose. A first word
    under four characters (or non-alphabetic) is excluded, or a company
    called "The Ledger" would make every question containing "The" pass."""
    world = json.loads(json.dumps(APM_WORLD))
    world["company"]["name"] = "The Ledger"
    terms = world_specific_terms(world)
    assert "The" not in terms
    assert "The Ledger" in terms


def test_is_generic_question_rejects_the_positive_control() -> None:
    """Spec §5's positive control, in this suite's own words: a question
    that would fit any case world."""
    assert is_generic_question("What would you do?", APM_WORLD) is True
    assert is_generic_question("How would you prioritize?", APM_WORLD) is True


# --- Row: vacuity floor -- non-empty strings, non-empty lists -----------------
# (also exercised in full by test_a_question_shaped_object_..._fails_the_full_battery)


def test_blank_or_short_fields_accepts_a_substantive_question() -> None:
    fields = {"question[1].question": GOOD_PLAN_FOR_APM_WORLD[0]["question"]}
    assert blank_or_short_fields(fields, min_len=15) == []


def test_blank_or_short_fields_rejects_an_empty_question() -> None:
    fields = {"question[1].question": ""}
    assert blank_or_short_fields(fields, min_len=15) == ["question[1].question"]


# ==============================================================================
# Sanity check on the sparse-world fixture specifically (spec §5 fixture 5):
# a thin world must still let a hand-written, grounded, non-generic plan
# exist -- proves the fixture itself isn't so thin that grounding is
# impossible, independent of any future agent's behavior on it.
# ==============================================================================


def test_a_grounded_non_generic_question_can_be_written_against_the_sparse_world() -> None:
    question = (
        "Palewell Software's time-tracking export has broken 4 times this quarter, "
        "and the founder fixes it personally each time. Would you hire the company's "
        "first support person, or build a self-serve repair tool instead?"
    )
    grounded_in = [
        "The time-tracking export has broken 4 times this quarter, each requiring "
        "the founder to fix it manually.",
        "Palewell Software",
    ]
    assert missing_grounding(grounded_in, SPARSE_WORLD) == []
    assert is_generic_question(question, SPARSE_WORLD) is False


# ==============================================================================
# Story 3.5.2 -- decorative_statistic, matches_no_shape, is_recitation_shaped.
#
# The honest corpus: DEV-STATE.md § Decisions 2026-08-05's three questions,
# recorded verbatim (do not paraphrase these -- they are quoted, not
# summarized, per the brief). This is the product's own real output the day
# before this story, kept as the positive/negative control for all three new
# checks rather than a hand-picked example.
# ==============================================================================

Q1 = (
    "At Nimbus Capital, how does the AI Risk Suite's current module mix support the "
    "company's revenue model given the $12.3B market size and the 31.4% ARR growth "
    "last year?"
)

Q2 = (
    "Considering Nimbus Capital's position in a market worth $12.3B, how does the "
    "competitive landscape with LendWise Analytics influence your go-to-market "
    "strategy for the AI Risk Suite?"
)

Q3 = (
    "Given Nimbus Capital's constraints, would you prioritize building the "
    "BehavioralRisk AI module, improve existing modules, or target SME lending, "
    "and why?"
)


# --- decorative_statistic: the brief's required table -------------------------


def test_decorative_statistic_fires_on_q1_the_market_size_and_growth_clause() -> None:
    """Q1 stapled both a market-size figure AND a growth-rate figure to the
    question. Either firing is sufficient to flag the question, so this
    only pins that SOMETHING fires and that the matched fragment carries the
    actual figure -- not which of the two clauses is returned first."""
    result = decorative_statistic(Q1)
    assert result is not None, "Q1 has a decorative statistic and must be flagged"
    assert "$12.3B" in result or "31.4" in result, (
        f"matched fragment should carry the offending figure, got {result!r}"
    )


def test_decorative_statistic_fires_on_q2_the_market_worth_clause() -> None:
    result = decorative_statistic(Q2)
    assert result is not None, "Q2 has a decorative statistic and must be flagged"
    assert "$12.3B" in result, f"matched fragment should carry the figure, got {result!r}"


def test_decorative_statistic_does_not_fire_on_q3_which_has_no_statistic() -> None:
    """Q3 is the shape to generalize from (spec's own framing): a forced
    trade-off with no market-size or growth-rate figure anywhere in it."""
    assert decorative_statistic(Q3) is None


def test_decorative_statistic_generalizes_beyond_the_three_named_strings() -> None:
    """The brief's explicit worry: a check that only matches Q1/Q2's exact
    numbers would not be measuring anything. Same shape of clause, a
    DIFFERENT company and DIFFERENT figures -- must still fire, proving the
    match is structural (dollar-figure-near-'market', percent-figure-near-
    'growth'), not a hard-coded string comparison."""
    different_company_same_shape = (
        "How would you improve retention at Solstice Health, given the $47.9M "
        "market size and the 8.6% quarterly growth?"
    )
    result = decorative_statistic(different_company_same_shape)
    assert result is not None, "must generalize to a different company/figures"
    assert "$47.9M" in result

    market_worth_variant = (
        "Considering Solstice Health's position in a market worth $47.9M, how "
        "would you prioritize the next release?"
    )
    result2 = decorative_statistic(market_worth_variant)
    assert result2 is not None
    assert "$47.9M" in result2


def test_decorative_statistic_fires_on_a_customer_count_style_figure() -> None:
    """Regression, independent re-verification 2026-08-06: the first version
    only recognized '$X market size' and 'X% growth', and was blind to every
    other figure the curated worlds actually carry -- `customer_count` here.
    A bare number followed by a scale word ('97.2 million') must fire."""
    result = decorative_statistic(
        "Given Reddit's 97.2 million daily actives, how would you prioritize "
        "the next quarter's roadmap?"
    )
    assert result is not None
    assert "97.2 million" in result


def test_decorative_statistic_fires_on_a_comma_grouped_integer() -> None:
    """A comma-grouped integer ('8,400') must not be mistaken for a clause
    boundary -- the internal comma is part of the figure, not the
    terminator, and the check must still find the figure and fire."""
    result = decorative_statistic(
        "With 8,400 enterprise customers, how would you expand upmarket?"
    )
    assert result is not None
    assert "8,400" in result


def test_decorative_statistic_fires_on_an_arr_dollar_figure() -> None:
    """Regression: `metrics.arr_usd`-shaped figure, a dollar amount with no
    'market' in sight -- must still fire on the currency pattern alone."""
    result = decorative_statistic(
        "Given Cursor's $247M ARR, how would you defend against a fast follower?"
    )
    assert result is not None
    assert "$247M" in result


def test_decorative_statistic_fires_on_a_churn_percent_figure() -> None:
    """Regression: `metrics.monthly_churn_pct`-shaped figure -- a percent
    with no 'growth' in sight -- must still fire on the percent pattern
    alone."""
    result = decorative_statistic(
        "With monthly churn at 3.7%, how would you redesign onboarding?"
    )
    assert result is not None
    assert "3.7%" in result


def test_decorative_statistic_deletion_test_rejects_a_clause_that_swallows_the_question() -> None:
    """The deletion test's own floor: if removing the matched clause would
    not leave a real standalone question behind, the match must not be
    returned. Constructed adversarially -- a 'question' that is nothing but
    the statistic clause -- to prove `_clause_deletion_leaves_a_standalone_
    question` is load-bearing, not decorative itself."""
    assert decorative_statistic("Given the $12.3B market size?") is None


def test_decorative_statistic_vacuity_floor_empty_question_returns_none() -> None:
    """An empty question has no statistic to find, so `None` here is
    CORRECT, not a silent pass on a bad question -- this is a denial check,
    not a membership check, so the vacuity risk is different from
    `missing_grounding`'s (see the function's own docstring). The floor that
    actually catches an empty question is `blank_or_short_fields`, exercised
    together with this one below so the pairing is not just asserted in
    prose."""
    assert decorative_statistic("") is None
    assert decorative_statistic(None) is None  # defensive: must not raise
    # Paired floor: an empty question is caught by the EXISTING vacuity
    # check, so a suite that runs both never lets a blank question through
    # by relying on `decorative_statistic` alone.
    assert blank_or_short_fields({"question": ""}, min_len=15) == ["question"]


# --- is_recitation_shaped: the brief's required table --------------------------


def test_is_recitation_shaped_fires_on_q1_the_how_does_x_support_y_given_z_frame() -> None:
    assert is_recitation_shaped(Q1) is True


def test_is_recitation_shaped_does_not_fire_on_q2() -> None:
    """Q2 has an explanatory frame ('how does') but also turns to the
    candidate directly -- 'your go-to-market strategy' -- so it clears on
    the second-person condition. Proves this check is independent of
    `decorative_statistic`, not a restatement of it (Q2 also fires that
    check, for an unrelated reason)."""
    assert is_recitation_shaped(Q2) is False


def test_is_recitation_shaped_does_not_fire_on_q3() -> None:
    """Q3 has no explanatory frame at all ('would you prioritize' is a
    decision verb, not 'how does'/'what role does'/etc), so it never even
    reaches the second-person or decision-verb checks."""
    assert is_recitation_shaped(Q3) is False


# --- is_recitation_shaped: regression, independent re-verification 2026-08-06 --
#
# The first version matched the literal string "how does ... support ...
# given" and fired on Q1 alone. These six cases (from the coordinator's own
# re-verification run) are the proof the property-based rule generalizes:
# same explanatory-frame-with-no-decision-and-no-second-person shape,
# different verbs and different frames, all correctly recognized.


def test_is_recitation_shaped_flips_true_with_a_different_verb_drive() -> None:
    """Named regression: same frame as Q1, verb swapped from 'support' to
    'drive'. The old literal match could never fire on this; this is the
    exact false-pass the coordinator caught."""
    assert is_recitation_shaped(
        "At Nimbus Capital, how does the current ad mix drive the revenue "
        "model given the $12.3B market size and the 31.4% ARR growth last "
        "year?"
    ) is True


def test_is_recitation_shaped_flips_true_with_a_different_verb_contribute() -> None:
    """Named regression: verb swapped to 'contribute', different company."""
    assert is_recitation_shaped(
        "How does Duolingo's streak feature contribute to retention given "
        "the cohort data from last quarter?"
    ) is True


def test_is_recitation_shaped_fires_on_the_same_frame_with_no_given_clause() -> None:
    """The frame alone -- no trailing 'given Z' clause at all -- is still
    recitation-shaped: it only asks how one fact of the world relates to
    another, with no second-person turn and no decision verb."""
    assert is_recitation_shaped(
        "How does Figma's plugin ecosystem support its enterprise motion?"
    ) is True


def test_is_recitation_shaped_fires_on_a_walk_me_through_how_frame() -> None:
    assert is_recitation_shaped(
        "Walk me through how YouTube Premium is positioned relative to Spotify."
    ) is True


def test_is_recitation_shaped_fires_on_a_what_role_does_frame() -> None:
    assert is_recitation_shaped(
        "What role does Cursor's free tier play in its conversion funnel?"
    ) is True


def test_is_recitation_shaped_generalizes_to_a_differently_worded_recitation() -> None:
    """Same frame, different company/nouns -- must still fire."""
    assert is_recitation_shaped(
        "How does Solstice Health's current pricing structure support its "
        "retention goals given the churn data from last quarter?"
    ) is True


def test_is_recitation_shaped_accepts_a_forced_tradeoff_question() -> None:
    """Q3's own shape (spec's "generalize from this") must never be flagged
    -- a forced trade-off between different kinds of bet is exactly what
    this check exists to let through."""
    assert is_recitation_shaped(
        "Should Solstice Health build a new triage module, harden the "
        "existing one, or expand into SMB clinics, and why?"
    ) is False


def test_is_recitation_shaped_vacuity_floor() -> None:
    """Empty input must not vacuously report True (that would flag every
    blank question as 'recitation-shaped', which is meaningless), and must
    not crash on `None`."""
    assert is_recitation_shaped("") is False
    assert is_recitation_shaped(None) is False


# --- matches_no_shape -----------------------------------------------------------

# One shared fill-values dict, reused by every test below that needs a
# filled shape -- keeps the values in ONE place rather than a copy per
# test, per the coordinator's explicit instruction. Every slot name that
# appears anywhere in SHAPE_BANK must have an entry here, or `.format()`
# raises `KeyError` for whichever shape needs the missing one -- which is
# the desired failure mode (loud, at the offending shape) if the bank ever
# grows a new slot name this dict does not cover.
_SHAPE_FILL_VALUES: dict[str, str] = {
    "company": "Duolingo",
    "adjacent_market": "gaming",
    "capability": "AI conversation practice",
    "product": "the Super subscription",
    "new_segment": "small businesses",
    "competitor": "Babbel",
    "current_model": "a flat subscription",
    "alternative_model": "usage-based pricing",
    "metric": "weekly active users",
    "period": "two quarters",
    "conversion_step": "signup-to-first-lesson",
    "n": "3",
}


def _fill(shape) -> str:
    return shape.template.format(**{slot: _SHAPE_FILL_VALUES[slot] for slot in shape.slots})


def test_matches_no_shape_accepts_a_question_built_from_the_bank_itself() -> None:
    """Positive control: every bank shape (thirteen as of 2026-08-06's added
    Nx-growth shape), filled with plausible slot values, must be recognized
    as a conforming shape (i.e. `matches_no_shape` returns False). If the
    bank's own output failed this check, the check would be measuring
    nothing."""
    for shape in SHAPE_BANK:
        filled = _fill(shape)
        assert matches_no_shape(filled) is False, (
            f"a question built directly from the bank must conform: {filled!r}"
        )


def test_matches_no_shape_accepts_karthiks_literal_10x_duolingo_example() -> None:
    """Named acceptance: PHASE-3.5-SPEC.md quotes 'how would you 10x
    Duolingo' as one of Karthik's own examples of the target register. The
    original 12-shape bank had no shape it could fill exactly to reproduce
    this phrasing (`{n}x` with no separate 'grow ... at ... by' framing);
    the added growth shape `How would you {n}x {company}?` closes that gap."""
    assert matches_no_shape("How would you 10x Duolingo?") is False


def test_matches_no_shape_rejects_a_freeform_question_that_matches_no_template() -> None:
    assert matches_no_shape("Tell me about a time you disagreed with a stakeholder.") is True


def test_matches_no_shape_vacuity_floor_empty_question_conforms_to_nothing() -> None:
    """An empty string must be True (conforms to no shape), never
    vacuously False -- a blank question is not a filled shape."""
    assert matches_no_shape("") is True
    assert matches_no_shape(None) is True
    assert matches_no_shape("   ") is True


def test_select_shape_is_deterministic() -> None:
    """CLAUDE.md § Style / the brief's Part 1 requirement: no LLM, and the
    same (level, category) must always return the same shape."""
    first = select_shape("PM", "growth")
    second = select_shape("PM", "growth")
    assert first == second
    assert first in SHAPE_BANK
    assert first.category == "growth"


def test_select_shape_covers_all_four_categories_across_the_four_levels() -> None:
    """Sanity check on the bank's shape: every category is selectable for
    every known level without raising."""
    for level in FOUR_LEVELS:
        for category in {s.category for s in SHAPE_BANK}:
            shape = select_shape(level, category)
            assert shape.category == category


# ==============================================================================
# Story 3.5.3 -- select_category / select_shape_for_world, Part 1 of the
# brief: shape selection is deterministic Python from (level,
# suits_categories), picking from the INTERSECTION with the four canonical
# categories.
# ==============================================================================


def test_select_category_is_deterministic() -> None:
    first = select_category("PM", ["strategy", "gtm", "growth"])
    second = select_category("PM", ["strategy", "gtm", "growth"])
    assert first == second
    assert first in {"strategy", "gtm", "growth"}


def test_select_category_only_returns_a_category_the_world_supports() -> None:
    """The whole point of the field: a world that does not list "pricing"
    must never resolve to a pricing shape, for any level."""
    suits = ["strategy", "gtm", "growth"]
    for level in FOUR_LEVELS:
        assert select_category(level, suits) in suits


def test_select_category_falls_back_to_all_categories_when_empty() -> None:
    """The untouched generative path: `CaseWorld.suits_categories` defaults
    to `[]` there (only the eight curated worlds set it). An empty list
    must fall back to the full bank, not raise -- a generated world must
    still be able to get a question."""
    assert select_category("PM", []) in CATEGORIES
    assert select_category("PM", None) in CATEGORIES


def test_select_category_raises_on_an_unrecognized_category_list() -> None:
    """A curated world with a typo'd category name must fail loudly at
    selection time, not silently fall back and mask the typo the way an
    empty list correctly does."""
    with pytest.raises(ValueError):
        select_category("PM", ["not_a_real_category"])


# ==============================================================================
# 2026-08-07 -- the level-to-category calibration, and the seniority
# inversion it replaced.
#
# 🔴 THESE EXIST BECAUSE THE SUITE WAS SILENT. The tests above assert
# determinism, membership and fallback, but NOTHING asserted WHICH category a
# level receives -- so the mapping could be, and was, fully inverted while all
# 374 offline tests stayed green. That inversion is what served a Senior PM
# "How would you increase booking conversion" in gate #4's live interview on
# 2026-08-07, in a product that calls itself a Product Strategy interview.
# See DEV-STATE § Decisions 2026-08-07.
# ==============================================================================


def test_every_level_gets_a_strategy_question_when_the_world_suits_strategy() -> None:
    """Karthik's calibration, 2026-08-07: the category is NOT a dial to vary
    by seniority. Level selects difficulty WITHIN strategy, never whether the
    candidate sits a strategy question at all. All eight curated worlds list
    `strategy`, so this governs every real interview."""
    suits = ["strategy", "gtm", "growth"]
    for level in FOUR_LEVELS:
        assert select_category(level, suits) == "strategy", (
            f"{level} did not get a strategy question from a world that suits strategy"
        )


def test_a_more_senior_level_never_gets_an_easier_shape() -> None:
    """🔴 The invariant the old `% len(candidates)` violated. Shapes are
    ordered easiest-first, so wrapping handed the MOST senior level the
    EASIEST question: `strategy`, `gtm` and `pricing` each hold 3 shapes
    against 4 levels, so GPM (index 3) wrapped to index 0 and drew the APM
    question. Monotonicity is the property that catches that, for any
    category, at any future bank size -- an index assertion would not.

    Uses its OWN ordered tuple rather than `FOUR_LEVELS`, which is a `set`
    and iterates arbitrarily; this assertion is meaningless without a
    seniority order, and reading one out of a set is how it would rot.
    """
    ascending_seniority = ("APM", "PM", "Senior PM", "GPM")
    assert set(ascending_seniority) == FOUR_LEVELS, "the four levels drifted"

    for category in CATEGORIES:
        shapes = shapes_by_category(category)
        picked = [shapes.index(select_shape(level, category)) for level in ascending_seniority]
        assert picked == sorted(picked), (
            f"{category}: shape difficulty is not monotonic across "
            f"{list(ascending_seniority)} -- got indices {picked}"
        )


def test_the_category_fallback_still_reaches_the_other_three_categories() -> None:
    """Strategy winning must not make the rest of the bank dead code. A world
    that does NOT suit strategy still resolves into whatever it does suit --
    otherwise `gtm`, `pricing` and `growth` are unreachable and the bank is
    lying about its own size."""
    assert select_category("PM", ["gtm", "pricing"]) in {"gtm", "pricing"}
    assert select_shape_for_world("PM", ["growth"]).category == "growth"


def test_select_shape_for_world_composes_category_and_shape_selection() -> None:
    shape = select_shape_for_world("PM", ["pricing"])
    assert shape.category == "pricing"
    assert shape in SHAPE_BANK


def test_select_shape_for_world_is_deterministic() -> None:
    first = select_shape_for_world("GPM", ["strategy", "growth"])
    second = select_shape_for_world("GPM", ["strategy", "growth"])
    assert first == second


# ==============================================================================
# THE cross-gate control -- the coordinator's own ad hoc probe, made
# permanent. It found a real defect on its first run: the original gtm
# shape "{competitor} shipped {capability} first. How does that change
# {company}'s launch?" reads as recitation-shaped once filled (an
# explanatory frame with no `you`/`your` and no decision verb), which is
# `is_recitation_shaped` correctly doing its job -- the SHAPE was wrong,
# not the rule. Fixed by adding "your launch plan for" to that template
# (see shapes.py's comment on that shape for the full story).
#
# Parametrized directly off `SHAPE_BANK`, not a hard-coded count or list of
# strings, so a shape added later is automatically covered by this test and
# CANNOT be checked in in a state where the Planner could never emit it
# without failing its own gates -- which is exactly the class of bug this
# test caught. This is the single most valuable test in this file: it is
# the one that verifies the bank and the checks agree with each other,
# which every other test in this file silently assumes.
# ==============================================================================


@pytest.mark.parametrize("shape", SHAPE_BANK, ids=lambda s: s.template)
def test_every_bank_shape_clears_its_own_gates(shape) -> None:
    """Fill this shape with plausible values and assert the result clears
    all three gates the Planner will need to clear in story 3.5.3: no
    decorative statistic, not recitation-shaped, and -- trivially, but
    checked for completeness -- conforms to a bank shape (its own)."""
    filled = _fill(shape)

    stat = decorative_statistic(filled)
    assert stat is None, (
        f"shape {shape.template!r} filled as {filled!r} carries a decorative "
        f"statistic once filled: {stat!r}"
    )

    assert is_recitation_shaped(filled) is False, (
        f"shape {shape.template!r} filled as {filled!r} is recitation-shaped -- "
        f"the Planner could never emit this shape's output without failing its "
        f"own gate"
    )

    assert matches_no_shape(filled) is False, (
        f"shape {shape.template!r} filled as {filled!r} does not conform to any "
        f"bank shape, including its own -- the fill or the template has a bug"
    )


# ==============================================================================
# Part 4 of the brief: prove the suite is RED against today's Planner output,
# BEFORE any prompt change. Q1 and Q2 are real questions this product served
# on 2026-08-05 -- if a golden test required
# `assert decorative_statistic(q) is None` (or `not is_recitation_shaped(q)`)
# on every served question, as the future prompt change will need to satisfy,
# today's output fails it. This test encodes that exact assertion and proves
# it currently fails, so the suite is falsifiable rather than green by
# default. See the brief's Part 4 and the pasted terminal output in the
# session report for the standalone proof run outside pytest's own
# pass/fail framing.
# ==============================================================================


def test_RED_todays_q1_and_q2_would_fail_a_no_decorative_statistic_gate() -> None:
    """This test is EXPECTED TO STAY GREEN forever (it asserts the failure,
    not the fix) -- it exists to document, executably, that the gate story
    3.5.3 must satisfy is not met by story 3.5.2's own starting point."""
    assert decorative_statistic(Q1) is not None, (
        "Q1 SHOULD fail a decorative-statistic gate today -- if this "
        "assertion itself fails, the check has gone blind to the exact "
        "defect it exists to catch"
    )
    assert decorative_statistic(Q2) is not None, "Q2 should also fail it"
    assert decorative_statistic(Q3) is None, "Q3 has no statistic and must pass"


def test_RED_todays_q1_would_fail_a_not_recitation_shaped_gate() -> None:
    assert is_recitation_shaped(Q1) is True, (
        "Q1 SHOULD fail a not-recitation-shaped gate today"
    )
    assert is_recitation_shaped(Q2) is False
    assert is_recitation_shaped(Q3) is False


def test_RED_todays_three_questions_conform_to_no_bank_shape() -> None:
    """None of Q1/Q2/Q3 were built from the shape bank (it didn't exist when
    they were served) -- `matches_no_shape` must say so for all three,
    additional evidence that today's Planner output would fail a
    shape-conformance gate."""
    assert matches_no_shape(Q1) is True
    assert matches_no_shape(Q2) is True
    assert matches_no_shape(Q3) is True
