"""Checkers shared by every golden case. Pure, offline, no LLM, no import of
`app.agents.planner` -- this module must stay importable before that agent
exists, since `test_assertions.py` exercises it at collection time under
`pytest tests -m "not live"`.

Deliberately self-contained rather than importing from
`tests.golden.case_architect.assertions`: the two suites test different
agents and this package must stay independently importable even if the
Case Architect suite's internals change shape. Every function takes
primitives (dicts, lists, strings) -- never a `QuestionPlan` instance --
mirroring both `case_architect/assertions.py` and `resume_analyst/
assertions.py`'s own shape, and for the same reason: they can be exercised
offline against hand-built dicts before the schema they will eventually
check against is even code (AGENT-PLANNER-SPEC.md §2).
"""
from __future__ import annotations

import re

# Story 3.5.2 imports the shape bank -- production data, not a test module --
# so `matches_no_shape` can check a real question against the twelve bank
# shapes rather than reimplementing them here. This is the one exception to
# this file's usual "no import outside this package" rule (see module
# docstring): `app.questions.shapes` has no LLM dependency and no agent
# dependency, so it cannot break this module's "importable before the agent
# exists" guarantee the way `app.agents.planner` would.
from app.questions.shapes import SHAPE_BANK

# --- generic count / vacuity floors -----------------------------------------


def count_out_of_range(items: list, low: int, high: int) -> bool:
    """True iff `len(items)` falls outside `[low, high]`. Used for question
    count (5-7) and, per-question, `probe_angles` (2-3)."""
    return not (low <= len(items) <= high)


def blank_or_short_fields(fields: dict[str, str], *, min_len: int = 10) -> list[str]:
    """Returns names of fields (name -> string value) that are empty,
    whitespace-only, or shorter than `min_len` characters. Direct analogue
    of resume_analyst's `empty_quote_lists` and case_architect's
    `blank_or_short_fields` -- story 1.3a's lesson, applied a third time: an
    empty string trivially fails every other content assertion by having
    nothing to object to, so silence must be caught here first.
    """
    return [name for name, value in fields.items() if len((value or "").strip()) < min_len]


# --- grounding: the whole design, per spec §2 --------------------------------


def world_haystack(case_world: dict) -> str:
    """Flattens every string and number in `case_world` into one blob.
    `missing_grounding` checks substring membership against this, the same
    shape as resume_analyst's verbatim-quote check against resume text --
    except the known-good source here is the case world, not a resume.
    """
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
    in `case_world`. Spec §2/§7: a fabricated `grounded_in` entry (an
    entity the world does not contain) must be mechanically detectable --
    the same shape as the Resume Analyst's `missing_verbatim_quotes`, and
    per the spec, the whole reason this schema field exists.

    Returns [] on an empty `grounded_in` list -- this is the exact vacuity
    trap named in spec §5/§7 and CLAUDE.md's "Named trap 1.3a": nothing to
    check means nothing can fail. Callers MUST pair this with
    `empty_grounded_in` (or an equivalent non-empty check) run first.
    """
    haystack = world_haystack(case_world)
    return [entry for entry in grounded_in if entry not in haystack]


def empty_grounded_in(questions: list[dict]) -> list[int]:
    """Returns the `idx` of every question whose `grounded_in` list is
    empty or missing. The floor beneath `missing_grounding`: a question
    with nothing in `grounded_in` passes the membership check vacuously,
    so this must be asserted separately and BEFORE that check runs.
    """
    return [q["idx"] for q in questions if not q.get("grounded_in")]


# --- rubric coverage -----------------------------------------------------------

# PRD.md §7's five dimensions, cross-referenced (not restated as prose) --
# matches AGENT-PLANNER-SPEC.md §2's RUBRIC_DIMENSIONS Literal exactly.
RUBRIC_DIMENSIONS: frozenset[str] = frozenset(
    {
        "business_model_fluency",
        "market_accuracy",
        "decision_quality",
        "structural_clarity",
        "point_of_view",
    }
)


def missing_dimension_coverage(questions: list[dict]) -> set[str]:
    """Returns rubric dimensions with no question naming them as
    `primary_dimension`. Spec §3: every dimension must be covered at least
    once or the Evaluator has nothing to score it on."""
    covered = {q.get("primary_dimension") for q in questions}
    return set(RUBRIC_DIMENSIONS) - covered


# --- structural bounds -------------------------------------------------------


def probe_angle_violations(questions: list[dict]) -> list[int]:
    """Returns `idx` of questions whose `probe_angles` count is not 2-3."""
    return [q["idx"] for q in questions if count_out_of_range(q.get("probe_angles", []), 2, 3)]


def total_minutes_mismatch(total_minutes: int, questions: list[dict]) -> bool:
    """True iff `total_minutes` exceeds the 45-minute interview (PRD §1),
    or does not equal the sum of per-question `minutes`. Spec §5's positive
    control: a plan claiming 30 whose questions sum to 70.
    """
    summed = sum(q.get("minutes", 0) for q in questions)
    return total_minutes > 45 or total_minutes != summed


# --- candidate-facing copy hygiene -------------------------------------------

_DASH_VARIANTS = ("—", "–")  # em dash, en dash


def no_dash_variants(text: str) -> bool:
    """True iff `text` contains neither an em dash nor an en dash. Questions
    are asked verbatim (PRD §8), so this is candidate-facing copy under the
    same CLAUDE.md em-dash ban as everywhere else in the product."""
    return not any(d in text for d in _DASH_VARIANTS)


# Same small explicit set as the Case Architect's, deliberately not a
# blanket round-number ban: "20% of customers" is a legitimate figure and
# must not be flagged (spec §4, mirroring AGENT-CASE-ARCHITECT-SPEC.md §8).
#
# Lookbehind/lookahead, not `\b`: `\b0%` false-positives on the tail of an
# organic decimal like "19.0%" -- "." is a non-word character, so `\b` sees
# a boundary right before the "0" and matches it as if it were the banned
# standalone figure. `(?<![\d.])` refuses to start a match with a digit or
# `.` immediately before it; `(?!\d)` refuses one with a digit immediately
# after (so "100" inside "1000%" cannot match as "0" or "0" + trailing).
# Found writing this suite's own fixtures -- "19.0%" was a real question
# string that tripped the naive version.
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
    banned round percentages, or `None`. Positive control (spec §5): a
    question citing "roughly 50% of users" or "50% of customers"."""
    match = _BANNED_ROUND_PERCENT_RE.search(text)
    return match.group(0) if match else None


def contains_banned_register_name(text: str) -> str | None:
    """Returns the first banned-register token found in `text` (case
    insensitive), or `None`. Same register CLAUDE.md / the Case Architect
    spec bans outright."""
    lowered = text.lower()
    for token in _BANNED_NAME_TOKENS:
        if token in lowered:
            return token
    return None


# --- genericness: the hard one, per spec §5 -----------------------------------


def world_specific_terms(case_world: dict) -> list[str]:
    """Proper nouns and figures a question grounded in THIS world could
    plausibly cite: the company name (full, or its distinctive first word),
    every competitor name, and every numeric metric/market figure. Spec §5's
    own mechanical approximation of
    "specific to this world" -- explicitly not perfect (a coincidental
    number match is possible), but cheap, deterministic, and directly
    measures the property that matters, which is the spec's own
    justification for choosing it over a semantic check.
    """
    company = case_world["company"]
    market = case_world["market"]
    metrics = case_world["metrics"]

    names = [company["name"]] + [c["name"] for c in market["competitors"]]

    # Also accept the DISTINCTIVE FIRST WORD of each two-word name, not just
    # the full string. Observed 2026-08-04: `deep` produced "what are the key
    # strengths and weaknesses of Ferngrove's business model?" against a world
    # whose company is "Ferngrove Media". That question is unambiguously about
    # this world and the full-string check called it generic -- the check was
    # under-measuring, not the model under-specifying. Real interviewers use
    # the short form and the possessive, so requiring the legal two-word name
    # verbatim measures formatting, not specificity.
    #
    # Length floor because the Case Architect is told to give every company a
    # two-word name and the first word is normally a coined proper noun
    # ("Verdant", "Northline"); a short one ("The", "Blue") would match common
    # prose and make this check pass vacuously, which is the failure this
    # suite exists to prevent.
    first_words = [n.split()[0] for n in names if n and len(n.split()) > 1]

    terms = names + [w for w in first_words if len(w) >= 4 and w.isalpha()]
    terms += [
        market["size_usd"],
        str(market["growth_rate_pct"]),
        metrics["arr_usd"],
        str(metrics["yoy_growth_pct"]),
        str(metrics["gross_margin_pct"]),
        str(metrics["monthly_churn_pct"]),
        str(metrics["customer_count"]),
    ]
    return [t for t in terms if t]


def is_generic_question(question: str, case_world: dict) -> bool:
    """True iff `question` contains NONE of the world's proper nouns or
    figures -- the mechanical genericness check, spec §5. A question that
    names no company, competitor, or number in this world could be pasted
    into any other case world unchanged, which is the failure mode spec §5
    calls "the failure most likely to ship, because it looks fine in
    isolation."
    """
    return not any(term in question for term in world_specific_terms(case_world))


# ==============================================================================
# Story 3.5.2 -- three new checks, widened BEFORE the Planner's prompt
# changes (PHASE-3.5-SPEC.md's trap table: "widen the assertion BEFORE
# changing the prompt", the ordering that worked in 3.1 and 2.5). All three
# are checked against the honest corpus: the three questions this product
# actually served on 2026-08-05, recorded verbatim in DEV-STATE.md
# § Decisions 2026-08-05. See `test_assertions.py` for the Q1/Q2/Q3 table
# and the proof that this suite is RED against them today.
# ==============================================================================


# --- decorative_statistic ----------------------------------------------------
#
# CORRECTED 2026-08-06: the first version matched exactly two catalogued
# shapes ("$X market size" and "X% growth"). Independent re-verification
# found it blind to every other figure the curated worlds actually carry --
# `customer_count`, `arr_usd`, `monthly_churn_pct` -- which is precisely
# where the defect ships next wearing a different field name.
#
# Reimplemented on the deletion test the spec itself describes: "a question
# that still parses the same with its leading statistic clause deleted is a
# question whose statistic did no work." A clause qualifies when it (a) is
# introduced by `given`, `considering`, `with`, `at`, or `despite`, (b)
# contains a figure of ANY kind -- currency, percent, a comma-grouped
# integer, or a bare number followed by a scale word -- before the next
# comma/terminator, and (c) can be deleted while leaving a standalone
# question behind. (c) is why Q3 stays silent: "Given Nimbus Capital's
# constraints," is a leading clause with the right introducer but NO figure
# in it, so (b) never matches and the clause is never even considered.
_FIGURE_RE = (
    r"(?:\$[\d,.]+\s?[kKmMbB]?\b"  # currency: $247M, $12.3B, $4.7M
    r"|\d{1,3}(?:,\d{3})+(?:\.\d+)?\b"  # comma-grouped integer: 8,400 / 1,234,567
    r"|\d+(?:\.\d+)?\s?%"  # percent: 31.4%, 3.7%
    r"|\d+(?:\.\d+)?\s?(?:million|billion|thousand|[kKmMbB])\b)"  # bare number + scale word
)

# The clause runs from the introducer word, through non-terminating
# characters, to wherever a qualifying figure is found, and then continues
# (still non-terminating) up to the next comma/`?`/`!`/`.`/end-of-string --
# covers BOTH a leading clause set off by a trailing comma (the reviewer's
# "Given Reddit's 97.2 million daily actives, ...") and a trailing clause
# that runs to the question mark with no comma at all (Q1's actual shape:
# "... revenue model given the $12.3B market size ... last year?").
_STATISTIC_CLAUSE_RE = re.compile(
    rf"\b(?:given|considering|with|at|despite)\b[^,?!.]*?{_FIGURE_RE}[^,?!.]*?(?=,|\?|!|\.|$)",
    re.IGNORECASE,
)


def _clause_deletion_leaves_a_standalone_question(question: str, clause: str) -> bool:
    """The spec's own deletion test, applied literally rather than assumed:
    delete `clause` from `question` and require what remains to still read
    as a complete, standalone question. Collapses the comma/whitespace
    debris the deletion leaves behind first -- "X, Y?" minus "X" should
    read as "Y?", not ", Y?" -- then requires the remainder still ends in
    "?" and still has enough words to be a real question, not a fragment.
    """
    remainder = question.replace(clause, "", 1)
    remainder = re.sub(r"\s*,\s*", " ", remainder)
    remainder = re.sub(r"\s+", " ", remainder).strip()
    return remainder.endswith("?") and len(remainder.split()) >= 4


def decorative_statistic(question: str) -> str | None:
    """Returns the offending clause -- a `given`/`considering`/`with`/`at`/
    `despite` clause carrying a figure of any kind that the rest of the
    question does not need -- or `None` if none is present.

    Tries every candidate clause left to right (`finditer`, not just the
    first `search` hit) and returns the first one that also passes the
    deletion test, so a false structural match earlier in the sentence
    cannot hide a real one later in it.

    Known trade-off, inherent to a mechanical proxy rather than a semantic
    read (same shape as `is_generic_question`'s own documented limitation):
    a question where the introducer clause names the actual subject under
    discussion, not a decorative fact ("How would you price this at $49 a
    month?"), can still fire. The five introducer words and "any figure"
    are deliberately broad per this story's brief; a false positive here is
    the cost of not missing the real defect (a stapled market size or
    growth rate wearing a different field's number).

    Returns `None` on an empty or missing `question` -- correct behavior
    (there is no statistic in nothing), NOT a vacuity trap the way an empty
    `grounded_in` list is: this function is a denial check, not a
    membership check, so silence here means "no violation found," which
    must be paired with `blank_or_short_fields` (already in this module) to
    catch an empty question in the first place. See `test_assertions.py`'s
    vacuity-floor test for the explicit demonstration.
    """
    text = question or ""
    for match in _STATISTIC_CLAUSE_RE.finditer(text):
        clause = match.group(0)
        if _clause_deletion_leaves_a_standalone_question(text, clause):
            return clause
    return None


# --- matches_no_shape ----------------------------------------------------------


def _shape_to_pattern(template: str) -> re.Pattern[str]:
    """Compiles a bank `template` (a `str.format()` string) into a regex that
    matches the template with every `{slot}` filled by ANY non-empty text --
    literal segments are escaped, each placeholder becomes a non-greedy
    `.+?` capture. An empty fill (`{slot}` replaced by nothing) does not
    match `.+?`, which requires at least one character, so a template with
    a slot left blank is correctly NOT a filled shape.
    """
    parts: list[str] = []
    last_end = 0
    for m in re.finditer(r"\{(\w+)\}", template):
        parts.append(re.escape(template[last_end : m.start()]))
        parts.append(r".+?")
        last_end = m.end()
    parts.append(re.escape(template[last_end:]))
    return re.compile("".join(parts), re.IGNORECASE)


_SHAPE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    _shape_to_pattern(shape.template) for shape in SHAPE_BANK
)


def matches_no_shape(question: str) -> bool:
    """True iff `question` conforms to NONE of the twelve bank shapes
    (`app.questions.shapes.SHAPE_BANK`) with their slots filled.

    Vacuity floor: an empty or whitespace-only `question` conforms to
    nothing and returns True (not vacuously False) -- there is no shape a
    blank string "matches" by default. Positive control (see
    `test_assertions.py`): a question built by literally filling one of the
    bank's own templates must return False, proving this function can
    accept, not just reject.
    """
    text = (question or "").strip()
    if not text:
        return True
    return not any(pattern.fullmatch(text) for pattern in _SHAPE_PATTERNS)


# --- is_recitation_shaped -------------------------------------------------------
#
# CORRECTED 2026-08-06: the first version of this check matched the literal
# string "how does ... support ... given", which fired on Q1 verbatim and on
# NOTHING else -- a question using any other explanatory verb ("drive",
# "contribute", "influence"...) sailed through green while carrying the
# exact defect this check exists to catch. Independent re-verification
# caught it with six counter-examples (see `test_assertions.py`).
#
# Reimplemented on the PROPERTY the spec actually names, not the phrasing of
# one example: a question is recitation-shaped when it (1) uses an
# explanatory frame that only asks how the world's own facts relate to each
# other, AND (2) never turns to the candidate ("you"/"your"), AND (3) never
# asks for a decision, a choice, or a trade-off. All three conditions must
# hold -- an explanatory frame that also asks the candidate to decide
# something (Q2's "your go-to-market strategy", Q3's "would you prioritize")
# is not this failure mode, because answering it requires judgment, not
# recitation.
_EXPLANATORY_FRAME_RE = re.compile(
    r"\b(?:how does|how do|what role does|in what way does|walk me through how|why does)\b",
    re.IGNORECASE,
)

_SECOND_PERSON_RE = re.compile(r"\b(?:you|your)\b", re.IGNORECASE)

_DECISION_VERB_RE = re.compile(
    r"\b(?:should|would you|which|prioritize|choose|recommend|trade-off)\b",
    re.IGNORECASE,
)


def is_recitation_shaped(question: str) -> bool:
    """True iff `question` opens an explanatory frame ("how does X relate to
    Y") and never asks the candidate for a decision -- answerable by
    reciting facts the case world already states, rather than by exercising
    judgment. False if the question contains no explanatory frame at all,
    turns to the candidate directly (`you`/`your`), or contains a decision
    verb (`should`, `would you`, `which`, `prioritize`, `choose`,
    `recommend`, `trade-off`) -- any one of those three is sufficient to
    clear it, matching the spec's "answerable by summarizing the case back
    rather than exercising judgment" definition.

    Returns False on an empty or missing `question` (no frame to match),
    the same non-vacuous-in-context reasoning as `decorative_statistic`:
    this is a denial check paired with `blank_or_short_fields`, not a
    membership check that silence could satisfy vacuously.
    """
    text = question or ""
    if not _EXPLANATORY_FRAME_RE.search(text):
        return False
    if _SECOND_PERSON_RE.search(text):
        return False
    if _DECISION_VERB_RE.search(text):
        return False
    return True
