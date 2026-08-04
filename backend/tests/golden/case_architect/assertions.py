"""Checkers shared by every golden case. Pure, offline, no LLM, no import of
`app.agents.case_architect` -- this module must stay importable before that
agent exists, since `test_assertions.py` exercises it at collection time
under `pytest tests -m "not live"`.

Every function here takes primitives (strings, floats, dicts of those) --
never a `CaseWorld` instance -- mirroring `resume_analyst/assertions.py`'s
own shape. `test_golden.py` is the only place that touches the real result
object; these checkers stay ignorant of it so they can be exercised offline
against hand-built dicts before the schema they will eventually check
against is even code.
"""
from __future__ import annotations

import re

# --- generic count / vacuity floors -----------------------------------------


def count_out_of_range(items: list, low: int, high: int) -> bool:
    """True iff `len(items)` falls outside `[low, high]`. Used for
    `supporting_facts` (8-15), `competitors` (2-4), and `options` (2-3) --
    same shape, different bounds, so one function instead of three."""
    return not (low <= len(items) <= high)


def blank_or_short_fields(fields: dict[str, str], *, min_len: int = 10) -> list[str]:
    """Returns names of fields in `fields` (name -> string value) that are
    empty, whitespace-only, or shorter than `min_len` characters.

    The floor beneath every other string-content assertion in this suite --
    direct analogue of resume_analyst's `empty_quote_lists` and the same
    lesson (story 1.3a): an empty string trivially contains no fake-round
    number and no banned name, so without this floor a `case_world` of ""
    fields would sail through the whole battery by having nothing to object
    to. Silence must not beat effort here either.
    """
    return [name for name, value in fields.items() if len(value.strip()) < min_len]


# --- fake-round numbers -------------------------------------------------------

# Deliberately small and explicit, not a blanket "reject every round number"
# regex. Spec §8 is specific about why: 20.0% is a legitimate gross margin
# and must not be flagged, while 50.0% and 100.0% are the textbook AI tells.
# Multiples of 25 draws that line without banning ordinary organic values --
# 10, 20, 30, 31.4, 18.2 all pass; 0, 25, 50, 75, 100 do not.
_BANNED_ROUND_PERCENTAGES = frozenset({0.0, 25.0, 50.0, 75.0, 100.0})

_DOLLAR_MANTISSA_RE = re.compile(r"^[\d,]+(\.\d+)?$")


def is_round_dollar_amount(value: str) -> bool:
    """True iff `value` (e.g. "$4.7M", "$1M", "$1,000,000") is a
    suspiciously round dollar figure: its numeric mantissa carries no
    decimal point. "$1M" and "$1,000,000" are the tells named in spec §4;
    "$4.7M" and "$3.2B" are organic and pass.
    """
    mantissa = value.strip().lstrip("$")
    if mantissa and mantissa[-1] in "MBKmbk":
        mantissa = mantissa[:-1]
    if not _DOLLAR_MANTISSA_RE.match(mantissa):
        raise ValueError(f"not a recognisable dollar amount: {value!r}")
    return "." not in mantissa


def banned_round_numbers(
    percentages: dict[str, float], dollar_amounts: dict[str, str]
) -> list[str]:
    """Returns "field=value" strings for every percentage in the small
    banned set, or every dollar amount with no decimal in its mantissa.
    Empty means the world is free of the textbook AI tells this exists to
    catch -- it does NOT mean the world is organic overall; see
    `organic_ratio_below_floor` for the complementary check.
    """
    violations = []
    for field, pct in percentages.items():
        if pct in _BANNED_ROUND_PERCENTAGES:
            violations.append(f"{field}={pct}")
    for field, amount in dollar_amounts.items():
        # An unparseable amount is an agent defect, not a harness one, and it
        # must SAY so. `arr_usd` and `size_usd` are deliberately absent from
        # test_golden's vacuity-floor field list (they are figures, not prose),
        # so "", "N/A" and "$18.6 million" reach this line unguarded and the
        # raw ValueError from is_round_dollar_amount reads as a broken test.
        # The case still fails either way; this only decides whether the next
        # person fixes the prompt or "fixes" the assertion. On this project a
        # confusing red has twice been the thing that got tuned away.
        try:
            if is_round_dollar_amount(amount):
                violations.append(f"{field}={amount}")
        except ValueError:
            violations.append(f"{field}={amount!r} is not a parseable dollar amount")
    return violations


def organic_ratio_below_floor(percentages: dict[str, float], min_ratio: float = 0.6) -> bool:
    """True iff FEWER than `min_ratio` of `percentages` carry a non-zero
    fractional part. Complements `banned_round_numbers` rather than
    duplicating it: a world of 10.0%, 30.0%, 90.0% churn/growth/margin hits
    no individual banned value, yet reads exactly as fabricated as a lone
    50.0% would, because organic figures are round only by coincidence, not
    in aggregate. Vacuously True (fails) on an empty dict -- a world with no
    percentages to check has not earned a pass.
    """
    if not percentages:
        return True
    organic = sum(1 for v in percentages.values() if v % 1 != 0)
    return (organic / len(percentages)) < min_ratio


# --- banned-register names ----------------------------------------------------

# Small and explicit, matching the register CLAUDE.md / v1 §7 name outright.
# Not a heuristic ("looks generic") -- a substring match against names this
# project has specifically banned, so it cannot drift into false positives
# against a genuinely organic name that merely sounds plain.
_BANNED_NAME_TOKENS = (
    "acme",
    "techcorp",
    "globex",
    "initech",
    "john doe",
    "jane doe",
    "sarah chan",
)


def contains_banned_register_name(*names: str) -> str | None:
    """Returns the first of `names` matching the banned generic-placeholder
    register (case-insensitive substring), or `None` if none leaked.
    """
    for name in names:
        lowered = name.lower()
        if any(token in lowered for token in _BANNED_NAME_TOKENS):
            return name
    return None


# Algebra-placeholder register: "the feature X", "Product A", "Company B".
# Distinct from _BANNED_NAME_TOKENS, which is a fixed substring list for
# named entities -- these need a word boundary, because a bare "X" or "A"
# substring-matches almost everything. Added 2026-08-04 after a live run put
# "The feature X would increase onboarding completion by 3.1%" into
# supporting_facts, which is candidate-facing copy. The prompt's own APM
# example ("Should we build X into the onboarding flow?") was the source.
# The noun is case-insensitive ("Product A" and "the product A" both count)
# but the placeholder letter must be a capital -- that asymmetry is why the
# whole pattern cannot just take re.IGNORECASE.
_PLACEHOLDER_PATTERN = re.compile(
    r"\b(?:[Ff]eature|[Pp]roduct|[Cc]ompany|[Cc]ompetitor|[Tt]eam|[Mm]etric|[Oo]ption)"
    r"\s+[A-Z]\b"
)


def contains_placeholder_token(*texts: str) -> str | None:
    """Returns the first of `texts` containing an algebra placeholder
    ("feature X", "Product A"), or `None` if none leaked. Case-sensitive on
    the letter deliberately: "feature x" in lowercase prose is nearly always
    a real sentence, while a capital standing alone is the placeholder tell.
    """
    for text in texts:
        if _PLACEHOLDER_PATTERN.search(text):
            return text
    return None


# --- internal consistency -----------------------------------------------------

_MULTIPLIERS = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}


def parse_dollar_amount(value: str) -> float:
    """Parses a formatted dollar string ("$4.7M", "$3.2B", "$1,000,000")
    into a float. Raises `ValueError` on input this suite's fixtures should
    never produce -- fail loud rather than silently returning 0.0 and
    passing every consistency check that depends on it vacuously.
    """
    text = value.strip().lstrip("$").replace(",", "")
    multiplier = 1
    if text and text[-1].upper() in _MULTIPLIERS:
        multiplier = _MULTIPLIERS[text[-1].upper()]
        text = text[:-1]
    return float(text) * multiplier


# Deliberately wide and overlapping, not tight boundaries -- spec §5 says
# start with the two cheapest consistency checks and warns that an
# over-strict check gets relaxed rather than fixed. These ranges exist to
# catch the embarrassing case (a seed company with 900 employees, a public
# company with 11), not to referee every boundary between stages.
_STAGE_EMPLOYEE_RANGES = {
    "seed": (1, 40),
    "series_a": (5, 120),
    "series_b": (30, 400),
    "series_c": (100, 1200),
    "growth": (200, 5000),
    "public": (300, 2_000_000),
}


def stage_employee_mismatch(stage: str, employees: int) -> bool:
    """True iff `employees` is implausible for `stage` -- e.g. a seed
    company with 900 employees, or a public company with 11. An unrecognised
    `stage` string is treated as unconstrained (no mismatch) rather than
    raising, since this is a plausibility check, not a schema validator --
    the Literal in `Company.stage` is what enforces valid values.
    """
    lo, hi = _STAGE_EMPLOYEE_RANGES.get(stage, (0, 10**9))
    return not (lo <= employees <= hi)


# Spec §5 requires implied ACV to be plausible "for the stated stage and
# market". The blind implementation dropped the market half and used a single
# $50 floor, which is a B2B ACV assumption: it failed `apm_consumer` twice on
# 2026-08-04 against worlds that were right ($30.75 ARPU over 400,000 users,
# then $3.91 over 3,200,000). `CaseWorld` has no b2b/consumer field, so
# customer_count is the market proxy -- nobody sells to 3.2 million
# ENTERPRISE accounts, so a count that large is consumer by construction and
# an ARPU of a few dollars is ordinary there.
#
# Two bands rather than one lowered floor, deliberately. Ratcheting the single
# floor down until the run passes is exactly the "an over-strict check gets
# relaxed rather than fixed" failure spec §5 warns about, and it would have
# destroyed the check for B2B, where $50 is a real signal. This keeps that
# signal where it applies and stops firing where it never did.
_CONSUMER_SCALE_CUSTOMERS = 100_000
_CONSUMER_MIN_ACV = 1.0
_B2B_MIN_ACV = 50.0
_MAX_ACV = 5_000_000.0


def implied_acv_implausible(
    arr_usd: str, customer_count: int, *, min_acv: float | None = None, max_acv: float = _MAX_ACV
) -> bool:
    """True iff the implied ACV (`arr_usd / customer_count`) falls outside a
    deliberately wide plausible band. Spec §5's example: a seed company with
    2 customers and "$40M" ARR implies a $20M ACV, which is not a business.
    `customer_count <= 0` is always implausible -- division by a
    non-positive count is undefined, not merely out of range.

    The floor is chosen from `customer_count` unless `min_acv` is passed
    explicitly: consumer scale gets $1, everything else keeps the original
    $50. See the comment above for why this is conditioned rather than
    lowered, and DEV-STATE § Decisions 2026-08-04.
    """
    if customer_count <= 0:
        return True
    if min_acv is None:
        min_acv = (
            _CONSUMER_MIN_ACV
            if customer_count >= _CONSUMER_SCALE_CUSTOMERS
            else _B2B_MIN_ACV
        )
    acv = parse_dollar_amount(arr_usd) / customer_count
    return not (min_acv <= acv <= max_acv)
