"""Offline tests for the checkers in `assertions.py`. No network, no marker,
no import of `app.agents.interviewer` -- collects and runs under `pytest
tests -m "not live"` today, before that agent exists.

Precedent (CLAUDE.md / DEV-STATE, story 0.6, 1.3a, 1.5, 2.2, 2.5): a denial
assertion is not trusted until it has been shown to FAIL against input it
should reject. Every checker below gets both directions -- accepts the
honest value, rejects the dishonest one named in
AGENT-INTERVIEWER-SPEC.md §5's positive-control table -- plus a guard
against story 1.3a's failure mode: a checker that returns "nothing wrong"
on an empty or missing input, which lets an agent that produced NOTHING
pass the check vacuously.

Sections mirror AGENT-INTERVIEWER-SPEC.md §5's assertion table plus the
story 3.1 brief's explicit control list:
  - vacuity floor on `grounded_in`, both branches of `can_answer`
  - grounding (missing_grounding) -- same shape as planner's
  - the figure check (ungrounded_figures) -- this suite's teeth, and NEW
    relative to the planner suite
  - can_answer=False must mean no figure at all
  - dash variants, fake-round numbers, banned-register names
  - refusal quality: must name the world's silence, not merely be short
  - the cross-world control -- built from a hand-written answer since no
    agent exists yet to generate a real one
"""
from __future__ import annotations

import json

import pytest

from tests.golden.interviewer.assertions import (
    blank_or_short_fields,
    contains_any_figure,
    contains_banned_register_name,
    contains_fake_round_number,
    figures_in_text,
    grounded_in_is_empty,
    missing_grounding,
    no_dash_variants,
    refusal_names_silence,
    ungrounded_figures,
    world_haystack,
)
from tests.golden.interviewer.cases import CASES, FIXTURES_DIR, _PLANNER_FIXTURES_DIR

# ==============================================================================
# Load the case worlds this suite reuses from the planner package, once.
# ==============================================================================


def _load_world(fixture_name: str) -> dict:
    payload = json.loads((_PLANNER_FIXTURES_DIR / f"{fixture_name}.json").read_text(encoding="utf-8"))
    return payload["case_world"]


APM_WORLD = _load_world("apm_consumer_world")
GPM_WORLD = _load_world("gpm_portfolio_world")
SPARSE_WORLD = _load_world("sparse_world")


def test_five_cases_defined() -> None:
    """Pins the count named in the brief -- a fixture silently dropped from
    `CASES` (but left on disk) would otherwise pass every other check here."""
    assert len(CASES) == 5, [c.id for c in CASES]


def test_all_five_fixtures_exist_and_point_at_a_real_planner_world() -> None:
    """Guards against a typo'd `world_fixture` pointer, which would
    otherwise only surface as a confusing FileNotFoundError deep inside a
    live, expensive test run."""
    for case in CASES:
        assert (FIXTURES_DIR / f"{case.fixture}.json").exists(), case.id
        world_path = _PLANNER_FIXTURES_DIR / f"{case.world_fixture}.json"
        assert world_path.exists(), f"{case.id}: points at missing planner fixture {world_path}"
        assert case.planned_question.strip(), case.id
        assert case.clarifying_question.strip(), case.id


def test_fixtures_do_not_embed_a_case_world_of_their_own() -> None:
    """Rule 3 of the brief, mechanically checked: this package's own
    fixture files hold only the pointer and the two questions -- never a
    copy of `case_world` -- so a `CaseWorld` schema change breaks every
    downstream suite loudly rather than leaving a stale copy here."""
    expected_keys = {"world_fixture", "planned_question", "clarifying_question"}
    for case in CASES:
        payload = json.loads((FIXTURES_DIR / f"{case.fixture}.json").read_text(encoding="utf-8"))
        assert set(payload.keys()) == expected_keys, case.id


# ==============================================================================
# Vacuity floor -- grounded_in must be non-empty on BOTH branches of
# can_answer. Spec §5's named escape hatch.
# ==============================================================================


def test_grounded_in_is_empty_accepts_a_populated_list() -> None:
    assert grounded_in_is_empty(["Ferngrove Media"]) is False


def test_grounded_in_is_empty_rejects_the_positive_control() -> None:
    """Brief control: an answer of "" and one of "I'm not able to say."
    both with grounded_in: []."""
    assert grounded_in_is_empty([]) is True
    assert grounded_in_is_empty(None) is True


def test_missing_grounding_is_vacuously_empty_on_an_empty_grounded_in_list() -> None:
    """Demonstrates the trap exists (same as planner's identical test): an
    empty `grounded_in` has nothing to fail to find, so `missing_grounding`
    correctly -- and dangerously -- reports no problem. This is exactly why
    `grounded_in_is_empty` must run FIRST, per spec §5's ordering."""
    assert missing_grounding([], APM_WORLD) == []


def test_blank_or_short_fields_rejects_an_empty_answer() -> None:
    """Brief control: an answer of ""."""
    fields = {"answer": ""}
    assert blank_or_short_fields(fields, min_len=15) == ["answer"]


def test_blank_or_short_fields_rejects_a_noncommittal_short_answer() -> None:
    """Brief control: "I'm not able to say." -- short enough to fail the
    floor on its own, independent of the grounded_in check above."""
    fields = {"answer": "I'm not able to say."}
    assert blank_or_short_fields(fields, min_len=25) == ["answer"]


def test_blank_or_short_fields_accepts_a_substantive_answer() -> None:
    fields = {
        "answer": (
            "Ferngrove has 41,000 paying subscribers out of roughly 2.4 "
            "million monthly active users."
        )
    }
    assert blank_or_short_fields(fields, min_len=15) == []


# ==============================================================================
# Grounding -- missing_grounding, same shape as planner's.
# ==============================================================================


def test_missing_grounding_accepts_an_entry_that_exists_in_the_world() -> None:
    assert missing_grounding(["Ferngrove Media"], APM_WORLD) == []


def test_missing_grounding_rejects_the_positive_control() -> None:
    """Brief control: an answer grounded in "Northwind Logistics" (no world
    contains it)."""
    result = missing_grounding(["Northwind Logistics"], APM_WORLD)
    assert result == ["Northwind Logistics"]


def test_world_haystack_includes_nested_and_numeric_values() -> None:
    haystack = world_haystack(APM_WORLD)
    assert "Skillet Social" in haystack
    assert "41000" in haystack  # metrics.customer_count, an int
    assert "11.3" in haystack  # supporting_facts prose, a float elsewhere


# ==============================================================================
# The figure check -- ungrounded_figures. This suite's teeth, per spec §5,
# and NEW relative to the planner suite (which has no equivalent).
# ==============================================================================


def test_figures_in_text_extracts_dollar_percent_and_comma_forms() -> None:
    text = "Ferngrove has $18.3M in ARR, 41,000 subscribers, and 76.5% gross margin."
    figures = figures_in_text(text)
    assert "$18.3" in figures
    assert "41,000" in figures
    assert "76.5%" in figures


def test_ungrounded_figures_accepts_a_correctly_cited_figure() -> None:
    answer = "Ferngrove has 41,000 paying subscribers."
    assert ungrounded_figures(answer, APM_WORLD) == []


def test_ungrounded_figures_accepts_the_same_figure_written_with_a_comma() -> None:
    """The brief's explicit negative-side requirement: 41,000 written with
    a comma must PASS against a world storing the bare int 41000 -- spec
    §6's own named failure mode ("or 41,000 fails against a stored 41000
    and the check fires on a CORRECT answer") must NOT occur here."""
    assert ungrounded_figures("about 41,000 subscribers", APM_WORLD) == []


def test_ungrounded_figures_rejects_the_positive_control() -> None:
    """Brief control, and spec §5's exact example: an answer citing "about
    62,000 subscribers" against apm_consumer_world, which states 41,000."""
    answer = "Ferngrove has about 62,000 subscribers."
    result = ungrounded_figures(answer, APM_WORLD)
    assert result == ["62,000"]


def test_ungrounded_figures_rejects_the_fifty_percent_positive_control() -> None:
    """Brief control: an answer citing "50% of customers" -- not present in
    any world in this suite, so it must be reported as ungrounded (this is
    independent of, and in addition to, the fake-round-number check below,
    which flags it for a different reason)."""
    answer = "Roughly 50% of customers would be affected."
    assert "50%" in ungrounded_figures(answer, APM_WORLD)


def test_ungrounded_figures_allows_small_ordinal_counts() -> None:
    """The documented allow-list (1, 2, 3): "the second point" or "3
    options" read as conversational counts, not a world figure. Kept short
    per spec §5 -- do not widen it."""
    answer = "There are 3 options here, and I'd focus on the 2nd one."
    assert ungrounded_figures(answer, APM_WORLD) == []


def test_ungrounded_figures_does_not_let_the_allowlist_hide_a_real_figure() -> None:
    """The allow-list must not swallow a genuinely invented number just
    because it happens to also contain a small digit -- pins that "62,000"
    (which contains no allow-listed standalone token) still fires."""
    answer = "The 2nd cohort had about 62,000 subscribers."
    result = ungrounded_figures(answer, APM_WORLD)
    assert "62,000" in result
    assert "2" not in result  # the allow-listed ordinal itself is not flagged


def test_ungrounded_figures_rejects_a_small_invented_integer() -> None:
    """🔴 The hole the first version of this check had, measured 2026-08-05
    and pinned here so it cannot come back.

    `ungrounded_figures` originally substring-searched the flattened world,
    so "roughly 7 designers" PASSED against a world containing no 7 -- a
    single digit is a substring of almost any world (187 employees, $2.8B,
    76.5%). That made the check strongest against the large distinctive
    figures a model is least likely to invent, and blind to the small
    integers it is MOST likely to invent, which is backwards. It sat
    directly on top of fixture 3's premise: a headcount question is exactly
    where "about 7 designers" appears.
    """
    assert ungrounded_figures("There are roughly 7 designers on that team.", APM_WORLD) == ["7"]


def test_ungrounded_figures_still_accepts_a_small_integer_the_world_states() -> None:
    """The other side of the test above, and the reason set membership is
    the right fix rather than banning small integers outright:
    apm_consumer_world does state an 8 ("within 8 seconds of signup") and a
    187 (company.employees), so both must still pass."""
    assert ungrounded_figures("The feed loads within 8 seconds.", APM_WORLD) == []
    assert ungrounded_figures("Ferngrove has 187 employees.", APM_WORLD) == []


def test_ungrounded_figures_rejects_a_figure_embedded_in_a_larger_world_number() -> None:
    """Whole-token comparison, not substring: 18 must NOT pass merely
    because the world contains "$18.3M". A model citing "18 competitors"
    against a world with three is inventing, and the substring version
    waved it through."""
    assert ungrounded_figures("There are 18 competitors in this space.", APM_WORLD) == ["18"]


# ==============================================================================
# can_answer=False must mean no figure at all -- not just none that fails
# grounding. Brief control: a refusal that still volunteers a number.
# ==============================================================================


def test_contains_any_figure_accepts_a_figure_free_refusal() -> None:
    answer = "The brief does not specify Ridgeline's employee engagement score."
    assert contains_any_figure(answer) == []


def test_contains_any_figure_rejects_the_positive_control() -> None:
    """Brief control: a can_answer=False refusal that still volunteers a
    number -- must be caught even though the number might coincidentally be
    grounded (the guard is "no figure at all", not "no ungrounded figure")."""
    answer = "The brief does not specify this, but it's probably around 41,000."
    assert contains_any_figure(answer) == ["41,000"]


def test_contains_any_figure_exempts_the_ordinal_allowlist() -> None:
    answer = "The brief does not specify this, and it's not one of the 3 known metrics."
    assert contains_any_figure(answer) == []


# ==============================================================================
# Dash variants -- em dash and en dash, both directions.
# ==============================================================================


def test_no_dash_variants_accepts_plain_punctuation() -> None:
    assert no_dash_variants("The world does not specify this, unfortunately.") is True


def test_no_dash_variants_rejects_an_em_dash() -> None:
    """Brief control: text containing an em-dash."""
    assert no_dash_variants("Ferngrove has 41,000 subscribers—well above the market.") is False


def test_no_dash_variants_rejects_an_en_dash() -> None:
    """Brief control: text containing an en-dash."""
    assert no_dash_variants("The range is roughly 40,000–42,000 subscribers.") is False


# ==============================================================================
# Fake-round numbers and banned-register names, same sets as planner's.
# ==============================================================================


def test_contains_fake_round_number_accepts_an_organic_figure() -> None:
    assert contains_fake_round_number("Ferngrove's gross margin is 76.5%.") is None


def test_contains_fake_round_number_rejects_the_positive_control() -> None:
    """Brief control: an answer citing "50% of customers"."""
    assert contains_fake_round_number("About 50% of customers churn.") == "50%"


def test_contains_banned_register_name_accepts_an_organic_name() -> None:
    assert contains_banned_register_name("Ferngrove Media has 41,000 subscribers.") is None


def test_contains_banned_register_name_rejects_a_banned_token() -> None:
    assert contains_banned_register_name("Acme would respond by cutting price.") == "acme"


# ==============================================================================
# Refusal quality -- must NAME the world's silence, not merely be short.
# ==============================================================================


def test_refusal_names_silence_accepts_an_explicit_refusal() -> None:
    answer = "The brief does not specify Ridgeline's employee engagement score."
    assert refusal_names_silence(answer) is True


def test_refusal_names_silence_rejects_a_merely_short_nonanswer() -> None:
    """Brief control: "I'm not able to say." -- short, but never names the
    world's silence, so it must fail this check even though it would also
    fail the vacuity length floor separately."""
    assert refusal_names_silence("I'm not able to say.") is False


def test_refusal_names_silence_rejects_a_long_nonanswer_that_never_names_silence() -> None:
    """Proves this check is doing real work beyond the length floor: a
    LONG non-answer that still never states the world is silent must fail,
    or this check would be redundant with `blank_or_short_fields`."""
    answer = (
        "That's a really interesting question and one worth thinking "
        "carefully about, though I think we should focus on the bigger "
        "picture here instead of getting lost in that particular detail."
    )
    assert len(answer) >= 25  # long enough to pass a length floor
    assert refusal_names_silence(answer) is False


# ==============================================================================
# NAMED CONTROL -- the cross-world control, spec §5: "the single most
# valuable test in this suite" (planner's framing, inherited here). A
# plausible answer built for apm_consumer_world must FAIL grounding AND the
# figure check against gpm_portfolio_world. Hand-built since no agent
# exists yet to generate a real one.
# ==============================================================================

# A good-faith answer, hand-written FOR apm_consumer_world: grounded_in
# points at real entries in that world, and the only figure cited (41,000)
# is real there too.
GOOD_ANSWER_FOR_APM_WORLD = {
    "can_answer": True,
    "answer": (
        "Ferngrove has 41,000 paying subscribers out of roughly 2.4 million "
        "monthly active users."
    ),
    "grounded_in": [
        "Ferngrove has 41,000 paying subscribers out of roughly 2.4 million "
        "monthly active users."
    ],
}


def test_good_answer_passes_grounding_against_its_own_world() -> None:
    assert missing_grounding(GOOD_ANSWER_FOR_APM_WORLD["grounded_in"], APM_WORLD) == []


def test_good_answer_passes_the_figure_check_against_its_own_world() -> None:
    assert ungrounded_figures(GOOD_ANSWER_FOR_APM_WORLD["answer"], APM_WORLD) == []


def test_good_answer_FAILS_grounding_against_a_different_world() -> None:
    """The cross-world control's grounding half."""
    missing = missing_grounding(GOOD_ANSWER_FOR_APM_WORLD["grounded_in"], GPM_WORLD)
    assert missing == GOOD_ANSWER_FOR_APM_WORLD["grounded_in"], (
        "expected the apm-world grounded_in entry to fail entirely against "
        "gpm_portfolio_world, but it partially or fully matched -- a plan "
        "that grounds against an unrelated world is still too generic"
    )


def test_good_answer_FAILS_the_figure_check_against_a_different_world() -> None:
    """The cross-world control's figure half: 41,000 is real in
    apm_consumer_world (customer_count) but does not appear anywhere in
    gpm_portfolio_world (whose customer_count is 58,000)."""
    bad_figures = ungrounded_figures(GOOD_ANSWER_FOR_APM_WORLD["answer"], GPM_WORLD)
    assert "41,000" in bad_figures


# ==============================================================================
# Sanity check on the sparse-world fixture specifically (fixture 5): a
# grounded, figure-free refusal must be constructible against it, proving
# the fixture's silence is real rather than an artifact of a check that is
# too strict to ever pass.
# ==============================================================================


def test_a_grounded_figure_free_refusal_can_be_written_against_the_sparse_world() -> None:
    answer = (
        "The brief does not specify Palewell's churn rate from a year ago -- "
        "it only gives this quarter's 4.6% figure and notes it is the "
        "highest since launch."
    )
    grounded_in = ["Monthly churn is 4.6%, the highest of any month since launch."]
    assert missing_grounding(grounded_in, SPARSE_WORLD) == []
    assert refusal_names_silence(answer) is True
    # This particular hand-written refusal cites the (grounded) current
    # figure while explaining what is missing -- contains_any_figure would
    # flag it, which is deliberately why cases.py's own check for this
    # fixture uses a refusal that omits the figure entirely. This test only
    # proves the world's silence is real and articulable, not that every
    # articulation is figure-free.
