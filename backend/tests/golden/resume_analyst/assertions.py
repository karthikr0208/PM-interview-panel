"""Checkers shared by every golden case. Pure, offline, no LLM, no import of
`app.agents.resume_analyst` -- this module must stay importable before that
agent exists, since `test_assertions.py` exercises it at collection time
under `pytest tests -m "not live"`.

Every comparison routes through `normalize_for_comparison`: `pypdf` /
`python-docx` extraction (story 1.2) produces irregular runs of whitespace,
newlines, and non-breaking spaces that a naive `in` check would treat as a
mismatch even when the underlying words are identical, and the model emits
typographic variants of ASCII punctuation for the same reason.
"""
from __future__ import annotations

import re

EM_DASH = "—"
EN_DASH = "–"

_WHITESPACE_RE = re.compile(r"\s+")

# Typographic variants that carry no content: the same character, rendered
# differently. Folded before any verbatim comparison because the fixtures are
# pure ASCII while the model is not -- gpt-oss-120b reproduced 42 words of
# fixture 08 exactly and substituted U+2011 for the two ASCII hyphens in
# "hard-coded" / "built-in", which `missing_verbatim_quotes` then reported as a
# fabricated quote. Measured 2026-08-01: 2 differing codepoints out of 233,
# both hyphens. See DEV-STATE § Decisions 2026-08-01.
#
# EM_DASH and EN_DASH are deliberately ABSENT. They are distinct punctuation
# rather than variants of the hyphen, and this project bans them in candidate-
# facing copy -- folding them would let a quote introduce a banned character
# and still read as verbatim.
_TYPOGRAPHIC = {
    "‐": "-",  # HYPHEN
    "‑": "-",  # NON-BREAKING HYPHEN
    "‘": "'",  # LEFT SINGLE QUOTATION MARK
    "’": "'",  # RIGHT SINGLE QUOTATION MARK
    "“": '"',  # LEFT DOUBLE QUOTATION MARK
    "”": '"',  # RIGHT DOUBLE QUOTATION MARK
}


def normalize_whitespace(text: str) -> str:
    """Collapse all whitespace runs to a single space and strip."""
    return _WHITESPACE_RE.sub(" ", text).strip()


def fold_typography(text: str) -> str:
    """Map typographic punctuation variants onto their ASCII equivalents.
    Content-neutral by construction: every entry in `_TYPOGRAPHIC` is a
    rendering of the character it maps to, never a different one."""
    return "".join(_TYPOGRAPHIC.get(ch, ch) for ch in text)


def normalize_for_comparison(text: str) -> str:
    """The one normalization helper every verbatim comparison routes through:
    typography folded, whitespace collapsed, stripped. Case is NOT folded --
    callers decide, and `missing_verbatim_quotes` deliberately does not."""
    return normalize_whitespace(fold_typography(text))


def _words(text: str) -> list[str]:
    normalized = normalize_for_comparison(text)
    return normalized.split(" ") if normalized else []


def eight_word_windows(source: str, min_words: int = 8) -> list[str]:
    """Every contiguous run of `min_words` (or more, exactly `min_words` at a
    time -- overlapping windows, not growing ones) words in `source`, as
    space-joined strings. Case preserved deliberately; callers decide folding.

    Returns `[]` when `source` has fewer than `min_words` words, rather than
    raising -- a resume fixture that short would be a fixture-authoring bug,
    not something this helper should paper over with a shorter window.
    """
    words = _words(source)
    if len(words) < min_words:
        return []
    return [" ".join(words[i : i + min_words]) for i in range(len(words) - min_words + 1)]


def rationale_cites_resume(rationale: str, resume_text: str, min_words: int = 8) -> bool:
    """True iff `rationale` contains, verbatim, at least one run of
    `min_words` consecutive words taken from `resume_text`.

    Case-INSENSITIVE, deliberately: a rationale routinely opens a sentence
    with the same clause the resume used mid-sentence ("Owned..." vs
    "...owned..."), and the property this assertion protects is "quotes real
    content", not "preserves the resume's original capitalization". Contrast
    with `missing_verbatim_quotes` below, which is case-sensitive because
    `scope_evidence` / `notable_outcomes` are specified as verbatim quotes,
    not paraphrase, and folding case there would let a fabricated
    recapitalization of a real phrase pass as genuine.
    """
    haystack = normalize_for_comparison(rationale).lower()
    return any(window.lower() in haystack for window in eight_word_windows(resume_text, min_words))


def missing_verbatim_quotes(quotes: list[str], source: str) -> list[str]:
    """Returns the subset of `quotes` that do NOT appear verbatim
    (whitespace- and typography-normalized, case-sensitive) in `source`. An
    empty return means every quote is honest -- this is the check the spec
    calls "the single most important assertion in the file": a fabricated
    quote in `scope_evidence` or `notable_outcomes` must fail the case.
    """
    normalized_source = normalize_for_comparison(source)
    return [q for q in quotes if normalize_for_comparison(q) not in normalized_source]


def empty_quote_lists(
    scope_evidence: list[str], notable_outcomes: list[str], *, expect_outcomes: bool
) -> list[str]:
    """Names the quote lists that came back empty when they should not have.

    The floor beneath `missing_verbatim_quotes`, and it is load-bearing:
    `missing_verbatim_quotes([])` returns `[]`, so an agent that quotes
    NOTHING passes the spec's "single most important assertion" vacuously,
    on every case at once. Verified 2026-07-31 with a from-scratch probe --
    a result carrying `scope_evidence=[]` and `notable_outcomes=[]` passed
    all eight cases' universal assertions. Silence must not beat effort.

    Same shape as story 1.1's `A/own = 1` column: a denial assertion needs a
    positive control or it passes when the mechanism under test is dead.

    `scope_evidence` has no exception -- all eight fixtures describe ownership
    scope, so an empty list is always a failure to do the work. `notable_
    outcomes` is conditional, because fixture 07 states zero results and an
    empty list there is the honest answer the case exists to check.
    """
    empty = []
    if not scope_evidence:
        empty.append("scope_evidence")
    if expect_outcomes and not notable_outcomes:
        empty.append("notable_outcomes")
    return empty


def no_dash_variants(text: str) -> bool:
    """True iff `text` contains neither an em-dash nor an en-dash."""
    return EM_DASH not in text and EN_DASH not in text


def contains_forbidden_token(text: str, tokens: list[str]) -> str | None:
    """Returns the first forbidden token (name / university / nationality
    detail) found in `text`, case-insensitive substring match, or `None` if
    none leaked. Case-insensitive because a rationale might re-case a name
    at a sentence boundary the same way it might re-case a resume clause --
    the leak is just as real either way.
    """
    lowered = text.lower()
    for token in tokens:
        if token.lower() in lowered:
            return token
    return None
