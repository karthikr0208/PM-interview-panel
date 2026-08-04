"""Interview Planner — turns a `case_world` into an ordered set of 5-7
questions covering all five rubric dimensions. `case_world` is read-only
here: this is the immutability rule's first real test by a downstream agent
(ARCHITECTURE §2). `grounded_in` is the whole design — every question
declares which case-world facts it depends on, which converts "is this
question answerable?" into a mechanical set-membership check downstream.

Pure function, no side effects. `plan_interview` performs no database writes
and emits no `agent_events` rows — those belong to the `plan_interview` node
in `app/graph/build.py`. Golden cases call this function directly with no
session and no database, so a DB call in here would break every one of them.

See docs/specs/agents/AGENT-PLANNER-SPEC.md for the full contract.
"""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel

from app.llm import Role, get_llm

RubricDimension = Literal[
    "business_model_fluency",
    "market_accuracy",
    "decision_quality",
    "structural_clarity",
    "point_of_view",
]


class PlannedQuestion(BaseModel):
    idx: int
    question: str  # asked verbatim; revealed whole, never streamed
    intent: str  # what this is trying to surface, for the Evaluator
    primary_dimension: RubricDimension
    probe_angles: list[str]  # 2-3 followups if the answer comes back thin
    grounded_in: list[str]  # case_world facts/entities this depends on
    minutes: int


class QuestionPlan(BaseModel):
    questions: list[PlannedQuestion]  # 5-7
    total_minutes: int  # <= 45


# One block, same reasoning as resume_analyst.py and case_architect.py: every
# constraint the golden suite checks (grounding, verbatim copying, dimension
# coverage, no fake-round numbers) has to stay visible in one place.
_SYSTEM_PROMPT = """You are the Interview Planner for a PM interview simulator. Given a candidate's \
confirmed level and a `case_world`, produce 5-7 interview questions. Answer directly with the JSON \
object; do not deliberate at length before answering.

THE HARD REQUIREMENT: every question must be answerable from the case world given. Never invent an \
entity, number, or fact the case world does not contain — that forces the Interviewer to improvise \
later and contradict the world live, the worst failure this product can produce.

GROUNDED_IN, checked mechanically: every entry must be copied EXACTLY, character-for-character, \
from the case world — never paraphrased, never empty. Use: the company name, a competitor name, or \
another named entity, exactly as written; or a bare number exactly as it appears in the schema with \
no unit added (yoy_growth_pct 41.2 -> write "41.2", never "41.2%"; arr_usd "$4.7M" -> copy with the \
$ and letter, "$4.7M"); or one of the supporting_facts strings copied in full, verbatim. 2-3 entries \
per question, never empty.

Each entry is the VALUE ALONE and nothing else: never the field name, never a colon, never quotes \
you add yourself. Write "$2.8B", never "size_usd: \\"$2.8B\\""; write "14.6", never \
"growth_rate_pct: 14.6". Prefer a short entry: a name or a bare number is safest, because a long \
sentence is the one you will get wrong. If you do copy a sentence, copy the WHOLE value from its first character to its \
last, and change nothing — do not stop at a clause, do not drop the tail, do not add a full stop \
the original does not have. Quoting from situation.prompt, situation.tension or \
situation.leadership_belief is where truncation happens; use supporting_facts instead.

THE QUESTION TEXT: name the company IN EVERY SINGLE QUESTION, all 5-7 of them, with no exception. \
This is checked mechanically on each one and it is the cheapest requirement here to satisfy, so do \
not skip it on the question where the rest of the sentence already feels specific — that is the \
one that fails. Use the company's name from the case world (the short form is fine, e.g. \
"Ferngrove Media" or "Ferngrove"), and cite a competitor or a figure from metrics or market as \
well where it fits naturally. Describing this world's situation is NOT a substitute: "given the \
constraints on headcount, how would you structure it?" fails even though the constraints are real, \
because it names nobody; "how would you structure it at Ferngrove, given no net-new headcount this \
quarter?" passes. Write them the way an interviewer who read the business would say it. Candidate-facing copy, asked verbatim: never \
an em-dash or en-dash (use a comma or "and"), no raw JSON, no meta-commentary, no fake-round number \
like "50% of customers" (copy figures with the world's own organic decimal precision).

No framework narration ("walk me through your RICE analysis") — ask about the business, not a \
framework to apply to it.

RUBRIC COVERAGE: every one of these five must be `primary_dimension` of at least one question: \
business_model_fluency, market_accuracy, decision_quality, structural_clarity, point_of_view. One \
or two get a second question; let level guide which (senior: a second decision_quality or \
point_of_view; junior: a second structural_clarity or business_model_fluency).

LEVEL CALIBRATION shifts scope, never the dimensions. APM: one feature/surface. PM: one product \
area end to end. Senior PM: real ambiguity across a product line or domain. GPM: multiple products \
or a portfolio-level business outcome (revenue, headcount, market position). Do not let \
single-surface language ("this feature/screen/flow") leak into a senior/GPM question, or portfolio \
language ("portfolio", "across our products", "business unit") leak into an APM/PM question.

TIME: 45 minutes total; plan roughly 35-40 minutes of questions, leaving room for followups. \
`total_minutes` must equal the exact sum of every question's `minutes` and never exceed 45.

ORDERING: put the most diagnostic question first, never last, so truncation degrades gracefully.

PROBE_ANGLES: 2-3 short followups per question, for when an answer comes back thin, referencing \
only things true of this case world.

INTENT: one short sentence for the Evaluator naming what this question surfaces about the \
candidate's thinking, not written for the candidate.
"""


async def plan_interview(
    assessed_level: str, case_world: dict, *, role: Role = "deep"
) -> QuestionPlan:
    """Plans 5-7 questions against `case_world` for `assessed_level`. Pure
    function: no DB, no session, no side effects — see module docstring.

    **Defaults to `deep`, against the portfolio calibration's "agents default
    to `fast`".** This is the evidence spec §6 asked for, and it is a
    correctness constraint rather than a quality preference: on 2026-08-04
    `fast` (gpt-oss-20b) failed Groq's strict schema validation on this
    agent's output TWICE IN A ROW, once by folding `grounded_in` into the
    preceding `probe_angles` array. `deep` produced a valid plan first try
    with no retry. `QuestionPlan` is the largest generation in the product
    (5-7 objects of 7 fields, two of them string arrays) and the 20b model
    cannot hold it. See DEV-STATE § Decisions 2026-08-04.

    `case_world` is READ ONLY. This function must never mutate the dict it
    is given, and the node calling it must never write `case_world` back to
    state — it was already written once, by the Case Architect, and stays
    immutable for the rest of the graph (ARCHITECTURE §2).

    `assessed_level` must be the CONFIRMED level from graph state, the same
    value `generate_case_world` was called with — this function has no way
    to verify that; the caller is responsible for reading it from
    `state["assessed_level"]`, never re-deriving it.

    Raises `ValueError` on an empty `assessed_level` or an empty
    `case_world` rather than silently planning against nothing.
    """
    if not assessed_level or not assessed_level.strip():
        raise ValueError("plan_interview requires a non-empty assessed_level")
    if not case_world:
        raise ValueError("plan_interview requires a non-empty case_world")

    llm = get_llm(role).with_structured_output(QuestionPlan)
    messages = [
        ("system", _SYSTEM_PROMPT),
        (
            "human",
            "Assessed level: "
            + assessed_level
            + "\n\nCase world:\n"
            + json.dumps(case_world, indent=2),
        ),
    ]
    return await llm.ainvoke(messages)
