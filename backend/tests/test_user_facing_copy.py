"""The em-dash ban, enforced against the code rather than trusted to reviewers.

CLAUDE.md § Design: "No em-dashes in user-facing UI copy. Docs are exempt;
anything a candidate reads is not." Story 1.2 shipped three em-dashes into
candidate-facing error messages anyway, in a function whose own docstring said
"the message is written for the candidate reading it" - so the author knew the
strings were user-facing and the rule still did not survive contact. That is
the definition of a rule needing a test instead of a reviewer.

Deliberately narrow: it inspects only strings passed to `HTTPException(...)`
and to `*Error(...)` constructors, which is what actually reaches a candidate.
Docstrings, comments, and developer-facing exceptions are exempt by the rule
itself, and a check that flagged them would be noise nobody keeps green.

Offline, no network, no database.
"""

from __future__ import annotations

import ast
import pathlib
import re
from pathlib import Path

APP_ROOT = pathlib.Path(__file__).resolve().parent.parent / "app"

EM_DASH = "\u2014"  # em dash
EN_DASH = "\u2013"  # en dash

# The other five dash-family characters. Widened 2026-08-06 after a
# non-breaking hyphen (U+2011) reached a live, candidate-facing probe and
# crashed a console print with UnicodeEncodeError -- this file's job is to
# catch exactly that class of character before it ships, and two of seven
# was not enough. Unlike `stripDashes` (`frontend/src/lib/copy.ts`) and the
# golden-suite assertions (`tests/golden/planner/assertions.py`,
# `tests/golden/interviewer/assertions.py`), this file does NOT split
# hyphen-like from aside/range dashes: the strings it scans (HTTPException
# messages, `_SUMMARY` constants, `_TRANSITIONS` lines) are rendered
# verbatim by the frontend with no `stripDashes` call in between (see
# `OrchestrationColumn.tsx`'s `status.summary` render), so there is no
# downstream fix to lean on. Any of the seven reaching a candidate through
# this surface is a real defect, not a formatting choice.
HYPHEN = "\u2010"  # hyphen
NON_BREAKING_HYPHEN = "\u2011"  # non-breaking hyphen
FIGURE_DASH = "\u2012"  # figure dash
HORIZONTAL_BAR = "\u2015"  # horizontal bar
MINUS_SIGN = "\u2212"  # minus sign

DASH_VARIANTS = (
    HYPHEN,
    NON_BREAKING_HYPHEN,
    FIGURE_DASH,
    EN_DASH,
    EM_DASH,
    HORIZONTAL_BAR,
    MINUS_SIGN,
)

# Raised at import/wiring time and read only by a developer. Phase 1 leaves the
# real graph unwired on purpose; story 1.4 replaces this.
DEVELOPER_FACING = {"NotImplementedError", "ConfigError", "StructuredOutputError"}


def _literal(node: ast.AST) -> str | None:
    """Best-effort constant text of an argument. Handles plain strings,
    implicit concatenation (a BinOp of constants after parsing), and f-strings,
    reading only their constant parts.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value for v in node.values if isinstance(v, ast.Constant))
    if isinstance(node, ast.BinOp):
        return "".join(
            c.value
            for c in ast.walk(node)
            if isinstance(c, ast.Constant) and isinstance(c.value, str)
        )
    return None


def _user_facing_strings() -> list[tuple[str, int, str, str]]:
    found: list[tuple[str, int, str, str]] = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
                continue
            name = node.func.id
            if name in DEVELOPER_FACING:
                continue
            if not (name == "HTTPException" or name.endswith("Error")):
                continue
            for arg in node.args:
                text = _literal(arg)
                if text:
                    found.append((path.name, node.lineno, name, text))
    return found


def _agent_event_summaries() -> list[tuple[str, int, str, str]]:
    """Every `_*_SUMMARY` module constant in `app/`.

    These are candidate-facing and were NOT in scope until 2026-08-04. They
    are written into `agent_events.summary` and rendered VERBATIM by
    `frontend/src/components/OrchestrationColumn.tsx`, in preference to that
    component's own fallback copy -- so a dash typed here reaches a candidate
    just as surely as one in an `HTTPException`. Story 2.7 tripled the number
    of them (three agents rather than one), which is what made the gap worth
    closing.

    Matched on the `_SUMMARY` name suffix rather than on the assignment's
    location, so a summary added to a future agent's node is covered the day
    it is written and nobody has to remember this file exists.
    """
    found: list[tuple[str, int, str, str]] = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if not (isinstance(target, ast.Name) and target.id.endswith("_SUMMARY")):
                    continue
                text = _literal(node.value)
                if text:
                    found.append((path.name, node.lineno, target.id, text))
    return found


def _transition_lines() -> list[tuple[str, int, str, str]]:
    """Every string inside a `_TRANSITIONS` tuple in `app/`.

    In scope since 2026-08-05, and the reason this collector exists is the
    whole argument for the change that created it. The transition between
    interview questions used to be an LLM call, whose output no static check
    could ever see; it was replaced by source strings precisely so the
    em-dash ban on that surface could be ENFORCED rather than merely
    prompted. Prompting had already failed twice on that exact rule (the
    Planner shipped em-dashes into candidate-facing questions), so a
    prompted ban is not a ban.

    These are read aloud by the interviewer immediately before the question,
    so they are as candidate-facing as copy gets.
    """
    found: list[tuple[str, int, str, str]] = []
    for path in sorted(APP_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.AnnAssign | ast.Assign):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if not any(isinstance(t, ast.Name) and t.id == "_TRANSITIONS" for t in targets):
                continue
            if not isinstance(node.value, ast.Tuple | ast.List):
                continue
            for element in node.value.elts:
                text = _literal(element)
                if text:
                    found.append((path.name, node.lineno, "_TRANSITIONS", text))
    return found


def test_the_transition_check_finds_the_interviewers_lines() -> None:
    """Guards the guard, same reasoning as the two below. An AST walk that
    silently matched nothing would make the dash test below pass vacuously,
    which is the exact failure story 1.3a is named for."""
    lines = _transition_lines()
    assert len(lines) >= 3, (
        f"expected the Interviewer's transition lines to be in scope, found {lines}"
    )


def test_no_dashes_in_interview_transitions() -> None:
    offenders = [
        f"{f}:{line} {name} -> {text[:80]}"
        for f, line, name, text in _transition_lines()
        if any(d in text for d in DASH_VARIANTS)
    ]
    assert not offenders, (
        "dash-family character in an interview transition line, which is read "
        "immediately before the question (CLAUDE.md § Design):\n" + "\n".join(offenders)
    )


def test_the_summary_check_finds_every_agents_copy() -> None:
    """Guards the guard, same reasoning as the one below it. A name-suffix
    match that drifted would silently stop covering the strings candidates
    actually read."""
    summaries = _agent_event_summaries()
    names = {name for _, _, name, _ in summaries}
    assert len(summaries) >= 9, f"expected 3 summaries per agent for 3 agents, got {summaries}"
    for expected in ("_CASE_WORLD_DONE_SUMMARY", "_PLAN_DONE_SUMMARY", "_DONE_SUMMARY"):
        assert expected in names, f"{expected} is candidate-facing and must be in scope: {names}"


def test_no_dashes_in_agent_event_summaries() -> None:
    offenders = [
        f"{f}:{line} {name} -> {text[:80]}"
        for f, line, name, text in _agent_event_summaries()
        if any(d in text for d in DASH_VARIANTS)
    ]
    assert not offenders, (
        "dash-family character in an agent_events summary, which the orchestration "
        "column renders verbatim to the candidate (CLAUDE.md § Design):\n" + "\n".join(offenders)
    )


def test_the_check_finds_real_user_facing_strings() -> None:
    """Guards the guard. An AST walk that silently matches nothing would make
    every assertion below vacuously true - the same failure shape as a
    cross-session denial test whose token is malformed.
    """
    strings = _user_facing_strings()
    assert len(strings) >= 5, f"expected to find real user-facing copy, got {strings}"
    assert any("PDF" in text for _, _, _, text in strings), (
        "story 1.2's upload error messages should be in scope for this check"
    )


def test_no_em_dashes_in_user_facing_copy() -> None:
    offenders = [
        f"{f}:{line} {call}() -> {text[:80]}"
        for f, line, call, text in _user_facing_strings()
        if EM_DASH in text
    ]
    assert not offenders, "em-dash in candidate-facing copy (CLAUDE.md § Design):\n" + "\n".join(
        offenders
    )


def test_no_en_dashes_in_user_facing_copy() -> None:
    offenders = [
        f"{f}:{line} {call}() -> {text[:80]}"
        for f, line, call, text in _user_facing_strings()
        if EN_DASH in text
    ]
    assert not offenders, "en-dash in candidate-facing copy:\n" + "\n".join(offenders)


def test_no_other_dash_variants_in_user_facing_copy() -> None:
    """The five dash-family characters `test_no_em_dashes_in_user_facing_copy`
    and `test_no_en_dashes_in_user_facing_copy` do not cover: hyphen,
    non-breaking hyphen, figure dash, horizontal bar, minus sign. Split into
    its own test, mirroring the em/en split above, so a failure here names
    the newly-covered characters instead of reusing the older two tests'
    messaging. Added 2026-08-06 -- see module docstring and `DASH_VARIANTS`
    for why this file covers the full family and not just the four
    aside/range dashes the golden suites check.
    """
    other_variants = (HYPHEN, NON_BREAKING_HYPHEN, FIGURE_DASH, HORIZONTAL_BAR, MINUS_SIGN)
    offenders = [
        f"{f}:{line} {call}() -> {text[:80]}"
        for f, line, call, text in _user_facing_strings()
        if any(d in text for d in other_variants)
    ]
    assert not offenders, (
        "hyphen-like or other dash-family character in candidate-facing "
        "copy (CLAUDE.md § Design):\n" + "\n".join(offenders)
    )


def test_all_three_suites_dash_variants_agree() -> None:
    """`tests/golden/planner/`, `tests/golden/interviewer/` and
    `tests/golden/resume_analyst/assertions.py` each define their own
    `_DASH_VARIANTS` constant on purpose -- their docstrings say the golden
    suites must stay independently importable even if a sibling's internals
    change shape.

    🔴 The resume_analyst copy is why this test names three modules and not
    two. It was the copy LEFT BEHIND when the other two were widened on
    2026-08-06, found only because a subagent flagged it out of scope. Its
    surface is `level_rationale`, which the candidate reads on the
    confirmation screen, so the weaker rule was live on a real surface.
    But a duplicated constant drifting apart is the actual long-term risk
    (this project has been bitten by exactly that class of rot before, per
    CLAUDE.md's "triggered updates" table) -- if one suite's set is widened
    to a newly-discovered dash-family character and the other is not, one
    golden suite silently starts enforcing a weaker rule than its sibling.
    This test is the guard: not a redundant duplication of the fix, an
    explicit check that the duplication has not rotted.
    """
    from tests.golden.interviewer.assertions import _DASH_VARIANTS as interviewer_variants
    from tests.golden.planner.assertions import _DASH_VARIANTS as planner_variants
    from tests.golden.resume_analyst.assertions import _DASH_VARIANTS as resume_variants

    sets = {
        "planner": set(planner_variants),
        "interviewer": set(interviewer_variants),
        "resume_analyst": set(resume_variants),
    }
    assert len(set(map(frozenset, sets.values()))) == 1, (
        "the three golden suites' _DASH_VARIANTS have drifted apart: "
        + ", ".join(f"{name}={sorted(v)!r}" for name, v in sets.items())
    )


# ==============================================================================
# `app.text.normalize_dashes` -- 2026-08-07. The golden suites DETECT dashes in
# what an agent generated; this FIXES them on the way to the database and the
# browser. Both exist because a display-only guard was not enough: a live
# interview on 2026-08-07 left 3 U+2011 in `question_plan` and 1 at
# `transcript_turns` idx=16, and Phase 4 renders scorecards from those rows.
# ==============================================================================


def test_normalize_dashes_handles_every_variant_the_suites_know_about() -> None:
    """Behavioural coverage of both classes, and the two literals below are
    the STRINGS THAT ACTUALLY REACHED A CANDIDATE on 2026-08-07 -- pinned
    rather than paraphrased, same reason as the interviewer suite's
    `echoes_false_premise` regression string."""
    from app.text import normalize_dashes

    # Hyphen-like -> ASCII hyphen. Both observed live.
    assert normalize_dashes("post‑booking placement") == "post-booking placement"
    assert normalize_dashes("short‑term rental market") == "short-term rental market"
    assert normalize_dashes("state‐of‐the‐art") == "state-of-the-art"
    assert normalize_dashes("a value of −5") == "a value of -5"

    # Aside/range -> " to " between digits, otherwise a comma.
    assert normalize_dashes("grew 2019–2023 steadily") == "grew 2019 to 2023 steadily"
    assert normalize_dashes("the plan — which slipped — shipped") == (
        "the plan, which slipped, shipped"
    )
    # A dash before other punctuation must not leave a stranded comma.
    assert normalize_dashes("ends with a dash —.") == "ends with a dash."

    # Total: callable on an absent optional field without guarding first.
    assert normalize_dashes("") == ""
    assert normalize_dashes(None) == ""  # type: ignore[arg-type]


def test_normalize_dashes_covers_exactly_the_family_the_suites_assert_on() -> None:
    """The fourth arm of the drift guard above, and it is deliberately TWO
    assertions because the two families are governed by different rules.

    🔴 The golden suites' `_DASH_VARIANTS` holds only the FOUR aside/range
    dashes, and that is correct, not an oversight. A BAN is right for those:
    an em dash in generated prose is an AI tell. A ban would be WRONG for
    the hyphen-like three -- U+2011 in "state-of-the-art" is a hyphen doing
    a hyphen's job, and the fix is to normalise it to ASCII, not to reject
    the generation. So `app.text` covers seven and the suites assert on
    four, by design. (This test asserted a flat equality when first written
    on 2026-08-07 and failed, which is how the distinction got pinned.)
    """
    from app.text import _ASIDE_LIKE, _HYPHEN_LIKE
    from tests.golden.planner.assertions import _DASH_VARIANTS as planner_variants

    assert set(_ASIDE_LIKE) == set(planner_variants), (
        "the aside/range dashes the app normalises and the golden suites ban "
        f"have drifted: app={sorted(set(_ASIDE_LIKE))!r} "
        f"suites={sorted(set(planner_variants))!r}"
    )
    assert set(_HYPHEN_LIKE) | set(_ASIDE_LIKE) == set(DASH_VARIANTS), (
        "app.text does not cover the same seven characters this module bans "
        f"in source strings: app={sorted(set(_HYPHEN_LIKE) | set(_ASIDE_LIKE))!r} "
        f"module={sorted(set(DASH_VARIANTS))!r}"
    )


def test_normalize_dashes_matches_stripDashes_character_classes() -> None:
    """🔴 The Python/TypeScript parity pin. `app.text.normalize_dashes` and
    `stripDashes` (`frontend/src/lib/copy.ts`) implement the SAME rules on
    two runtimes, and nothing but this test stops them diverging -- which is
    exactly the rot that left `resume_analyst`'s copy behind on 2026-08-06.

    Reads the TypeScript as TEXT and compares the character classes rather
    than executing it: this suite has no JS runtime, and the classes are
    where a divergence would actually show up.
    """
    from app.text import _ASIDE_LIKE, _HYPHEN_LIKE

    copy_ts = (
        Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "copy.ts"
    ).read_text(encoding="utf-8")

    classes = re.findall(r"\[([‐-―−]+)\]", copy_ts)
    assert classes, (
        "no dash character class found in frontend/src/lib/copy.ts -- either "
        "stripDashes was rewritten or this test's pattern has rotted; do NOT "
        "delete this test to make it pass"
    )

    ts_family = set("".join(classes))
    assert ts_family == set(_HYPHEN_LIKE) | set(_ASIDE_LIKE), (
        "stripDashes and normalize_dashes cover different characters: "
        f"ts={sorted(ts_family)!r} python={sorted(set(_HYPHEN_LIKE) | set(_ASIDE_LIKE))!r}"
    )

    # The hyphen-like class must be handled SEPARATELY on both sides. Folding
    # a non-breaking hyphen in "state-of-the-art" into a comma would be worse
    # than leaving it, which is why this is two classes and not one.
    assert set(_HYPHEN_LIKE) in [set(c) for c in classes], (
        "the TypeScript no longer treats the hyphen-like characters as their "
        f"own class: classes={[sorted(set(c)) for c in classes]!r}"
    )
