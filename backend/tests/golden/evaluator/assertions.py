"""Checkers for the Evaluator golden suite. Pure, offline, no LLM, no import
of an `evaluate_answer` function that does not exist yet (story 4.2) -- this
module must stay importable at collection time by both `test_golden.py` and
the fully offline `test_assertions.py`, under `pytest tests -m "not live"`.

Deliberately DOES import `app.agents.evaluator` -- unlike the interviewer and
case_architect golden suites' equivalents, which avoid importing their
agent's schema because the schema itself did not exist at story-1 time. Here
the schema IS story 4.1's own deliverable (`AnswerEvaluation`,
`DimensionScore`), so importing it is safe and correct; only the FUNCTION
(`evaluate_answer`) does not exist, and only `test_golden.py`'s lazy,
inside-a-fixture import touches that name -- see that module's docstring.

Every function here takes primitives (dicts, lists, strings), never an
`AnswerEvaluation` instance directly -- same reasoning as every other golden
suite in this product: a checker exercised against hand-built dicts today
must keep working unmodified once story 4.2's `evaluate_answer` returns real
`AnswerEvaluation` objects, at which point `test_golden.py` converts
`result.model_dump()` before calling these.
"""
from __future__ import annotations

from app.agents.planner import RUBRIC_DIMENSIONS

# --- vacuity floor -- must run FIRST, before anything it could hide behind,
# same ordering rule as interviewer's and planner's assertions.py. -----------


def blank_or_short_fields(fields: dict[str, str], *, min_len: int = 10) -> list[str]:
    """Returns names of fields (name -> string value) that are empty,
    whitespace-only, or shorter than `min_len` characters. Same shape as
    every other golden suite's identically-named function -- story 1.3a's
    lesson, applied a fifth time: an empty string trivially passes every
    other content assertion by having nothing to object to, so silence must
    be caught here first, before the verbatim-quote check below (which would
    happily report "" as "not found" for the wrong reason -- a blank quote
    is a vacuity failure, not a fabrication one).
    """
    return [name for name, value in fields.items() if len((value or "").strip()) < min_len]


# --- the verbatim-quote check: THIS suite's teeth, per the brief's item 4 --


def transcript_haystack(transcript_turns: list[dict]) -> str:
    """Flattens every turn's text into one blob, in transcript order.
    `quotes_not_found_verbatim` checks EXACT substring membership against
    this -- same "flatten, then substring-check" shape as
    `interviewer/assertions.py`'s `world_haystack`, applied to a transcript
    instead of a case_world.

    Reads `content` (the DB column name, `transcript_turns.content`) with a
    fallback to `text` (the in-graph turn shape `interviewer.py`'s
    `_render_transcript` uses) so this function accepts either representation
    without the caller normalising first.
    """
    parts = [str(turn.get("content") if turn.get("content") is not None else turn.get("text", "")) for turn in transcript_turns]
    return "\n".join(parts)


def quotes_not_found_verbatim(dimension_scores: list[dict], transcript_turns: list[dict]) -> list[str]:
    """Returns the `dimension` of every entry in `dimension_scores` whose
    `evidence_quote` is NOT an exact substring of the flattened transcript.

    🔴 EXACT SUBSTRING, deliberately not fuzzy or semantic matching -- PRD
    §8's "every score carries a verbatim quote" is falsifiable only if
    "verbatim" means byte-for-byte. See `test_assertions.py`'s falsification
    test: a hand-written evaluation whose quote has ONE word changed from
    the real transcript sentence is proven to fail here, or this check would
    be decorative -- the same class of bug `interviewer/assertions.py`'s
    `ungrounded_figures` docstring records for its own first (too-loose)
    version.

    Returns [] on an empty `dimension_scores` list -- there is nothing to
    fail to find. That is `not_assessed`'s job to require, not this
    function's; a caller must run `blank_or_short_fields` (or equivalent) on
    every quote FIRST, same ordering rule as `grounded_in_is_empty` /
    `missing_grounding` in the interviewer and planner suites.
    """
    haystack = transcript_haystack(transcript_turns)
    return [
        ds["dimension"]
        for ds in dimension_scores
        if (ds.get("evidence_quote") or "") not in haystack
    ]


# --- not_assessed coherence -- PHASE-4-SPEC.md #1's hardest problem --------


def not_assessed_carries_a_score(dimension_scores: list[dict], not_assessed: list[str]) -> list[str]:
    """Returns dimensions present in BOTH `dimension_scores` and
    `not_assessed` -- the exact defect the brief names: "a dimension in
    not_assessed carries no score." Sorted so a failure message is
    deterministic across runs.

    This is the mechanical, dict-level twin of the pydantic model_validator
    on `AnswerEvaluation` itself (`app/agents/evaluator.py`) -- kept as its
    own function (not merely "trust the schema") because a caller working
    with `.model_dump()`'d state (the graph's own representation once story
    4.3 writes it) or a hand-built dict fixture has no pydantic validation
    running at all; this is what still catches it there.
    """
    scored = {ds["dimension"] for ds in dimension_scores}
    return sorted(scored & set(not_assessed))


def dimensions_unaccounted_for(dimension_scores: list[dict], not_assessed: list[str]) -> set[str]:
    """Dimensions that are neither scored nor listed in `not_assessed` --
    the silent-drop failure mode `app/agents/evaluator.py`'s module docstring
    names. An aggregate built from the surviving dimensions would misreport
    itself as complete if this ever fires."""
    scored = {ds["dimension"] for ds in dimension_scores}
    accounted = scored | set(not_assessed)
    return set(RUBRIC_DIMENSIONS) - accounted


def duplicate_dimensions(dimension_scores: list[dict]) -> list[str]:
    """Dimensions scored more than once. Each of the five is scored at most
    once -- a duplicate is either a double-count in an aggregate or a sign
    the model filled the same slot twice instead of covering the ladder."""
    seen: set[str] = set()
    dupes: list[str] = []
    for ds in dimension_scores:
        d = ds["dimension"]
        if d in seen:
            dupes.append(d)
        seen.add(d)
    return dupes


def score_out_of_range(dimension_scores: list[dict]) -> list[str]:
    """Dimensions whose `score` is not an integer in [1, 4]. Redundant with
    `DimensionScore`'s own `Field(ge=1, le=4)` for a real pydantic instance,
    kept here for the same reason as `not_assessed_carries_a_score`: this
    suite also exercises hand-built dicts that never pass through pydantic
    at all."""
    return [ds["dimension"] for ds in dimension_scores if not (1 <= ds.get("score", 0) <= 4)]


# --- level anchors -- PRD §7: "anchors shift with assessed_level; the
# dimensions do not." ---------------------------------------------------------


def scored_lower_at_higher_level(
    lower_level_scores: dict[str, int], higher_level_scores: dict[str, int]
) -> list[str]:
    """Returns dimensions where the SAME answer did NOT score strictly lower
    at the higher `assessed_level` -- a violation of PRD §7's anchor-shift
    rule (a Hire-bar answer at APM should read as a No-Hire-bar answer at
    GPM; the rubric dimensions stay fixed, the bar behind each number moves).

    Only compares dimensions present in BOTH maps -- a dimension `not_assessed`
    at one level and scored at the other has nothing to compare, and that
    mismatch is `not_assessed`'s own concern, not this function's.

    Positive control (brief's own naming pattern): the SAME score at both
    levels is a violation too, not just a higher score at the higher level --
    "the same answer scores lower," not "no worse."
    """
    violations = []
    for dim, hi_score in higher_level_scores.items():
        lo_score = lower_level_scores.get(dim)
        if lo_score is None:
            continue
        if not (hi_score < lo_score):
            violations.append(dim)
    return violations
