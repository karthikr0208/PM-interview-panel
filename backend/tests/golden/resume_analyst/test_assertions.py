"""Offline tests for the checkers in `assertions.py`. No network, no marker,
no import of `app.agents.resume_analyst` -- collects and runs under
`pytest tests -m "not live"` today, before that agent exists.

Precedent (CLAUDE.md / DEV-STATE, story 0.6 and story 1.5): an assertion is
not trusted until it has been shown to FAIL against input it should reject.
Every checker below gets both directions -- accepts the honest case, rejects
the dishonest one -- plus, where the project's own precedent
(`test_user_facing_copy.py::test_the_check_finds_real_user_facing_strings`)
shows the failure mode is a checker silently matching nothing (which would
make every downstream "no offenders" assertion vacuously true), a dedicated
guard against that.
"""
from __future__ import annotations

from tests.golden.resume_analyst.assertions import (
    EM_DASH,
    EN_DASH,
    contains_forbidden_token,
    eight_word_windows,
    empty_quote_lists,
    fold_typography,
    missing_verbatim_quotes,
    no_dash_variants,
    normalize_for_comparison,
    normalize_whitespace,
    rationale_cites_resume,
)
from tests.golden.resume_analyst.cases import CASES

RESUME = (
    "Owned the checkout and payments surface end to end across web and mobile, "
    "and set its quarterly roadmap independently of the wider commerce team. "
    "Grew conversion from 12.4% to 19.1% over two quarters."
)


# --- normalize_whitespace ----------------------------------------------------


def test_normalize_whitespace_collapses_runs_and_strips() -> None:
    assert normalize_whitespace("  a\n\nb\t\tc  ") == "a b c"


# --- fold_typography ---------------------------------------------------------


def test_fold_typography_maps_hyphen_and_quote_variants_to_ascii() -> None:
    """The variants gpt-oss actually emits against pure-ASCII fixtures."""
    assert fold_typography("hard‑coded") == "hard-coded"
    assert fold_typography("hard‐coded") == "hard-coded"
    assert fold_typography("the team’s roadmap") == "the team's roadmap"
    assert fold_typography("“shipped”") == '"shipped"'


def test_fold_typography_leaves_em_and_en_dashes_alone() -> None:
    """The deliberate exclusion, and the reason this fold cannot be widened
    casually: em- and en-dashes are distinct punctuation this project bans in
    candidate-facing copy, not renderings of the hyphen. Folding them would
    let a quote introduce a banned character and still read as verbatim."""
    assert fold_typography(f"checkout {EM_DASH} payments") == f"checkout {EM_DASH} payments"
    assert fold_typography(f"2019{EN_DASH}2023") == f"2019{EN_DASH}2023"


def test_fold_typography_is_a_noop_on_ascii() -> None:
    assert fold_typography(RESUME) == RESUME


def test_normalize_for_comparison_applies_both_and_preserves_case() -> None:
    assert normalize_for_comparison("  Hard‑coded\n\nlist  ") == "Hard-coded list"


# --- eight_word_windows: vacuity guard ---------------------------------------


def test_eight_word_windows_count_and_boundaries_are_not_vacuous() -> None:
    """Pins the window count to len(words) - 7 and checks the first and last
    window's exact content, not merely non-emptiness. A degenerate
    implementation (one giant window, or silently returning []) would sail
    through a looser check and quietly break every case that depends on it,
    the same silent-pass shape CLAUDE.md's precedent warns about."""
    ten_words = "one two three four five six seven eight nine ten"
    windows = eight_word_windows(ten_words, min_words=8)
    assert len(windows) == 3, windows
    assert windows[0] == "one two three four five six seven eight"
    assert windows[-1] == "three four five six seven eight nine ten"


def test_eight_word_windows_empty_below_threshold() -> None:
    assert eight_word_windows("only seven words total right here today", min_words=8) == []


# --- rationale_cites_resume ---------------------------------------------------


def test_rationale_cites_resume_accepts_a_genuine_span() -> None:
    rationale = (
        "Owned the checkout and payments surface end to end across web and mobile, "
        "which reads as Senior PM-level scope."
    )
    assert rationale_cites_resume(rationale, RESUME)


def test_rationale_cites_resume_rejects_generic_praise() -> None:
    rationale = "An impressive track record of driving meaningful impact across the organisation."
    assert not rationale_cites_resume(rationale, RESUME)


def test_rationale_cites_resume_is_case_insensitive_by_design() -> None:
    """Documents the deliberate choice: a rationale opening a sentence with
    the resume's mid-sentence clause differs only in capitalization, and that
    difference should not fail an otherwise genuine citation."""
    rationale = "OWNED THE CHECKOUT AND PAYMENTS SURFACE END TO END ACROSS WEB AND MOBILE."
    assert rationale_cites_resume(rationale, RESUME)


# --- missing_verbatim_quotes ---------------------------------------------------


def test_missing_verbatim_quotes_accepts_a_real_quote() -> None:
    assert missing_verbatim_quotes(["Grew conversion from 12.4% to 19.1%"], RESUME) == []


def test_missing_verbatim_quotes_rejects_a_fabricated_quote() -> None:
    fake = "Grew conversion from 40% to 90%"
    assert missing_verbatim_quotes([fake], RESUME) == [fake]


def test_missing_verbatim_quotes_is_case_sensitive_by_design() -> None:
    """Documents the deliberate choice: scope_evidence / notable_outcomes are
    specified as verbatim quotes, not paraphrase, so a recapitalized
    fabrication must not be waved through as a genuine one."""
    recapitalized = "grew CONVERSION from 12.4% to 19.1%"
    assert missing_verbatim_quotes([recapitalized], RESUME) == [recapitalized]


def test_missing_verbatim_quotes_accepts_a_typographic_hyphen_variant() -> None:
    """The false positive this fold exists to close, measured 2026-08-01 on
    golden case 08: gpt-oss-120b reproduced 42 words of the fixture exactly and
    emitted U+2011 for the two ASCII hyphens. The words were identical; the
    suite's most important assertion called it a fabrication."""
    source = "replacing a hard-coded list of nine built-in commands"
    assert missing_verbatim_quotes(["replacing a hard‑coded list"], source) == []


def test_missing_verbatim_quotes_still_rejects_a_fabrication_wearing_a_hyphen() -> None:
    """The fold must not become a fabrication path. Same typographic hyphen,
    but the WORDS are invented -- this must still fail."""
    fake = "replacing a hard‑coded list of forty legacy commands"
    source = "replacing a hard-coded list of nine built-in commands"
    assert missing_verbatim_quotes([fake], source) == [fake]


def test_missing_verbatim_quotes_rejects_a_quote_that_swaps_in_an_em_dash() -> None:
    """The guard on the exclusion above. A quote that introduces the banned
    character is not verbatim, and the fold must not launder it."""
    source = "Owned checkout and payments, and set its quarterly roadmap"
    swapped = f"Owned checkout and payments{EM_DASH} and set its quarterly roadmap"
    assert missing_verbatim_quotes([swapped], source) == [swapped]


def test_missing_verbatim_quotes_empty_list_is_vacuously_honest() -> None:
    """An agent that quotes nothing has fabricated nothing -- this is the one
    place an empty result is the correct, non-vacuous answer.

    Correct for this helper in isolation, and exactly why `empty_quote_lists`
    below has to exist: at the suite level that same property let an agent
    quoting nothing pass the spec's most important assertion on all eight
    cases at once."""
    assert missing_verbatim_quotes([], RESUME) == []


# --- empty_quote_lists: the floor under the two checks above ---------------------


def test_empty_quote_lists_catches_the_agent_that_quotes_nothing() -> None:
    """The regression this checker exists for, proven 2026-07-31: empty lists
    sail through `missing_verbatim_quotes` on every case."""
    assert empty_quote_lists([], [], expect_outcomes=True) == [
        "scope_evidence",
        "notable_outcomes",
    ]


def test_empty_quote_lists_accepts_a_substantive_profile() -> None:
    assert (
        empty_quote_lists(
            ["Owned the checkout and payments surface end to end"],
            ["Grew conversion from 12.4% to 19.1%"],
            expect_outcomes=True,
        )
        == []
    )


def test_empty_quote_lists_permits_no_outcomes_only_where_the_fixture_states_none() -> None:
    """Fixture 07 states zero results, so an empty notable_outcomes is the
    honest answer there and a failure everywhere else. Both directions."""
    assert empty_quote_lists(["Managed the partner integrations roadmap"], [], expect_outcomes=False) == []
    assert empty_quote_lists(["Managed the partner integrations roadmap"], [], expect_outcomes=True) == [
        "notable_outcomes"
    ]


def test_empty_quote_lists_never_excuses_empty_scope_evidence() -> None:
    """`expect_outcomes=False` relaxes outcomes only. Every fixture describes
    ownership scope, so an empty scope_evidence is always a failure to work."""
    assert empty_quote_lists([], ["Grew conversion from 12.4% to 19.1%"], expect_outcomes=False) == [
        "scope_evidence"
    ]


def test_exactly_one_case_expects_no_outcomes() -> None:
    """Vacuity guard on the flag itself: if a future edit set expect_outcomes
    False everywhere, the outcomes floor would silently stop gating."""
    relaxed = [c.id for c in CASES if not c.expect_outcomes]
    assert relaxed == ["07_duties_no_outcomes"], relaxed


# --- no_dash_variants -----------------------------------------------------------


def test_dash_constants_are_distinct_single_characters() -> None:
    """Guards the guard: a wrong constant (e.g. an accidental empty string)
    would make `no_dash_variants` return True unconditionally."""
    assert len(EM_DASH) == 1
    assert len(EN_DASH) == 1
    assert EM_DASH != EN_DASH


def test_no_dash_variants_catches_an_em_dash() -> None:
    assert not no_dash_variants(f"Owned checkout {EM_DASH} set its roadmap.")


def test_no_dash_variants_catches_an_en_dash() -> None:
    assert not no_dash_variants(f"Owned checkout 2019{EN_DASH}2023.")


def test_no_dash_variants_accepts_clean_text() -> None:
    assert no_dash_variants("Owned checkout, set its roadmap.")


# --- contains_forbidden_token -----------------------------------------------------


def test_contains_forbidden_token_catches_the_fixtures_name() -> None:
    case = next(c for c in CASES if c.id == "01_apm_rotational")
    leaked = contains_forbidden_token(
        "Ingrid Solberg owned a single onboarding screen.", list(case.forbidden_tokens)
    )
    assert leaked is not None


def test_contains_forbidden_token_returns_none_when_clean() -> None:
    case = next(c for c in CASES if c.id == "01_apm_rotational")
    clean = contains_forbidden_token(
        "The candidate owned a single onboarding screen inside a larger flow.",
        list(case.forbidden_tokens),
    )
    assert clean is None


# --- vacuity guard on the case table itself --------------------------------------


def test_every_case_declares_a_real_forbidden_token_set() -> None:
    """A case shipped with an empty (or trivially small) forbidden_tokens
    tuple would make the golden suite's leak check pass on every run for
    that case, no matter what the agent writes into level_rationale -- the
    same silent-pass failure shape as an AST walk that finds nothing to
    check. Each fixture is built with a name, a university, and a
    nationality-suggesting detail (brief for story 1.3a), so 3 is the floor."""
    for case in CASES:
        assert len(case.forbidden_tokens) >= 3, (
            f"{case.id}: forbidden_tokens too small to be a real guard: {case.forbidden_tokens}"
        )


def test_every_case_fixture_file_exists_and_is_nonempty() -> None:
    """Guards against a typo'd filename in cases.py that would otherwise only
    surface as a confusing FileNotFoundError deep inside a live, expensive
    test run."""
    for case in CASES:
        text = case.resume_text
        assert text.strip(), f"{case.id}: fixture file is empty"
