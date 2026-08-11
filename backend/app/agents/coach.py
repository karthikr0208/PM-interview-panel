"""The Coach — three improvements, each anchored to something that actually
happened in the interview.

Runs ONCE, after the loop exits. See `docs/specs/PHASE-5-SPEC.md`.

── WHAT THIS AGENT READS, AND WHY IT IS NOT THE TRANSCRIPT ──────────────
`ARCHITECTURE.md:121` specifies the Coach as "whole transcript in one 1M-context
call". That model does not exist on this stack: the ceiling is 8,000 TPM and the
full transcript measured 10,274 tokens on 2026-08-06. Feeding the raw transcript
is over the ceiling before the prompt is added -- the same wall that forced the
Evaluator into per-answer scoring.

So the Coach reads `answer_evaluations` instead: per (turn, dimension) a score, a
VERBATIM candidate quote, and since migration 0004 the Evaluator's `reasoning`.
That migration's comment anticipated exactly this -- without it "the coach report
would have to re-derive from a quote and a digit the judgement the Evaluator
already made and wrote down." The Coach therefore reads JUDGEMENT, not raw
material, and the input collapses from a transcript to a bounded set of rows.

── THE TWO KINDS, AND WHY THREE IS ALWAYS REACHABLE ─────────────────────
Karthik's call 2026-08-11: three improvements, always. That is honest only
because improvements are not all one shape.

  moment  "here is what you said, here is a stronger version"
          quotes the candidate -- FEWER available when coverage is thin
  gap     "you never took a position on the market at all"
          quotes nothing, because nothing was said -- MORE available when
          coverage is thin

A dimension in `not_assessed` is not an absence of coaching material; it is among
the most useful things a coach can say. PHASE-4-SPEC §1 measured a real interview
evidencing three of five dimensions, so it produced two gaps. The two kinds move
in opposite directions with coverage, which is what makes three reachable at
every realistic coverage level without inventing anything.

── WHAT MAKES AN INVENTED ANCHOR DETECTABLE ─────────────────────────────
ARCHITECTURE §9 says a fabricated fact is the failure mode nothing can catch at
runtime. Here it CAN be caught, because a `moment`'s anchor is not free text: it
must be one of the `evidence_quote` values the Evaluator already stored for this
session. `verify_anchors` below is the check, and it is pure -- no LLM, no
network -- so the graph node and the golden suite run the identical assertion.
A `gap` is falsifiable the mirror way: its dimension must genuinely carry no
score in this session.
"""
from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.agents.planner import RUBRIC_DIMENSIONS
from app.llm import Role, get_llm

# PRD §3 and §10: three improvements. Not a target the model may miss -- the
# schema below refuses a report of any other length, because "up to three"
# silently becomes one on a thin interview and nobody notices.
IMPROVEMENTS_PER_REPORT = 3

# 🔴 Part of the REQUEST size against the 8,000 TPM ceiling on Groq, not merely
# a cap on the reply -- see `app/llm.py`'s `get_llm` note. The budget test reads
# THIS constant rather than a literal of its own, so the two cannot drift the way
# the Evaluator's did (DEV-STATE § Decisions 2026-08-11).
#
# 4096 rather than 2048 for the reason recorded on `evaluate_answer`:
# `gpt-oss-20b` is a reasoning model and its reasoning tokens come out of the
# SAME output budget as the JSON, so a tight cap returns `failed_generation: ''`
# -- an EMPTY body, not a truncated one. This output is three improvements with
# three prose fields each, which is larger than one `AnswerEvaluation`.
COACH_MAX_TOKENS = 4096


class Improvement(BaseModel):
    kind: Literal["moment", "gap"]

    # Set on a `moment`, and it must be COPIED from the quotes supplied in the
    # prompt -- `verify_anchors` rejects anything else. `None` on a `gap`, where
    # there is by definition nothing the candidate said to quote.
    anchor_quote: str | None = None

    # Set on a `gap`, naming the rubric dimension that went unevidenced. `None`
    # on a `moment`, which anchors to a quote instead.
    dimension: str | None = None

    # Prose the candidate reads. `min_length` is the same content floor
    # `DimensionScore` uses; whitespace-only is the golden suite's job, matching
    # this project's convention.
    stronger_version: str = Field(min_length=1)
    drill: str = Field(min_length=1)

    @model_validator(mode="after")
    def _kind_carries_its_own_evidence(self) -> "Improvement":
        """Mirrors `0005_coach_reports.sql`'s two scoped check constraints.
        Enforced HERE as well as in Postgres deliberately: the database check is
        the guarantee, but it fires at write time with a `CheckViolation` that
        says nothing about which agent produced the bad row. Failing in pydantic
        fails inside the validate-retry loop instead, where the model gets a
        second attempt with the reason.
        """
        if self.kind == "moment":
            if not (self.anchor_quote or "").strip():
                raise ValueError(
                    "a 'moment' improvement must carry anchor_quote, copied verbatim "
                    "from one of the quotes supplied in the prompt -- an improvement "
                    "with no quote is generic advice"
                )
            if self.dimension is not None:
                raise ValueError(
                    "a 'moment' improvement anchors to a quote, not a dimension; "
                    "leave dimension null"
                )
        else:
            if self.dimension not in RUBRIC_DIMENSIONS:
                raise ValueError(
                    f"a 'gap' improvement must name one of the five rubric dimensions, "
                    f"got {self.dimension!r}"
                )
            if (self.anchor_quote or "").strip():
                raise ValueError(
                    "a 'gap' improvement is about something the candidate never said, "
                    "so it cannot carry a quote; leave anchor_quote null"
                )
        return self


class CoachReport(BaseModel):
    improvements: list[Improvement]

    @model_validator(mode="after")
    def _report_is_three_distinct_improvements(self) -> "CoachReport":
        if len(self.improvements) != IMPROVEMENTS_PER_REPORT:
            raise ValueError(
                f"a coach report is exactly {IMPROVEMENTS_PER_REPORT} improvements, "
                f"got {len(self.improvements)}"
            )

        # Two gaps naming the same dimension is the cheapest way to reach three
        # without saying three things, and it reads as padding to the candidate.
        gap_dimensions = [i.dimension for i in self.improvements if i.kind == "gap"]
        duplicate_gaps = {d for d in gap_dimensions if gap_dimensions.count(d) > 1}
        if duplicate_gaps:
            raise ValueError(
                f"dimension(s) {sorted(duplicate_gaps)} named by more than one 'gap' "
                f"improvement -- each gap covers a different dimension"
            )

        anchors = [i.anchor_quote for i in self.improvements if i.kind == "moment"]
        duplicate_anchors = {a for a in anchors if anchors.count(a) > 1}
        if duplicate_anchors:
            raise ValueError(
                "the same quote anchors more than one improvement -- three "
                "improvements means three different moments"
            )
        return self


def available_quotes(evaluations: list[dict]) -> list[str]:
    """Every `evidence_quote` the Evaluator stored this session, in turn order.

    This is the closed set a `moment` anchor must come from. Pure, so the graph
    node and the golden suite check the identical thing.
    """
    return [
        score["evidence_quote"]
        for evaluation in evaluations
        for score in evaluation.get("dimension_scores", [])
        if score.get("evidence_quote")
    ]


def unevidenced_dimensions(evaluations: list[dict]) -> list[str]:
    """The rubric dimensions carrying NO score anywhere in this session.

    Derived from what was actually scored rather than from any single answer's
    `not_assessed`: a dimension unevidenced in turn 1 and scored in turn 4 was
    covered, and coaching the candidate that they never addressed it would be
    false. Order follows `RUBRIC_DIMENSIONS` so the prompt is stable run to run.
    """
    scored = {
        score["dimension"]
        for evaluation in evaluations
        for score in evaluation.get("dimension_scores", [])
    }
    return [d for d in RUBRIC_DIMENSIONS if d not in scored]


def verify_anchors(report: CoachReport, evaluations: list[dict]) -> list[str]:
    """Return a list of problems, empty when the report is fully grounded.

    🔴 This is the check ARCHITECTURE §9 says cannot exist at runtime, and it
    exists here only because the Coach's anchors are drawn from a closed set.
    Returns problems rather than raising so a caller can log every one at once
    instead of discovering them one retry at a time.
    """
    problems: list[str] = []
    quotes = set(available_quotes(evaluations))
    absent = set(unevidenced_dimensions(evaluations))

    for idx, improvement in enumerate(report.improvements):
        if improvement.kind == "moment":
            if improvement.anchor_quote not in quotes:
                problems.append(
                    f"improvement {idx}: anchor_quote is not one of the "
                    f"{len(quotes)} quotes stored for this session -- it was invented "
                    f"or paraphrased"
                )
        elif improvement.dimension not in absent:
            problems.append(
                f"improvement {idx}: claims {improvement.dimension!r} was never "
                f"addressed, but it carries a score in this session"
            )
    return problems


_COACH_SYSTEM_PROMPT = """You are writing the coaching notes a PM candidate reads \
immediately after a product strategy interview. You did not watch the interview. You are \
reading the evaluator's notes on it: what the candidate said, scored against five rubric \
dimensions, with the exact words they used.

Write exactly three improvements. Address the candidate directly as "you".

Each improvement is one of two kinds.

A "moment" improvement is about something the candidate DID say.
  - anchor_quote must be copied EXACTLY, character for character, from the quotes listed \
under "What you said". Do not paraphrase it, do not tidy the grammar, do not trim it. If \
you cannot find a quote worth building on, write a "gap" improvement instead.
  - dimension must be null.

A "gap" improvement is about a rubric dimension the candidate never gave any evidence on.
  - dimension must be one of the dimensions listed under "What never came up".
  - anchor_quote must be null, because there is nothing to quote.
  - Do not treat a gap as a smaller point than a moment. A dimension that never came up in \
forty minutes is usually the most useful thing you can tell someone.

For every improvement, whichever kind:
  - stronger_version: what a stronger candidate at this level would have said instead, or \
would have said at all. Write the actual words, two or three sentences, not a description \
of what they should have done. "Say which segment you are giving up and why" is a note to \
yourself. "I would drop the SMB tier entirely for two quarters, because the support load \
per account is the thing capping enterprise delivery" is a stronger version.
  - drill: one concrete thing to practise before the next interview. It must be doable in \
under thirty minutes and it must be specific to what went wrong here. Not "practise \
structuring answers".

Rules:
  - Do not invent anything the candidate said. Every quote comes from the list.
  - Do not repeat a dimension across two gap improvements, and do not anchor two \
improvements to the same quote.
  - Do not praise. This is the improvements section; the scorecard already carries the \
scores. Be direct and specific, the way a good manager is in a one to one.
  - Use ONLY plain ASCII punctuation. No em dashes and no en dashes: use a comma, a colon, or a \
full stop instead. For a hyphenated word like "state-of-the-art", use the ordinary ASCII hyphen \
on your keyboard, never a Unicode hyphen variant.
  - No invented statistics, and no round made-up numbers like "50%" or "$1M". If you cite \
a figure it comes from the case world.
  - Do not name the rubric dimensions in your prose. The candidate reads plain English, \
not "your business_model_fluency was weak"."""


# 🔴 MEASURED, not chosen. `max_tokens` is part of the request on Groq, so
# COACH_MAX_TOKENS alone is 51% of the 8,000 TPM ceiling before a single input
# token. At 25 rendered rows plus a full case world the request measured 8,328
# on the largest world -- OVER the ceiling, found by `tests/test_coach_budget.py`
# before this agent was ever wired into the graph. The two constants below are
# what bring it back under, and both are principled rather than arbitrary:
#
# The weakest answers are the coachable ones. A dimension the candidate scored
# 4 on twice does not need three worked examples in the prompt; the 2 lowest
# carry the pattern. Rendering every row spent ~2,350 tokens to say the same
# thing.
_QUOTES_PER_DIMENSION = 2

# The Coach does not check factual accuracy -- the Evaluator already did, and
# its verdict arrives as `reasoning`. So `supporting_facts` (the improvisation
# material, ~425 tokens on the largest world) and `suits_categories` (Planner
# routing metadata) are not sent. What remains is what a coach needs to write a
# specific stronger answer: who the company is, the market, the numbers, and
# the strategic tension.
_WORLD_KEYS_THE_COACH_NEEDS = ("company", "market", "metrics", "situation")


def _summarise_world(case_world: dict) -> dict:
    """The case world reduced to what coaching needs.

    `case_world` is immutable and this does not mutate it -- it selects. Keys
    absent from a given world are simply skipped, so a world missing `metrics`
    costs nothing and raises nothing.
    """
    return {
        key: case_world[key] for key in _WORLD_KEYS_THE_COACH_NEEDS if key in case_world
    }


def _render_evaluations(evaluations: list[dict]) -> str:
    """The candidate's quotes plus the evaluator's reasoning, grouped by
    dimension rather than by turn, capped at the weakest few per dimension.

    By dimension deliberately: the Coach is looking for a pattern across an
    interview, and the same weakness showing up in turns 1 and 4 is the single
    most coachable thing there is. Grouped by turn, that pattern is split across
    two places in the prompt and reads as two unrelated notes.

    Lowest score first, then earliest turn, so the cap keeps the most coachable
    rows rather than whichever happened to come first. The sort is total (score,
    then turn index) so the prompt is byte-stable across runs -- an unstable
    prompt would make every golden case flap for reasons that have nothing to do
    with the model.
    """
    by_dimension: dict[str, list[dict]] = {}
    for turn_position, evaluation in enumerate(evaluations):
        for score in evaluation.get("dimension_scores", []):
            by_dimension.setdefault(score["dimension"], []).append(
                {**score, "_turn": evaluation.get("turn_idx", turn_position)}
            )

    if not by_dimension:
        return "(nothing was scored in this interview)"

    lines: list[str] = []
    for dimension in RUBRIC_DIMENSIONS:
        scores = by_dimension.get(dimension)
        if not scores:
            continue
        weakest = sorted(scores, key=lambda s: (s["score"], s["_turn"]))[:_QUOTES_PER_DIMENSION]
        lines.append(f"\n{dimension}:")
        for score in weakest:
            lines.append(f'  you said: "{score["evidence_quote"]}"')
            lines.append(f"    scored {score['score']}/4")
            if score.get("reasoning"):
                lines.append(f"    because: {score['reasoning']}")
    return "\n".join(lines)


def _build_coach_messages(
    case_world: dict,
    question: str,
    assessed_level: str,
    evaluations: list[dict],
) -> list[tuple[str, str]]:
    """Pure message assembly, split out from `generate_coach_report` so the
    token budget can be measured offline with `tiktoken` and no LLM call --
    same reason `_build_evaluation_messages` and `_build_probe_messages` are
    split out. `tests/test_coach_budget.py` calls this directly.
    """
    absent = unevidenced_dimensions(evaluations)
    never_came_up = (
        "\n".join(f"  {dimension}" for dimension in absent)
        if absent
        else "  (every dimension got evidence -- write three 'moment' improvements)"
    )

    human = (
        "Case world (read only, the ground truth behind the interview):\n"
        + json.dumps(_summarise_world(case_world), indent=2)
        + "\n\nThe question you were asked: "
        + question
        + "\n\nYour level: "
        + assessed_level
        + "\n\nWhat you said, as the evaluator recorded it:\n"
        + _render_evaluations(evaluations)
        + "\n\nWhat never came up (available for 'gap' improvements):\n"
        + never_came_up
        + f"\n\nWrite exactly {IMPROVEMENTS_PER_REPORT} improvements."
    )
    return [("system", _COACH_SYSTEM_PROMPT), ("human", human)]


async def generate_coach_report(
    case_world: dict,
    question: str,
    assessed_level: str,
    evaluations: list[dict],
    *,
    role: Role = "fast",
) -> CoachReport:
    """One call, at the end of the interview.

    `role` defaults to `fast` per the 2026-08-02 portfolio calibration, which
    supersedes PRD §6's `deep` assignment for this agent. The Planner carried
    the same `deep` assignment and measured down to `fast` in 3.5.3.

    Raises `ValueError` if `evaluations` is empty: a coach report is three
    improvements grounded in what happened, and an interview with nothing scored
    gives the model nothing to ground them in. The caller renders an honest
    empty state rather than asking for three inventions.
    """
    if not available_quotes(evaluations) and not unevidenced_dimensions(evaluations):
        raise ValueError(
            "generate_coach_report got no quotes and no unevidenced dimensions; "
            "there is nothing to coach on and nothing to ground three improvements in"
        )

    llm = get_llm(role, max_tokens=COACH_MAX_TOKENS, agent="coach").with_structured_output(
        CoachReport
    )
    return await llm.ainvoke(_build_coach_messages(case_world, question, assessed_level, evaluations))
