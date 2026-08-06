"""Checkers for the Interviewer golden suite. Pure, offline, no LLM, no
import of `app.agents.interviewer` -- this module must stay importable
before that agent exists, since `test_assertions.py` exercises it at
collection time under `pytest tests -m "not live"`.

Deliberately self-contained rather than importing from
`tests.golden.planner.assertions`, matching that suite's own stated choice
(AGENT-INTERVIEWER-SPEC.md §5): each golden package must stay independently
importable even if a sibling suite's internals change shape. Every function
takes primitives (dicts, lists, strings) -- never a `ClarificationAnswer`
instance -- for the same reason planner's and case_architect's do: they can
be exercised offline against hand-built dicts before the schema they will
eventually check against is even code (AGENT-INTERVIEWER-SPEC.md §3).
"""
from __future__ import annotations

import re

# --- vacuity floor -- must be asserted FIRST, before anything it could hide
# behind (AGENT-INTERVIEWER-SPEC.md §5's ordering: "Vacuity floor is
# asserted FIRST"). -----------------------------------------------------------


def blank_or_short_fields(fields: dict[str, str], *, min_len: int = 10) -> list[str]:
    """Returns names of fields (name -> string value) that are empty,
    whitespace-only, or shorter than `min_len` characters. Same shape as
    resume_analyst's `empty_quote_lists`, case_architect's and planner's
    `blank_or_short_fields` -- story 1.3a's lesson, applied a fourth time:
    an empty string trivially fails every other content assertion by having
    nothing to object to, so silence must be caught here first.
    """
    return [name for name, value in fields.items() if len((value or "").strip()) < min_len]


def grounded_in_is_empty(grounded_in: list[str] | None) -> bool:
    """True iff `grounded_in` is missing or empty. Spec §3/§5: `grounded_in`
    must be non-empty on BOTH branches of `can_answer` -- a refusal still
    rests on the nearest thing the world does say. This is the floor that
    must run BEFORE `missing_grounding`, per the same reasoning as
    planner's `empty_grounded_in`: an empty list has nothing to fail to
    find, so `missing_grounding([], world)` returns `[]` and would pass a
    refusal that grounded itself in nothing at all. `can_answer=False` is
    NOT an exemption from this floor -- that is the escape hatch spec §5
    names explicitly ("a suite that lets can_answer=False skip the content
    checks can be passed by an agent that refuses everything").
    """
    return not grounded_in


# --- grounding: same set-membership shape as planner's `grounded_in` -------


def world_haystack(case_world: dict) -> str:
    """Flattens every string and number in `case_world` into one blob.
    `missing_grounding` and `ungrounded_figures` check substring membership
    against this."""
    parts: list[str] = []

    def _walk(node: object) -> None:
        if isinstance(node, dict):
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for value in node:
                _walk(value)
        elif node is not None:
            parts.append(str(node))

    _walk(case_world)
    return " \n ".join(parts)


def missing_grounding(grounded_in: list[str], case_world: dict) -> list[str]:
    """Returns entries in `grounded_in` that do NOT appear verbatim anywhere
    in `case_world`. Same shape as planner's `missing_grounding` and, per
    spec §3, inherited from the Planner deliberately: it converts "did this
    answer invent something?" from a judgment call into a set-membership
    check.

    Returns [] on an empty `grounded_in` list -- the exact vacuity trap
    `grounded_in_is_empty` exists to catch. Callers MUST run that floor
    first.
    """
    haystack = world_haystack(case_world)
    return [entry for entry in grounded_in if entry not in haystack]


# --- the figure check: this suite's teeth, per spec §5 -----------------------

# Digits, optionally led by `$` and/or trailed by `%`, with `,` or `.` as
# internal separators. Deliberately does NOT capture a trailing unit letter
# ("M", "B", "K") -- "$18.3M" extracts as "$18.3", which is still a valid
# substring check against a world storing "$18.3M" verbatim (spec §5/§6).
_FIGURE_RE = re.compile(r"\$?\d[\d,]*(?:\.\d+)?%?")

# Small ordinals/counts that render as bare digits in fluent prose ("your
# 2nd point", "the 3 options") rather than a figure drawn from case_world.
# Spec §5: "keep it explicit and short ... widening it is the cheapest way
# to destroy it." Deliberately does not include anything above 3 -- past
# that a bare digit is far more likely to be a genuine (and checkable)
# figure than a conversational count.
_ALLOWED_FIGURES = frozenset({"1", "2", "3"})


def figures_in_text(text: str) -> list[str]:
    """Every numeric token in `text`, per `_FIGURE_RE`. Does NOT apply the
    ordinal/count allow-list -- callers decide whether that applies to
    their check (see `ungrounded_figures` vs `contains_any_figure`)."""
    return _FIGURE_RE.findall(text or "")


def _normalize_figure(raw: str) -> str:
    """Strips thousands separators, `$`, and `%` so "41,000" and "41000"
    (an int, dumped by `world_haystack` as a bare digit string) compare
    equal, and so a percentage or dollar figure compares against a world
    value that has neither symbol. Spec §6: "Normalise thousands separators
    before comparing, or 41,000 fails against a stored 41000 and the check
    fires on a CORRECT answer" -- exactly the failure this function exists
    to prevent.
    """
    return raw.replace(",", "").replace("$", "").replace("%", "")


def world_figures(case_world: dict) -> set[str]:
    """Every numeric token in `case_world`, normalised. Half of the
    known-good set `ungrounded_figures` checks against -- see
    `known_figures` for the other half."""
    return {_normalize_figure(f) for f in figures_in_text(world_haystack(case_world))}


def known_figures(case_world: dict, improvised_facts: list[str] | None = None) -> set[str]:
    """`world_figures(case_world)` UNION every numeric token in
    `improvised_facts`, normalised the same way.

    🔴 PHASE-3.5-SPEC.md "THREE DECISIONS" #2: the refusal branch is gone,
    replaced by invent-and-record. `ungrounded_figures` is RETARGETED at
    `case_world ∪ improvised_facts` rather than deleted -- an interview that
    invents "3.4 million weekly active users" and is later asked the same
    thing again must not have that figure flagged as ungrounded the SECOND
    time, or the consistency this design exists to produce would fail its
    own suite's figure check on every replay.
    """
    known = world_figures(case_world)
    for fact in improvised_facts or []:
        known |= {_normalize_figure(f) for f in figures_in_text(fact)}
    return known


def ungrounded_figures(
    answer: str, case_world: dict, improvised_facts: list[str] | None = None
) -> list[str]:
    """Returns every numeric token in `answer` that is not a figure the
    world states OR a figure already improvised this interview.
    AGENT-INTERVIEWER-SPEC.md §5's "assertion with teeth": `grounded_in`
    alone does not catch an invented figure sitting in the sentence beside
    an honestly grounded one.

    `improvised_facts` defaults to `None` (treated as empty) so every
    existing call site -- including the golden suite's fixtures 1/2/4,
    which never improvise -- keeps working unmodified.

    🔴 SET MEMBERSHIP against `known_figures`, deliberately NOT a substring
    search of the flattened world. Measured 2026-08-05, and the substring
    version was written first: "roughly 7 designers" PASSED against a world
    containing no 7, because a single digit is a substring of almost any
    world (187 employees, $2.8B, 76.5%). That hole sat directly on top of
    fixture 3's premise -- a headcount question is exactly where a small
    invented integer appears -- so the check was strongest against the
    figures least likely to be invented and blind to the ones most likely.
    Extracting the world's figures with the same regex and comparing whole
    tokens closes it: "7" now fails, while "187 employees" and "within 8
    seconds" still pass against a world that states them.

    Residual, accepted: a coincidental collision still passes (an invented
    "8" against a world that says "8 seconds"). Same class of mechanical
    imprecision planner's `is_generic_question` accepts for the same reason
    -- cheap, deterministic, and it measures the property that matters.
    """
    known = known_figures(case_world, improvised_facts)
    missing = []
    for figure in figures_in_text(answer):
        if figure in _ALLOWED_FIGURES:
            continue
        if _normalize_figure(figure) in known:
            continue
        missing.append(figure)
    return missing


def contains_any_figure(text: str) -> list[str]:
    """Figures present in `text`, excluding the small ordinal/count
    allow-list. Used for the `can_answer=False` guard (spec §5): a refusal
    must contain NO figure at all, not merely none that fails grounding --
    a refusal that volunteers a real, correctly-grounded number is still
    the failure mode named in spec §7 ("Refuses everything" / a refusal
    that isn't actually a refusal)."""
    return [f for f in figures_in_text(text) if f not in _ALLOWED_FIGURES]


# --- candidate-facing copy hygiene, same shapes as planner's ---------------

_DASH_VARIANTS = ("—", "–")  # em dash, en dash


def no_dash_variants(text: str) -> bool:
    """True iff `text` contains neither an em dash nor an en dash. Applies
    to both `bridge` and `answer` -- spec §4: "This surface is new ...
    prompting has already failed twice to enforce this mechanical rule."""
    return not any(d in (text or "") for d in _DASH_VARIANTS)


# Identical set to planner's and case_architect's -- spec §4: "same set,"
# not a re-derivation. See planner/assertions.py's comment for the regex
# rationale (lookaround, not `\b`, to avoid false-positiving on "19.0%").
_BANNED_ROUND_PERCENT_RE = re.compile(r"(?<![\d.])(?:0|25|50|75|100)(?!\d)\s?%")

_BANNED_NAME_TOKENS = (
    "acme",
    "techcorp",
    "globex",
    "initech",
    "john doe",
    "jane doe",
    "sarah chan",
)


def contains_fake_round_number(text: str) -> str | None:
    """Returns the matched fragment if `text` cites one of the textbook
    banned round percentages, or `None`."""
    match = _BANNED_ROUND_PERCENT_RE.search(text or "")
    return match.group(0) if match else None


def contains_banned_register_name(text: str) -> str | None:
    """Returns the first banned-register token found in `text` (case
    insensitive), or `None`."""
    lowered = (text or "").lower()
    for token in _BANNED_NAME_TOKENS:
        if token in lowered:
            return token
    return None


# --- refusal quality: a refusal must NAME the silence, not merely be short -


# Spec §5: "assert the refusal is a refusal (it names the world's silence)
# rather than merely short." A refusal of e.g. "I'm not able to say." is
# short (would fail the vacuity floor anyway at a low enough min_len) but
# even a LONG non-answer that never says the world is silent is not the
# structured refusal `can_answer=False` promises. Kept short and literal
# rather than semantic, matching this suite's other mechanical proxies.
_SILENCE_PHRASES = (
    "does not specify",
    "doesn't specify",
    "does not say",
    "doesn't say",
    "does not state",
    "doesn't state",
    "does not mention",
    "doesn't mention",
    "does not include",
    "doesn't include",
    "does not provide",
    "doesn't provide",
    "not specified",
    "isn't specified",
    "is not specified",
    "no information",
    "not provided",
    "brief does not",
    "brief doesn't",
    "world does not",
    "case does not",
)


def refusal_names_silence(answer: str) -> bool:
    """True iff `answer` uses language that names the world's silence
    (rather than merely declining to answer)."""
    lowered = (answer or "").lower()
    return any(phrase in lowered for phrase in _SILENCE_PHRASES)
