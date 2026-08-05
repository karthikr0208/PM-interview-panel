"""Golden-case suite for the Interviewer agent's clarification behaviour.
Run with `make golden AGENT=interviewer` or `pytest tests/golden/interviewer -v`.

Hits the real Groq endpoint (`@pytest.mark.live`) once per case against
`app.agents.interviewer.answer_clarification`. Five fixed
`(case_world, planned_question, clarifying_question)` inputs, per
AGENT-INTERVIEWER-SPEC.md §5, reusing Phase 2's hand-written case worlds
(via `tests/golden/interviewer/cases.py`'s `case_world` property), checked
against the universal assertions §5 specifies (apply to every case, no
exceptions) plus the case table in `cases.py`.

Only `answer_clarification` is exercised here, not `ask_question` -- spec
§2a: asking the planned question is deterministic Python (the question is
emitted verbatim, never rewritten by the model), so it has nothing for a
golden suite to check. The bridge (§2a's only other LLM call) is candidate
small talk with no grounding risk by design (it receives no case_world).
The clarification answer is "the real work, and the whole risk" (spec
§2b) -- this suite exists for it alone.

CRITICAL -- collection must stay clean: `app.agents.interviewer` does not
exist yet as this suite is written (story 3.1; the agent is story 3.2's
job). A module-level `from app.agents.interviewer import ...` would make
`pytest tests -m "not live"` ERROR during collection -- deselection happens
after collection, so it would not save this file, it would break the
project's fastest feedback loop for every file. The import is therefore
lazy, inside the session-scoped `answer_clarification` fixture below:
collection succeeds unconditionally, and only actually running a `live`
test raises (loudly, as `ModuleNotFoundError`, naming exactly the missing
module).

Deliberately NOT `pytest.importorskip`: once `app.agents.interviewer`
exists but is misnamed or mis-exported, `importorskip` would silently skip
forever, and a silently-skipped golden suite is worse than no suite --
nobody would notice the gate stopped gating. See planner's, case_architect's
and resume_analyst's identical choice.

Role: `GOLDEN_ROLE` env var, "fast" default -- NOTE this differs from the
other three suites' "deep" default. AGENT-INTERVIEWER-SPEC.md §1/§8 and
PHASE-3-SPEC.md are explicit that this is the one agent where ARCHITECTURE
§4's table and the portfolio calibration agree: `fast` is the only model
this product runs while a candidate is watching a cursor. §8 flags that
`fast` holding the three-field `ClarificationAnswer` schema is UNMEASURED
(the Planner needed `deep` for its much larger `QuestionPlan` and that was
a surprise) -- story 3.2's job, not this one's.
"""
from __future__ import annotations

import asyncio
import logging
import os

import pytest

from tests.golden.interviewer.assertions import (
    contains_any_figure,
    contains_banned_register_name,
    contains_fake_round_number,
    grounded_in_is_empty,
    missing_grounding,
    no_dash_variants,
    ungrounded_figures,
)
from tests.golden.interviewer.cases import CASES

GOLDEN_ROLE = os.environ.get("GOLDEN_ROLE", "fast")
print(f"\n[golden/interviewer] GOLDEN_ROLE={GOLDEN_ROLE}")

pytestmark = pytest.mark.live


@pytest.fixture(scope="session")
def answer_clarification():
    """Imported here, not at module level -- see module docstring."""
    from app.agents.interviewer import answer_clarification as fn

    return fn


# ==============================================================================
# Pacing arithmetic, per AGENT-INTERVIEWER-SPEC.md §6 (not re-derived here --
# cross-referenced, matching this project's own discipline against restating
# spec numbers as prose that can drift from the source).
#
# The clarification call's input is `case_world` + the current question only
# (§2b: "It reads case_world and the current question, and nothing else" --
# never the transcript). Measured input ceiling ~1,150 tokens, `max_tokens`
# projected at 2,048 (§6's table). Requested = prompt + input + max_tokens
# against the 8,000 TPM bucket, refilling at 133.3 tokens/sec.
#
# §6: "a 60-second pace is sufficient -- the same figure resume_analyst
# settled on after measuring a real header, and safe here only because this
# call is materially smaller than the Planner's, which needed 90." This
# suite has no measured `Requested` header yet (the agent does not exist),
# so 60s is a pre-launch estimate per spec §6, not a re-derivation of
# resume_analyst's measured one -- re-measure once `app.agents.interviewer`
# is real (story 3.2), the same way resume_analyst's projected pacing was
# eventually replaced by an observed one.
# ==============================================================================
_PACE_SECONDS = 60


@pytest.fixture(autouse=True)
async def _pace_for_tokens_per_minute():
    yield
    await asyncio.sleep(_PACE_SECONDS)


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_golden_case(case, answer_clarification, caplog) -> None:
    # Loaded ONCE into a local so the immutability check below compares
    # this exact object (the one passed into the call, and therefore the
    # one a misbehaving implementation would mutate in place) against a
    # fresh read from disk -- not two independent disk reads, which would
    # trivially match regardless of what the call did.
    case_world = case.case_world

    with caplog.at_level(logging.INFO, logger="app.llm"):
        result = await answer_clarification(
            case_world,
            case.planned_question,
            case.clarifying_question,
            role=GOLDEN_ROLE,
        )

    # Same retry-observation shape as the other three golden suites: reads
    # the log this call already produced, no extra LLM call.
    retried = any(
        "outcome=empty" in r.getMessage() or "outcome=invalid" in r.getMessage()
        for r in caplog.records
        if r.name == "app.llm"
    )
    print(f"[golden/interviewer] {case.id}: role={GOLDEN_ROLE} retry_fired={retried}")

    # --- Immutability: story 3.2's first real test of the ARCHITECTURE §2
    # rule by this agent (spec §1: "case_world is READ ONLY, and this agent
    # is where that rule finally earns its keep"). `case_world` must be
    # byte-identical after the call; a mutation here would corrupt the
    # artifact every later agent (Evaluator, Coach) depends on.
    import json

    assert json.dumps(case_world, sort_keys=True) == json.dumps(
        case.case_world, sort_keys=True
    ), f"{case.id}: case_world was mutated by answer_clarification"

    # --- Vacuity floor, FIRST -- spec §5's ordering. grounded_in must be
    # non-empty on BOTH branches of can_answer, or the membership check
    # below would pass a refusal vacuously (spec §5's named escape hatch).
    assert not grounded_in_is_empty(result.grounded_in), (
        f"{case.id}: grounded_in is empty (can_answer={result.can_answer}) -- "
        f"the membership check below would pass this vacuously"
    )
    assert (result.answer or "").strip(), f"{case.id}: answer is blank"

    # --- Grounding: every grounded_in entry must appear in case_world ---
    missing = missing_grounding(result.grounded_in, case.case_world)
    assert not missing, (
        f"{case.id}: grounded_in entry not found in case_world (fabricated): {missing}"
    )

    # --- The figure check: every numeric token in `answer` must appear in
    # case_world (spec §5's "assertion with teeth") ---
    bad_figures = ungrounded_figures(result.answer, case.case_world)
    assert not bad_figures, (
        f"{case.id}: answer cites figure(s) not in case_world: {bad_figures} "
        f"in {result.answer!r}"
    )

    # --- can_answer=False must mean no figure at all, not just none that
    # fails grounding (spec §5) ---
    if result.can_answer is False:
        figures = contains_any_figure(result.answer)
        assert not figures, (
            f"{case.id}: can_answer=False but answer volunteers figure(s) "
            f"{figures}: {result.answer!r}"
        )

    # --- Candidate-facing copy hygiene: no dash variants, no fake-round
    # numbers, no banned-register names, on BOTH bridge (if present) and
    # answer (spec §4/§5) ---
    assert no_dash_variants(result.answer), (
        f"{case.id}: answer contains an em-dash or en-dash: {result.answer!r}"
    )
    # 🔴 `bridge` is NOT checked here, and its absence is a known gap, not an
    # oversight. Spec §5's assertion table reads "no em-dash or en-dash
    # anywhere in `bridge` or `answer`" as though one call produced both, but
    # §3 puts `bridge` on a separate `BridgeLine` schema from a separate call
    # (`ask_question`). This suite's inputs only exercise
    # `answer_clarification`, so there is no bridge here to check -- and a
    # `getattr(result, "bridge", None)` guard, which is what was written
    # first, is worse than nothing: it can only ever no-op, so it reads as
    # coverage while asserting nothing. That is story 1.3a's bug wearing a
    # different hat. Story 3.2 owes the bridge its own case shape; the spec
    # has been corrected to say so.

    fake_round = contains_fake_round_number(result.answer)
    assert fake_round is None, (
        f"{case.id}: answer cites a fake-round number ({fake_round!r}): {result.answer!r}"
    )
    banned_name = contains_banned_register_name(result.answer)
    assert banned_name is None, (
        f"{case.id}: answer cites a banned-register name ({banned_name!r}): {result.answer!r}"
    )

    # --- Case-specific assertion, spec §5's table ---
    case.check(result, case.case_world)


# ==============================================================================
# Cross-world control, live: the answer to fixture 1's clarifying question,
# checked against fixture 4's world, must FAIL grounding. Spec §5: "the
# single most valuable test" in the planner suite's equivalent. Kept as its
# own test (not folded into the parametrized loop above) so a single red
# case_id in CI output tells you immediately which control failed, matching
# planner's `test_good_plan_FAILS_grounding_against_a_different_world`
# being a standalone test rather than a parametrized one.
# ==============================================================================


async def test_cross_world_control_apm_answer_fails_against_gpm_world(
    answer_clarification, caplog
) -> None:
    apm_case = next(c for c in CASES if c.id == "apm_consumer_world")
    gpm_case = next(c for c in CASES if c.id == "gpm_portfolio_world")

    with caplog.at_level(logging.INFO, logger="app.llm"):
        result = await answer_clarification(
            apm_case.case_world,
            apm_case.planned_question,
            apm_case.clarifying_question,
            role=GOLDEN_ROLE,
        )

    missing = missing_grounding(result.grounded_in, gpm_case.case_world)
    assert missing, (
        "cross-world control: an answer generated for apm_consumer_world "
        "grounded successfully against gpm_portfolio_world -- it should be "
        "world-specific enough to fail"
    )
