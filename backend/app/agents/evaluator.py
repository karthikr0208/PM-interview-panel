"""Evaluator -- scores a candidate's answer against the PRD §7 rubric: five
dimensions, 1 to 4, each score carrying a verbatim quote from the transcript.

Story 4.1 wrote the `AnswerEvaluation` / `DimensionScore` schema; story 4.2
added `evaluate_answer` below it, scoped by the measured token budget that
sits directly above the system prompt. Both live here. The GRAPH NODE and the
`answer_evaluations` write are story 4.3 and are not in this module:
`evaluate_answer` is a pure function with no DB, no session and no side
effects, exactly like `answer_clarification` and `generate_probe` (see
`app/agents/interviewer.py`'s docstring for the same split). The golden cases
call it directly with no session and no database, so a DB call in here would
break every one of them.

`tests/golden/evaluator/test_golden.py` imports `evaluate_answer` LAZILY,
inside a session-scoped fixture, and keeps doing so: that import was written
while the name did not exist (story 4.1's acceptance was a deliberately RED
suite raising `ImportError`), and it now resolves. The suite stays `live`-
marked, so `pytest tests -m "not live"` still deselects it and it still costs
nothing to collect. `tests/test_evaluator_budget.py` is the offline half --
it measures the assembled messages with `tiktoken` and never calls a model.

See PHASE-4-SPEC.md § "WHAT THE LIVE INTERVIEW ALREADY DECIDED" #1: two of
five rubric dimensions got ZERO evidence in a real interview, and PRD §8
already forbids scoring a dimension nothing was said about ("every score
carries a verbatim quote ... enforced at the schema level, not by
convention"). `not_assessed` is how that is represented -- see the module
validator below, which enforces two invariants IN THE SCHEMA rather than by
convention, going further than the PRD's own quote-per-score guarantee:

  1. A dimension cannot be BOTH scored and `not_assessed` -- that would be a
     score wearing a "no evidence" label at the same time, which is
     incoherent, not just undesirable.
  2. Every one of the five rubric dimensions must be accounted for exactly
     once, either scored or `not_assessed` -- never silently dropped. This
     is the schema-level version of the trap named in
     `app/agents/interviewer.py`'s `resolve_primary_dimension` docstring: a
     dimension that quietly falls out of the response "collapses the
     ladder's whole rubric coverage," which is exactly the thing Phase 4's
     Evaluator reads and must not do to itself.

`framework_narration` (PRD §7: "recorded separately from the five scores")
is a bool, not a dimension -- a candidate who narrates a framework by name
("I'll run a SWOT here...") without doing the analysis is flagged here, kept
entirely apart from the five rubric scores so it can never be mistaken for a
sixth dimension or folded into one of the five by accident.
"""
from __future__ import annotations

import json

from pydantic import BaseModel, Field, model_validator

from app.agents.planner import RUBRIC_DIMENSIONS, RubricDimension
from app.llm import Role, get_llm


class DimensionScore(BaseModel):
    dimension: RubricDimension
    score: int = Field(ge=1, le=4)
    # PRD §8, enforced HERE rather than by convention: a `DimensionScore`
    # literally cannot be constructed with a blank quote. `min_length=1`
    # catches an empty string; whitespace-only ("   ") is not caught by
    # pydantic's length check and is instead the golden suite's job (see
    # `blank_or_short_fields` in `tests/golden/evaluator/assertions.py`),
    # matching this project's convention of a `min_len` content floor.
    evidence_quote: str = Field(min_length=1)
    reasoning: str = Field(min_length=1)


class AnswerEvaluation(BaseModel):
    dimension_scores: list[DimensionScore]
    # PRD §7: recorded SEPARATELY from the five scores -- never a sixth
    # dimension, never folded into one of the five. See module docstring.
    framework_narration: bool
    # `list[str]`, not `list[RubricDimension]` -- deliberately looser than
    # `DimensionScore.dimension` so the validator below can give a clearer
    # error on an unrecognised value (`ValueError` naming the bad string)
    # rather than pydantic's less specific literal-mismatch message on a
    # field a model is more likely to get wrong under retry pressure.
    not_assessed: list[str]

    @model_validator(mode="after")
    def _dimensions_are_coherent(self) -> "AnswerEvaluation":
        scored = [ds.dimension for ds in self.dimension_scores]
        scored_set = set(scored)

        duplicates = {d for d in scored if scored.count(d) > 1}
        if duplicates:
            raise ValueError(
                f"dimension(s) {sorted(duplicates)} appear more than once in "
                f"dimension_scores -- each of the five dimensions is scored at most once"
            )

        unknown_not_assessed = set(self.not_assessed) - set(RUBRIC_DIMENSIONS)
        if unknown_not_assessed:
            raise ValueError(
                f"not_assessed contains unrecognised dimension(s): {sorted(unknown_not_assessed)}"
            )

        # NAMED TRAP, PHASE-4-SPEC.md #1: a dimension with no evidence must
        # render as not_assessed, never scored anyway. A dimension that is
        # BOTH scored and not_assessed is a score wearing a "no evidence"
        # label at the same time -- incoherent on its face, not merely an
        # inconsistency a downstream reader would have to reconcile.
        overlap = scored_set & set(self.not_assessed)
        if overlap:
            raise ValueError(
                f"dimension(s) {sorted(overlap)} appear in BOTH dimension_scores and "
                f"not_assessed -- a dimension is either scored (with evidence) or "
                f"not_assessed (with none), never both"
            )

        # Every dimension accounted for exactly once. Catches the silent
        # drop this module's docstring names: a dimension that is neither
        # scored NOR listed as not_assessed has vanished with no trace, and
        # an aggregate built from the surviving four would misreport itself
        # as complete.
        accounted = scored_set | set(self.not_assessed)
        missing = set(RUBRIC_DIMENSIONS) - accounted
        if missing:
            raise ValueError(
                f"dimension(s) {sorted(missing)} are neither scored nor listed in "
                f"not_assessed -- every one of the five rubric dimensions must be "
                f"accounted for"
            )

        return self


# ═══════════════════════════════════════════════════════════════════════════
# 🔴 THE TOKEN BUDGET, ALREADY MEASURED -- do not re-derive it. Measured
# 2026-08-11 (orchestrator, offline, zero tokens) with tiktoken's o200k_base
# against every golden fixture at its LAST answer plus a worst-case
# `prior_scores`. `Requested = system + human + max_tokens` (`body` below is
# system + human), against the 8,000 TPM ceiling (see `app/llm.py`'s
# `get_llm` note -- max_tokens is part of the REQUEST size, not just a cap on
# the reply):
#
#   fixture                                            body    @4096   headroom
#   karthik_live_airbnb_senior_pm                      3281     7377      623
#   apm_consumer_world_full_coverage                   3339     7435      565   <- worst
#   pm_b2b_world_narrow_coverage                       3124     7220      780
#   senior_pm_platform_world_level_pair_pm             3321     7417      583
#   senior_pm_platform_world_level_pair_gpm            3322     7418      582
#   gpm_portfolio_world_extreme_narrow                 3059     7155      845
#   sparse_world_framework_narration                   2838     6934     1066
#   followup_defends_decision                          3208     7304      696
#   followup_abandons_decision                         3152     7248      752
#
# 🔴 Every fixture fits at `max_tokens=4096`, but headroom on the worst
# fixture is 565 tokens -- about 93% of the 8,000 TPM ceiling is already
# spoken for, not the 3,217-token cushion `max_tokens=2048` used to leave.
# `EVALUATION_MAX_TOKENS` below is the single source for this value; both the
# request built here and `tests/test_evaluator_budget.py`'s assertion read
# the same constant, so the two cannot drift the way this comment block did
# on 2026-08-10 when the call site moved to 4096 and this arithmetic did not.
#
# PHASE-4-SPEC.md § "WHAT THE LIVE INTERVIEW ALREADY DECIDED" #2 measured the
# FULL transcript at 10,274 tokens, over the ceiling, which is what forces
# per-answer scoring. This is the arithmetic showing per-answer actually fits
# -- computed at the LAST answer before the loop was built, per that section's
# own instruction, not after.
#
# The reason it fits with room: `prior_scores` is a RUNNING SUMMARY, five
# short entries, NOT the raw transcript. It is bounded at five dimensions no
# matter how long the interview runs, so this budget does not grow with turn
# count the way the Interviewer's window does.
# ═══════════════════════════════════════════════════════════════════════════

# Part of the REQUEST size against the 8,000 TPM ceiling, not just a cap on
# the reply (see `app/llm.py`'s `get_llm` note, and the budget block above).
# `tests/test_evaluator_budget.py` imports THIS constant rather than pinning
# its own literal, so the call site and the test that budgets it cannot
# silently disagree the way `max_tokens=4096` vs. a stale `_MAX_TOKENS = 2048`
# once did.
EVALUATION_MAX_TOKENS = 4096

_EVALUATION_SYSTEM_PROMPT = """You are scoring ONE answer a PM candidate gave in a live product strategy interview, \
against a fixed five-dimension rubric. You are not coaching, not replying to the candidate, and \
not continuing the interview. Your entire output is the evaluation.

Work in this order. The order matters.

STEP 1 - DECIDE WHAT THE ANSWER ACTUALLY GIVES YOU EVIDENCE FOR.
Read the answer and ask, for each of the five dimensions, whether the candidate said something \
that dimension can be scored on. Most answers give evidence for two or three of the five. That is \
normal and it is what a real interview looks like.

A dimension with no evidence goes in not_assessed. LISTING A DIMENSION AS NOT ASSESSED IS A \
CORRECT AND COMPLETE RESULT, not a failure and not a gap for you to fill. A number invented for a \
dimension nobody said anything about is worse than no number, because it carries the rubric's \
authority and none of its meaning. Do not stretch an unrelated sentence to cover a dimension. If \
you cannot point at a sentence, the dimension is not assessed.

🔴 THE ONE DISTINCTION THAT MATTERS HERE. Not assessed means THE TOPIC NEVER CAME UP. It does not \
mean the candidate handled it badly. If the question put something on the table and the candidate \
avoided it, that is a failure you watched happen and you score it at the bottom of the range. If \
the interview simply never went near it, that is a coverage gap and it is not assessed. Work out \
which of the two you are looking at before reaching for not_assessed.

Every one of the five dimensions must appear exactly once: either scored, or in not_assessed. \
Never both, never neither.

STEP 2 - QUOTE BEFORE YOU SCORE.
For each dimension you are scoring, find the sentence in THE CANDIDATE'S ANSWER that is your \
evidence, and copy it into evidence_quote CHARACTER FOR CHARACTER.

- Copy from the candidate's answer only. Never from the question, never from the case world, \
never from your own words.
- Copy exactly what is written, including any typo, odd spacing, or unusual punctuation. Do not \
tidy it, do not shorten it with an ellipsis, do not join two sentences that were not adjacent.
- The quote is checked against the transcript byte for byte. A quote with one word changed counts \
as a fabricated quote.
- If no sentence supports the score, you do not have a score. Go back to step 1 and put that \
dimension in not_assessed.

STEP 3 - SCORE AGAINST THE ANCHORS, AT THIS CANDIDATE'S LEVEL.
1 = Strong No Hire, 2 = No Hire, 3 = Hire, 4 = Strong Hire.

business_model_fluency
  1  No grasp of how the company makes money
  4  Revenue mechanics are load-bearing in the recommendation, not decoration
market_accuracy
  1  Invents or misreads the competitive landscape
  4  Correctly reads the given market, identifies the real structural threat
decision_quality
  1  Hedges, or picks without stating criteria
  4  Commits to one option, states criteria first, names what is being given up
     🔴 THE OPENING ANSWER ONLY: if the question asked the candidate to choose, this dimension is \
ALWAYS SCORED. Never put it in not_assessed. Refusing to choose is not missing evidence, it IS the \
evidence, and it scores at the bottom of the range:
       lists the options but never picks one to defend    ->  2
       does not even lay out the options                  ->  1
     A candidate is expected to make a choice and defend it. Dodging a question that demanded one \
is a failure you observed, not a topic that never came up.
     🔴 ON A FOLLOW-UP, THAT RULE DOES NOT APPLY. You are told above which one this is. The choice \
was made earlier and the probe did not ask for a new one. Score what the follow-up does WITH the \
decision:
       4  defends it with new reasoning, revises it and says why, or names what would change it
       3  holds the decision and adds substance, but nothing new about the decision itself
       2  restates the earlier decision without advancing it
       1  abandons the decision under pressure with no reason, or contradicts it unknowingly
     Restating the original choice is NOT required on a follow-up, and its absence is NOT a \
failure.
structural_clarity
  1  Rambles, and the interviewer has to drag the answer forward
  4  States the approach up front, signposts transitions, adapts structure to the prompt
     NARRATING A FRAMEWORK IS NOT STRUCTURE. An answer whose signposts are the steps of a named \
method ("first RICE, then build versus buy, then a two-by-two") has borrowed a shape rather than \
adapted one to this prompt, and it scores LOW here, not high. Structure means the argument is \
organised. Reciting a method is a substitute for organising it.
point_of_view
  1  Restates the prompt back, with no thesis
  4  Has a defensible thesis and sharpens it under pushback

The five dimensions never change with seniority. The bar inside each one does:
  APM        the bar is potential. Structured thinking and a stated choice clear it.
  PM         owns a decision and the criteria behind it without being asked for them.
  Senior PM  revenue mechanics are expected to be load-bearing, and the trade-off being given \
up must be named out loud.
  GPM        expects second-order effects, portfolio-level reasoning, and a thesis that holds \
under pushback.

THE SAME ANSWER SCORES LOWER AT A HIGHER LEVEL. An answer you would call a 3 at PM is a 2 at \
Senior PM unless it clears the higher bar on its own terms.

STEP 4 - FRAMEWORK NARRATION, RECORDED SEPARATELY.
Set framework_narration TRUE when the candidate names a method and describes running it, rather \
than just doing the thinking. Any of these on its own is enough:
- naming a framework and listing its letters or steps ("a RICE analysis, scoring Reach, Impact, \
Confidence and Effort", "now I'll do the C in CIRCLES", "step two of my SWOT")
- announcing a method they then never fill in with this company's actual numbers
- naming two or more frameworks in one answer

It is FALSE when the candidate simply reasons well and never names a method. Internalized \
structure is not narration, and a candidate can be highly structured without ever naming anything.

Judge this on the words in the answer, not on whether the reasoning was good. A strong answer can \
narrate and a weak one can avoid it. Recording it is not a penalty you are applying; it is an \
observation the scorecard reports on its own, and it must never move any of the five scores.

reasoning: one or two plain sentences saying what the quote shows and why it lands on that \
number. Never use an em dash.

Scores already assigned earlier in this same interview are given to you as context for the ARC of \
the interview, so you can see whether a thesis is being sharpened or merely repeated. Score THIS \
answer only. Do not re-score the earlier ones."""


def _render_prior_scores(prior_scores: list[dict]) -> str:
    """The running summary as the prompt sees it. An empty list is SAID OUT
    LOUD rather than rendered as `[]`: the first answer of an interview is the
    common case, and a bare `[]` under a heading about earlier scores reads as
    a gap the model might try to fill."""
    if not prior_scores:
        return "(none yet - this is the first answer being scored)"
    return json.dumps(prior_scores, indent=2)


_OPENING_ANSWER_NOTICE = "THIS IS THE OPENING ANSWER to the question above."
_FOLLOWUP_ANSWER_NOTICE = (
    "THIS IS A FOLLOW-UP ANSWER. The candidate already answered the main question earlier in "
    "this interview and committed to a choice, and the interviewer then probed. Do not expect a "
    "fresh choice here."
)


def _build_evaluation_messages(
    case_world: dict,
    question: str,
    answer: str,
    assessed_level: str,
    prior_scores: list[dict],
    *,
    is_followup: bool = False,
) -> list[tuple[str, str]]:
    """Pure message assembly, split out from `evaluate_answer` so the token
    budget can be measured offline against `tiktoken`, with no LLM call --
    same reason `_build_probe_messages` is split out in
    `app/agents/interviewer.py`. `tests/test_evaluator_budget.py` calls this
    directly; the numbers it reproduces are the ones in the budget comment
    above.

    `is_followup` decides which of the two notices below is placed immediately
    before the candidate's answer -- not appended after it, and never folded
    into the answer text itself, so the model cannot mistake the notice for
    something the candidate said. This is what fixes the bug where every
    probe answer was scored as if it were a fresh opening answer: the
    `decision_quality` rubric's "the question demanded a choice" guard fires
    on the phrasing of `question` alone, which is the SAME `main_question` for
    every probe in an interview, so without this notice the guard is
    permanently true and every follow-up that elaborates an already-made
    decision scores at the bottom of the range.
    """
    notice = _FOLLOWUP_ANSWER_NOTICE if is_followup else _OPENING_ANSWER_NOTICE
    human = (
        "Case world (read only, the ground truth the answer is scored against):\n"
        + json.dumps(case_world, indent=2)
        + "\n\nThe question the candidate was asked: "
        + question
        + "\n\nCandidate level: "
        + assessed_level
        + "\n\nScores already assigned earlier in this interview:\n"
        + _render_prior_scores(prior_scores)
        + "\n\n"
        + notice
        + "\n\nThe candidate's answer to score:\n"
        + answer
    )
    return [("system", _EVALUATION_SYSTEM_PROMPT), ("human", human)]


async def evaluate_answer(
    case_world: dict,
    question: str,
    answer: str,
    assessed_level: str,
    prior_scores: list[dict],
    *,
    role: Role = "fast",
    is_followup: bool = False,
) -> AnswerEvaluation:
    """Scores ONE candidate answer against the five-dimension rubric.

    `is_followup`: False for the opening answer to a question, True for a
    probe answer. `build.py`'s `evaluate_answer_node` derives this from
    `followup_count > 0`, since `ask_probe` is what increments it -- see that
    node's docstring. Threaded straight through to `_build_evaluation_messages`,
    which is where the actual notice text lives.

    Pure function: no DB, no session, no `agent_events` row, no side effects
    -- same contract as `answer_clarification` and `generate_probe`. The
    graph node and the `answer_evaluations` write are story 4.3, not this
    module's. `tests/golden/evaluator/test_golden.py` calls this directly with
    no session and no database, so a DB call here would break every case.

    The positional order (`case_world, question, answer, assessed_level,
    prior_scores`, keyword `role`) is fixed by that golden suite's call site.

    `prior_scores` is the RUNNING SUMMARY of the interview so far -- the
    dimensions already evidenced, with their scores and quotes. It is NEVER
    the raw transcript (PHASE-4-SPEC.md § "WHAT THE LIVE INTERVIEW ALREADY
    DECIDED" #3), and that is exactly why this call fits the ceiling: it is
    bounded at five short entries however long the interview runs, where the
    full transcript measured 10,274 tokens and did not fit. `[]` means this is
    the first answer being scored.

    `case_world` is READ ONLY, same rule as every other agent: it was written
    once by the Case Architect and is immutable after Phase 2 (ARCHITECTURE
    §2). This function never mutates it, and neither may its caller.

    `max_tokens=EVALUATION_MAX_TOKENS` (4096): see the measured budget block
    above for the arithmetic, and `generate_probe`'s docstring for why arguing
    this DOWN from the size of the output schema is wrong. On gpt-oss it is a
    reasoning-plus-output budget, not an output cap, and reasoning scales with
    the INPUT. Lowering it buys nothing the budget needs and reproduces the
    `json_validate_failed` of 2026-08-06, which names the prompt and is not a
    prompt problem.

    Raises `ValueError` on an empty `case_world`, a blank `question` or
    `answer`, or an `assessed_level` outside the four known levels, rather
    than scoring against nothing or against an anchor that does not exist.
    """
    if not case_world:
        raise ValueError("evaluate_answer requires a non-empty case_world")
    if not question or not question.strip():
        raise ValueError("evaluate_answer requires a non-empty question")
    if not answer or not answer.strip():
        raise ValueError("evaluate_answer requires a non-empty answer")
    if assessed_level not in ("APM", "PM", "Senior PM", "GPM"):
        raise ValueError(
            f"evaluate_answer got assessed_level={assessed_level!r}; expected one of "
            f"'APM', 'PM', 'Senior PM', 'GPM' -- the rubric's bar is set per level, so an "
            f"unknown level has no anchors to score against"
        )

    # EVALUATION_MAX_TOKENS (4096), not 2048: `gpt-oss-20b` is a reasoning model
    # and its reasoning tokens come out of the SAME output budget as the JSON.
    # On a realistic answer (~250 words) the reasoning exhausted 2048 before any
    # JSON was emitted, and Groq returned `failed_generation: ''` -- an EMPTY
    # body, not a truncated one. Observed 2026-08-10 in a human-paced live
    # interview with ZERO rate-limit errors, so it is not the TPM artifact the
    # same shape was blamed on twice before. The test suite never caught it
    # because its fixtures answer with "Answer number 1." See DEV-STATE
    # § Decisions 2026-08-10.
    llm = get_llm(role, max_tokens=EVALUATION_MAX_TOKENS, agent="evaluator").with_structured_output(
        AnswerEvaluation
    )
    messages = _build_evaluation_messages(
        case_world, question, answer, assessed_level, prior_scores, is_followup=is_followup
    )
    return await llm.ainvoke(messages)
