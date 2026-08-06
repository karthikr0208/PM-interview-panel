"""Interview Planner — picks ONE question shape deterministically and asks
the LLM to fill only its slots, plus a probe ladder to sustain 45 minutes of
follow-up. PHASE-3.5-SPEC.md 3.5.3 rewrites this agent from a 5-7 free-form
question generator to a slot-filler: shape SELECTION is pure Python
(`app.questions.shapes.select_shape_for_world`), and the model never writes
the question string itself -- `shape.template.format(**slots)` does, in
Python, after the call returns. That is the structural fix for the decorative
statistic and recitation-shaped defects DEV-STATE § Decisions 2026-08-05
recorded: a template with no `{market_size}` slot cannot have a market size
stapled to it, no matter what the model tries.

`case_world` is read-only here: this is the immutability rule's first real
test by a downstream agent (ARCHITECTURE §2). `grounded_in` is unchanged in
meaning from the pre-3.5.3 contract -- every entry must be copied
character-for-character from `case_world`, still a set-membership check
downstream (`missing_grounding`).

Pure function, no side effects. `plan_interview` performs no database writes
and emits no `agent_events` rows -- those belong to the `plan_interview` node
in `app/graph/build.py`. Golden cases call this function directly with no
session and no database, so a DB call in here would break every one of them.

🔴 Backward compatibility that matters (PHASE-3.5-SPEC.md 3.5.3's brief):
`ask_question` in `app/graph/build.py` reads
`state["question_plan"][q_idx]["question"]` AND
`state["question_plan"][q_idx]["primary_dimension"]` (the latter feeds
`dimension_coverage`). `question_plan` stays a list of dicts with both keys
present -- one entry now instead of 5-7. This story does not touch
`build.py`, so `PlannedQuestion.primary_dimension` is set programmatically
from the probe ladder's first entry (the dimension the main question opens
on) rather than asked of the model as a second, redundant field. See this
module's own comment on `_first_dimension` below.

See docs/specs/agents/AGENT-PLANNER-SPEC.md for the full contract (owed an
update by this story, per the brief -- Karthik's, not this file's).
"""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel

from app.llm import Role, get_llm
from app.questions.shapes import QuestionShape, select_shape_for_world

RubricDimension = Literal[
    "business_model_fluency",
    "market_accuracy",
    "decision_quality",
    "structural_clarity",
    "point_of_view",
]

RUBRIC_DIMENSIONS: tuple[RubricDimension, ...] = (
    "business_model_fluency",
    "market_accuracy",
    "decision_quality",
    "structural_clarity",
    "point_of_view",
)


# ── What the model actually returns ─────────────────────────────────────────
# Deliberately NOT a `dict[str, str]` for `slots`: Groq's strict JSON schema
# mode wants enumerable properties, not an open string-keyed map, and every
# other structured-output schema in this product (CaseWorld, the pre-3.5.3
# QuestionPlan) is built the same way -- fixed fields, lists of fixed-shape
# objects. A `list[SlotFill]` of {name, value} pairs is the strict-schema-safe
# equivalent of a dict.
class SlotFill(BaseModel):
    name: str  # must match one of the shape's `slots` names, verbatim
    value: str  # copied/derived from case_world -- see prompt's NUMBERS rule


class ProbeAngle(BaseModel):
    angle: str  # a follow-up prompt, referencing only this case world
    primary_dimension: RubricDimension


class _PlannerFill(BaseModel):
    """The model's raw output. Never exposed outside this module -- Python
    turns it into `QuestionPlan` below, which is what `build.py`'s node and
    the golden suite actually see."""

    slots: list[SlotFill]
    grounded_in: list[str]  # 2-3 entries, character-for-character from case_world
    probe_ladder: list[ProbeAngle]  # 5-8 ordered angles, all 5 dimensions covered
    intent: str  # one sentence, for the Evaluator


# ── What this module exports: unchanged shape of the OLD contract ──────────
# (`question_plan` stays "a list of dicts with a `question` key"), so
# `build.py`'s `plan.questions` / `q.model_dump()` calls need no edit.
class PlannedQuestion(BaseModel):
    idx: int = 0
    question: str  # `shape.template.format(**slots)`, verbatim, never model-written
    intent: str
    primary_dimension: RubricDimension  # see module docstring: probe_ladder[0]'s
    probe_ladder: list[ProbeAngle]
    grounded_in: list[str]
    minutes: int = 40  # the whole interview budget now, not a per-question slice


class QuestionPlan(BaseModel):
    questions: list[PlannedQuestion]  # always length 1, story 3.5.3
    total_minutes: int = 40


class MissingSlotError(ValueError):
    """The model filled `slots` but left one of the shape's required names
    unfilled. Raised rather than silently formatting a KeyError out of
    `str.format` -- a missing slot is a real generation failure, not
    something to paper over with a default value the case world never
    stated (that would reopen the exact invention risk story 2 of this
    phase's 'THREE DECISIONS' section is about, just one story early)."""


def _build_question(shape: QuestionShape, fills: list[SlotFill]) -> str:
    values = {f.name: f.value for f in fills}
    missing = [name for name in shape.slots if name not in values]
    if missing:
        raise MissingSlotError(
            f"shape {shape.template!r} needs slot(s) {missing}, model returned "
            f"{sorted(values)}"
        )
    return shape.template.format(**{name: values[name] for name in shape.slots})


def _first_dimension(probe_ladder: list[ProbeAngle]) -> RubricDimension:
    """`ask_question` (app/graph/build.py:470) reads
    `question_plan[q_idx]["primary_dimension"]` to seed `dimension_coverage`
    -- untouched by this story, so this key must still exist. Rubric
    coverage itself now lives across the WHOLE probe ladder (spec §3's
    rewrite), so there is no single "the" dimension for a one-question plan
    any more; the ladder's first entry (what the main question is asked to
    open on) is the least arbitrary single value to report here. Raises if
    the ladder is empty rather than picking a fake default -- an empty
    ladder is `missing_probe_ladder_coverage`'s job to catch, not this
    function's job to hide."""
    if not probe_ladder:
        raise ValueError("probe_ladder is empty; cannot derive a primary_dimension")
    return probe_ladder[0].primary_dimension


# One block, same reasoning as the pre-3.5.3 prompt and every other agent in
# this product: every constraint the golden suite checks has to stay visible
# in one place so it cannot silently drop out of a future edit.
_SYSTEM_PROMPT = """You are the Interview Planner for a PM interview simulator. You will be given \
ONE fixed question TEMPLATE with named slots, and a `case_world`. Your only job is to fill the \
named slots from the case world, ground your fill, and plan a probe ladder for the 45-minute \
interview that follows. You never write the question itself -- the template is filled in code \
after you answer, not by you. Answer directly with the JSON object; do not deliberate at length.

SLOTS: fill EVERY slot name you are given, exactly once each, nothing extra. Each value is SHORT \
-- a name or a short noun phrase copied or lightly derived from the case world, never a full \
sentence and never a number. A slot value must NEVER itself contain a dollar figure, a percentage, \
or any digit -- the template has no slot for a market size or growth rate on purpose (that is the \
whole point of this design), and smuggling a figure into an unrelated slot (e.g. writing "the \
$12.3B licensing market" into an "adjacent_market" slot) defeats it exactly the same way. If a slot \
calls for a market, product, capability, or segment, name it in words only ("the AI licensing \
market", never "the $12.3B AI licensing market").

GROUNDED_IN, checked mechanically: 2-3 entries, each copied EXACTLY, character-for-character, from \
the case world -- never paraphrased, never empty. Use the company name, a competitor name, another \
named entity, or a supporting_facts string copied in full. Each entry is the VALUE ALONE: never a \
field name, never a colon, never quotes you add yourself.

PROBE_LADDER: 5-8 ordered follow-up angles for the Interviewer to draw on as the candidate answers \
the one main question over 45 minutes. Order them so the early angles are natural next questions \
and the later ones go deeper or pivot to a different facet. Every one of these five dimensions must \
be the `primary_dimension` of AT LEAST ONE angle -- business_model_fluency, market_accuracy, \
decision_quality, structural_clarity, point_of_view. One or two dimensions may get a second angle; \
let the case's own tension guide which. Each `angle` is a short instruction for what to probe next \
("push on what happens to gross margin if churn rises"), not a question addressed to the candidate \
directly, and it must reference only facts true of this case world -- never invent a number, \
competitor, or fact the world does not contain.

INTENT: one short sentence for the Evaluator naming what the main question is trying to surface \
about the candidate's thinking, not written for the candidate.

Never use an em-dash or en-dash anywhere in any field (use a comma or "and" instead). Never a \
fake-round number like "50% of customers" in any field that permits a number at all (only \
grounded_in's verbatim copies may contain the case world's own organic figures)."""


async def plan_interview(
    assessed_level: str, case_world: dict, *, role: Role = "fast"
) -> QuestionPlan:
    """Plans ONE question, probed by a 5-8 angle ladder, against
    `case_world` for `assessed_level`. Pure function: no DB, no session, no
    side effects -- see module docstring.

    **Defaults to `fast`, reversing the pre-3.5.3 `deep` default.** The old
    `QuestionPlan` (5-7 objects of 7 fields, `deep`-only per DEV-STATE §
    Decisions 2026-08-04) no longer exists; this call's output is a
    fraction of that size (one shape's slots, a probe ladder of short
    strings, one sentence). Re-measured per PHASE-3.5-SPEC.md 3.5.3's Part
    4 -- see DEV-STATE for the observed golden-smoke result before trusting
    this default in production.

    Shape SELECTION happens before the LLM is ever called --
    `select_shape_for_world(assessed_level, case_world.get("suits_categories"))`
    is deterministic Python (CLAUDE.md § Style), and the chosen shape's
    category, template, and slot names are what the prompt hands the model
    to fill. `case_world` is READ ONLY: this function must never mutate the
    dict it is given, and the node calling it must never write `case_world`
    back to state (ARCHITECTURE §2).

    `assessed_level` must be the CONFIRMED level from graph state, the same
    value `generate_case_world` was called with -- this function has no way
    to verify that; the caller is responsible for reading it from
    `state["assessed_level"]`, never re-deriving it.

    Raises `ValueError` on an empty `assessed_level` or an empty
    `case_world`. Raises `MissingSlotError` if the model's `slots` do not
    cover every name the chosen shape requires -- a real generation
    failure, not something to paper over with an invented default.
    """
    if not assessed_level or not assessed_level.strip():
        raise ValueError("plan_interview requires a non-empty assessed_level")
    if not case_world:
        raise ValueError("plan_interview requires a non-empty case_world")

    shape = select_shape_for_world(assessed_level, case_world.get("suits_categories"))

    llm = get_llm(role, max_tokens=2048).with_structured_output(_PlannerFill)
    messages = [
        ("system", _SYSTEM_PROMPT),
        (
            "human",
            "Assessed level: "
            + assessed_level
            + f"\n\nQuestion template (category: {shape.category}): {shape.template!r}"
            + f"\nSlot names to fill, exactly these and no others: {list(shape.slots)}"
            + "\n\nCase world:\n"
            + json.dumps(case_world, indent=2),
        ),
    ]
    fill = await llm.ainvoke(messages)

    question_text = _build_question(shape, fill.slots)
    planned = PlannedQuestion(
        idx=0,
        question=question_text,
        intent=fill.intent,
        primary_dimension=_first_dimension(fill.probe_ladder),
        probe_ladder=fill.probe_ladder,
        grounded_in=fill.grounded_in,
    )
    return QuestionPlan(questions=[planned])
