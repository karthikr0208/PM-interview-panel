"""The question shape bank -- fixed templates across four categories,
checked in as DATA, not prose. Started as the spec's named twelve; a
thirteenth (growth, `{n}x`) was added 2026-08-06 to cover Karthik's own
literal example phrasing ("how would you 10x Duolingo") that the original
twelve could not reproduce exactly -- see that shape's own comment below.
Story 3.5.2 (PHASE-3.5-SPEC.md), which exists
to fix the decorative-statistic defect recorded in DEV-STATE.md
Decisions 2026-08-05: two of the three questions this product actually
served stapled a market-size or growth-rate clause to the front of the
question, and the third could be answered by reciting the brief back rather
than exercising judgment.

**Why a bank of templates instead of a prompt instruction, and why this is
the entire design:** a prompted ban does not hold in this codebase. The
em-dash rule failed as prompt text TWICE and was only fixed by making the
dash unsayable -- `stripDashes` on the frontend, a deterministic transform,
not an instruction the model could ignore. The same logic applies here, one
level earlier: rather than telling the model "do not cite a market size or
growth rate", the fix removes the *slot* the statistic would go in.

**🔴 NO SHAPE BELOW HAS A SLOT FOR A MARKET SIZE OR A GROWTH RATE.** A model
filling one of these templates has nowhere to put "$12.3B market" or
"31.4% ARR growth last year" even if it tries, because no `{market_size}` or
`{growth_rate}` placeholder exists to fill. If a future edit adds one "just
for this one case", it reopens exactly the defect this file exists to
close -- do not add it. `select_shape` below is the only sanctioned way to
choose a shape, and it is deterministic Python (CLAUDE.md § Style: no LLM
call where the decision can be made from state).

Story 3.5.3 (the next story, NOT this one) is what makes the Planner
actually select and fill from this bank. This module only needs to exist
and be correct; nothing here calls an LLM.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

Category = str  # "strategy" | "gtm" | "pricing" | "growth"


@dataclass(frozen=True)
class QuestionShape:
    """One fixed question template. `template` is a `str.format()` string;
    `slots` names every placeholder it requires, in the order they appear in
    `template` -- redundant with `template` itself (the placeholders could be
    parsed out), but kept explicit so a caller can validate it has a value
    for every slot before calling `.format()`, and so a shape's arity is
    readable without parsing the template string."""

    category: Category
    template: str
    slots: tuple[str, ...]


# The twelve shapes, per PHASE-3.5-SPEC.md "3.5.2" and Karthik's own examples
# of the target register ("what is Reddit's biggest threat", "should Samsung
# enter gaming", "how would you price YouTube Premium", "how would you 10x
# Duolingo") -- shorter and broader than anything the generative prompt has
# produced so far. Order within each category is deliberate: it is the order
# `select_shape` indexes into, so reordering changes which shape a given
# (level, category) pair resolves to.
SHAPE_BANK: tuple[QuestionShape, ...] = (
    # --- strategy ---------------------------------------------------------
    QuestionShape(
        category="strategy",
        template="What is {company}'s biggest threat over the next three years?",
        slots=("company",),
    ),
    QuestionShape(
        category="strategy",
        template="Should {company} enter {adjacent_market}?",
        slots=("company", "adjacent_market"),
    ),
    QuestionShape(
        category="strategy",
        template="{company} can make one big bet next year. What should it be?",
        slots=("company",),
    ),
    # --- gtm ----------------------------------------------------------------
    QuestionShape(
        category="gtm",
        template="{company} just built {capability}. How would you take it to market?",
        slots=("company", "capability"),
    ),
    QuestionShape(
        category="gtm",
        template="How would you launch {product} for {new_segment}?",
        slots=("product", "new_segment"),
    ),
    # "How does that change {company}'s launch?" (the original phrasing)
    # passes `is_recitation_shaped` when filled -- no `you`/`your`, no
    # decision verb, so the rule (correctly) reads it as asking what
    # changed rather than what the candidate would do about it. Fixed
    # 2026-08-06 by making the candidate own the plan explicitly: "your
    # launch plan for {company}" turns this into a decision question, which
    # is what it was always meant to test, and it is better interview copy
    # regardless of the gate. See `test_every_shape_clears_its_own_gates`.
    QuestionShape(
        category="gtm",
        template="{competitor} shipped {capability} first. How does that change your launch plan for {company}?",
        slots=("competitor", "capability", "company"),
    ),
    # --- pricing --------------------------------------------------------------
    QuestionShape(
        category="pricing",
        template="How would you price {product}?",
        slots=("product",),
    ),
    QuestionShape(
        category="pricing",
        template="Should {product} move from {current_model} to {alternative_model}?",
        slots=("product", "current_model", "alternative_model"),
    ),
    QuestionShape(
        category="pricing",
        template="{company} wants to raise prices on {product}. How would you do it?",
        slots=("company", "product"),
    ),
    # --- growth ---------------------------------------------------------------
    QuestionShape(
        category="growth",
        template="How would you grow {metric} at {company} by {n}x?",
        slots=("metric", "company", "n"),
    ),
    QuestionShape(
        category="growth",
        template="{metric} has been flat for {period}. How would you diagnose and fix it?",
        slots=("metric", "period"),
    ),
    QuestionShape(
        category="growth",
        template="How would you increase {conversion_step} for {product}?",
        slots=("conversion_step", "product"),
    ),
    # Added 2026-08-06: Karthik's own literal example of the target register
    # ("how would you 10x Duolingo") did not survive `matches_no_shape`'s
    # strict `fullmatch` -- no shape produced that exact multiplier phrasing.
    # This is his example verbatim with the two variables it actually has.
    QuestionShape(
        category="growth",
        template="How would you {n}x {company}?",
        slots=("n", "company"),
    ),
)

CATEGORIES: tuple[Category, ...] = ("strategy", "gtm", "pricing", "growth")

# Deterministic index a level resolves to, when picking among a category's
# shapes -- arbitrary but fixed, so the SAME (level, category) pair always
# returns the SAME shape. No claim that this ordering is calibrated to level
# difficulty; that is a decision for whoever calls this with real judgment
# behind it (story 3.5.3), not something to infer here.
_LEVEL_INDEX: dict[str, int] = {"APM": 0, "PM": 1, "Senior PM": 2, "GPM": 3}


def shapes_by_category(category: Category) -> tuple[QuestionShape, ...]:
    """All bank shapes in `category`, in `SHAPE_BANK` order."""
    return tuple(s for s in SHAPE_BANK if s.category == category)


def select_shape(level: str, category: Category) -> QuestionShape:
    """Deterministic shape pick, no LLM call (CLAUDE.md § Style: prefer
    deterministic Python over an LLM call wherever the decision can be made
    from state). `level` need not be one of the four known levels -- an
    unrecognized level falls back to index 0, rather than raising, so a
    caller passing a slightly different level string degrades gracefully
    instead of crashing the interview.

    Raises `ValueError` if `category` has no shapes -- a typo'd category
    name should fail loudly here, not silently return nothing to format.
    """
    candidates = shapes_by_category(category)
    if not candidates:
        raise ValueError(f"no shapes registered for category {category!r}")
    index = _LEVEL_INDEX.get(level, 0) % len(candidates)
    return candidates[index]


def select_category(level: str, suits_categories: Sequence[str] | None) -> Category:
    """Story 3.5.3: picks a category from the INTERSECTION of the four
    canonical categories and `suits_categories` (`CaseWorld.suits_categories`,
    set per curated world in `app/cases/*.json`) -- deterministic Python, no
    LLM call, same reasoning as `select_shape` above. Iterates `CATEGORIES`
    (not `suits_categories` itself) so a world listing its categories in an
    arbitrary order still resolves to the same index for the same level.

    `suits_categories` falsy (`None` or `[]`) falls back to the FULL
    `CATEGORIES` tuple rather than raising -- this is what keeps the
    untouched generative Case Architect path working: `CaseWorld.
    suits_categories` defaults to `[]` there (only the eight curated worlds
    set it), and a generated world with no curated category list must still
    be able to get a question. Curated worlds always set 2-3 entries, so
    this fallback never engages for the eight real companies.

    Raises `ValueError` if none of `suits_categories` names a real category
    -- a typo'd category in a curated world's JSON should fail loudly at
    selection time, not silently fall back and mask the typo.
    """
    pool = suits_categories or CATEGORIES
    candidates = tuple(c for c in CATEGORIES if c in set(pool))
    if not candidates:
        raise ValueError(
            f"suits_categories {list(suits_categories or [])!r} names none of "
            f"the known categories {CATEGORIES}"
        )
    index = _LEVEL_INDEX.get(level, 0) % len(candidates)
    return candidates[index]


def select_shape_for_world(level: str, suits_categories: Sequence[str] | None) -> QuestionShape:
    """The one function story 3.5.3's Planner calls: composes
    `select_category` and `select_shape` into a single deterministic pick
    from `(level, case_world["suits_categories"])`. Same (level,
    suits_categories) always resolves to the same shape -- matches
    `select_case_world`'s determinism (`app/cases/__init__.py`), for the
    same reason: a retried request must never mid-flight change which
    question shape a candidate is being interviewed against.
    """
    category = select_category(level, suits_categories)
    return select_shape(level, category)
