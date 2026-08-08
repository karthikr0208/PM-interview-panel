"""Evaluator -- scores a candidate's answer against the PRD §7 rubric: five
dimensions, 1 to 4, each score carrying a verbatim quote from the transcript.

🔴 STORY 4.1 SCOPE ONLY. This module holds the `AnswerEvaluation` /
`DimensionScore` schema and nothing else. There is no `evaluate_answer`
function here -- that is story 4.2's job (PHASE-4-SPEC.md), once the
per-answer call has been measured against the 8,000 TPM ceiling and `fast`
vs `deep` has been measured on real fixtures. Importing this module is safe
today (no LLM client, no network) precisely because it is a schema, not an
agent -- `tests/golden/evaluator/cases.py` and `assertions.py` import it
directly at module level, unlike `app.agents.interviewer`'s
`answer_clarification`, which those suites' equivalents had to import
lazily while the AGENT (not merely its schema) did not exist yet.

`tests/golden/evaluator/test_golden.py` still lazily imports `evaluate_answer`
from THIS module inside a fixture -- that name does not exist here, so any
attempt to actually run the live golden suite fails loudly with
`ImportError`, which is this story's acceptance criterion (PHASE-4-SPEC.md
4.1: "the suite is deliberately RED at the end of this story").

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

from pydantic import BaseModel, Field, model_validator

from app.agents.planner import RUBRIC_DIMENSIONS, RubricDimension


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
