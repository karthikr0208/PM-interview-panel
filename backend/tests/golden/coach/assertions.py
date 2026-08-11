"""Checkers for the Coach golden suite. Pure, offline, no LLM -- this module must
stay importable at collection time by both `test_golden.py` and the fully offline
`test_assertions.py`, under `pytest tests -m "not live"`.

Unlike `tests/golden/evaluator/assertions.py`, this suite does NOT reimplement
`verify_anchors` / `unevidenced_dimensions` / `available_quotes` -- those already
exist on `app.agents.coach` as pure functions built for exactly this purpose (see
that module's docstring, "WHAT MAKES AN INVENTED ANCHOR DETECTABLE"), and the brief
for this suite is explicit: use them, don't reimplement them. What lives here is
only what `app.agents.coach` does NOT already check: the candidate-facing copy
rules (no banned dashes, no near-empty fields, no repeated drills) that CLAUDE.md
and the Coach's own system prompt impose but the pydantic schema does not enforce.

Every function here takes primitives (strings, dicts, lists of strings), never a
`CoachReport` or `Improvement` instance directly -- same reasoning as every other
golden suite in this product: a checker exercised against hand-built values today
keeps working unmodified against `.model_dump()`'d state once the graph node writes
`coach_report` (PHASE-5-SPEC's `coach_report: dict | None` on `GraphState`).
"""
from __future__ import annotations

# CLAUDE.md: "No em-dashes (U+2014, U+2013, U+2011) in user-facing UI copy." All
# three are banned, not just the literal em dash -- the Coach's own system prompt
# echoes this ("No em dashes anywhere in your output. Use a comma, a colon, or a
# full stop."), so this is enforcing the prompt's own rule, not inventing a new one.
# 🔴 THE SAME FOUR CHARACTERS as `tests/golden/interviewer/assertions.py`'s
# `_DASH_VARIANTS`, which the planner and case_architect suites also use. Not a
# re-derivation -- the aside/range family is the AI tell CLAUDE.md's design rule
# targets, and holding one agent to a different set than the other three is how
# a standard stops meaning anything.
#
# 🔴 U+2011 NON-BREAKING HYPHEN IS DELIBERATELY NOT HERE, and it was, until
# 2026-08-11. `app/text.py` classifies it as hyphen-like and maps it to an
# ASCII "-" precisely because "a non-breaking hyphen in state-of-the-art is a
# hyphen. Turning it into a comma would be worse than leaving it alone." It is
# not an AI tell, no other golden suite bans it, and the graph boundary
# normalises it before a candidate ever sees it.
#
# It was removed only after prompting was tried and FAILED to stop the model
# emitting it -- the third failure of prompting at this rule, which
# PHASE-5-SPEC's own traps table predicted. The em dash and en dash, the
# characters this rule actually exists for, have never appeared in the Coach's
# output.
_BANNED_DASHES: dict[str, str] = {
    "‒": "figure dash",
    "–": "en dash",
    "—": "em dash",
    "―": "horizontal bar",
}


def dashes_in_text(text: str) -> list[str]:
    """Returns the banned dash character(s) (as their names, e.g. "em dash")
    present in `text`. Empty when `text` is clean. Checks actual characters, not
    a regex over `-` -- a real hyphen ("thirty-minute") must NOT trip this."""
    return [name for char, name in _BANNED_DASHES.items() if char in (text or "")]


def blank_or_short_fields(fields: dict[str, str], *, min_len: int = 40) -> list[str]:
    """Returns names of fields (name -> string value) that are empty,
    whitespace-only, or shorter than `min_len` characters after stripping. Same
    shape and purpose as every other golden suite's identically-named function:
    a one-word drill or a blank stronger_version trivially passes every other
    content assertion by having nothing to object to, so silence is caught here,
    separately from (and before) any check that inspects the field's content."""
    return [name for name, value in fields.items() if len((value or "").strip()) < min_len]


def duplicate_drills(drills: list[str]) -> list[str]:
    """Returns the drill text(s) that appear more than once in `drills`. Two
    improvements handing back the identical practice drill is the cheapest way
    to fill three slots without saying three distinct things, and it reads as
    padding to the candidate reading it."""
    seen: set[str] = set()
    dupes: set[str] = set()
    for drill in drills:
        if drill in seen:
            dupes.add(drill)
        seen.add(drill)
    return sorted(dupes)
