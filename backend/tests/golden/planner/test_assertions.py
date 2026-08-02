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

from tests.golden.case_architect import assertions as ca_assertions
from tests.golden.planner.assertions import (
    RUBRIC_DIMENSIONS,
    blank_or_short_fields,
    contains_banned_register_name,
    contains_fake_round_number,
    count_out_of_range,
    empty_grounded_in,
    is_generic_question,
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
