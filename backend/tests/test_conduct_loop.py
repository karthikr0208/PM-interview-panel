"""Story 3.2: the conduct loop --
`ask_question -> await_candidate -> route_input -> {answer_clarification_node,
decide_next} -> ...`. Per PHASE-3-SPEC.md's test table:

  - `await_candidate` re-runs without re-asking -- assert on `app/llm.py`'s
    call log, NEVER on state. The trap named for this exact story: a loop
    that re-runs upstream work on resume looks correct from state, because
    the transcript still reads sensibly. `test_confirm_level.py`'s single
    interrupt already proved the general principle; this file proves it for
    the LOOPING interrupt specifically, which `falsify_looping_interrupt.py`
    (separately) proves the assertion below can actually fail against.
  - `route_input` splits clarify from answer -- pure, offline.
  - `decide_next` is deterministic and covered at its boundaries (question
    count, elapsed time, `dimension_coverage` is read but does not gate) --
    pure, offline, no graph needed.
  - the loop exits -- covered by `decide_next`'s question-count boundary
    offline, and end to end by the live test below.

Offline tests import `app.graph.build` directly and call `route_input` /
`decide_next` with hand-built `dict`s -- no graph, no checkpointer, no LLM.
Live tests build a real graph via `build_graph(checkpointer,
interviewer_role="fast")`, matching `test_confirm_level.py`'s graph-level
fixtures and cleanup pattern exactly (this file's `graph_sessions` fixture
is copied from there rather than imported, matching that file's own
precedent of not sharing test-only fixtures across modules).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterator

import psycopg
import pytest
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command

from app.config import settings
from app.graph.build import build_graph, decide_next, route_input

# ═══════════════════════════════════════════════════════════════════════
# route_input -- pure, offline.
# ═══════════════════════════════════════════════════════════════════════


def test_route_input_returns_clarify_for_a_clarify_reply() -> None:
    state = {"last_input": {"type": "clarify", "text": "how big is the team?"}}
    assert route_input(state) == "clarify"


def test_route_input_returns_answer_for_an_answer_reply() -> None:
    state = {"last_input": {"type": "answer", "text": "I would ship guest checkout first."}}
    assert route_input(state) == "answer"


def test_route_input_defaults_to_answer_on_missing_last_input() -> None:
    """Defensive: a malformed/absent payload must not stall the interview.
    Same "uniform failure behaviour" reasoning ARCHITECTURE §9 applies
    elsewhere -- fail toward progress, not toward a stuck session."""
    assert route_input({}) == "answer"


def test_route_input_defaults_to_answer_on_an_unrecognized_type() -> None:
    state = {"last_input": {"type": "something_else", "text": "..."}}
    assert route_input(state) == "answer"


# ═══════════════════════════════════════════════════════════════════════
# decide_next -- pure, offline, no LLM, no I/O. Covered at its boundaries:
# question count, elapsed time, and a sanity check that dimension_coverage
# does NOT gate the decision in this phase (spec §2c).
# ═══════════════════════════════════════════════════════════════════════


def _iso_minutes_ago(minutes: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


def test_decide_next_continues_below_the_question_count_boundary() -> None:
    state = {"current_q_idx": 2, "followup_count": 0, "dimension_coverage": {}}
    assert decide_next(state) == "ask"


def test_decide_next_exits_exactly_at_the_question_count_boundary() -> None:
    """`_QUESTIONS_THIS_PHASE` is 3 -- pins the boundary itself, not just
    values comfortably on either side of it."""
    state = {"current_q_idx": 3, "followup_count": 0, "dimension_coverage": {}}
    assert decide_next(state) == "exit"


def test_decide_next_exits_past_the_question_count_boundary() -> None:
    state = {"current_q_idx": 4, "followup_count": 0, "dimension_coverage": {}}
    assert decide_next(state) == "exit"


def test_decide_next_continues_when_time_budget_is_not_exceeded() -> None:
    state = {
        "current_q_idx": 1,
        "followup_count": 0,
        "dimension_coverage": {},
        "started_at": _iso_minutes_ago(5),
    }
    assert decide_next(state) == "ask"


def test_decide_next_exits_when_the_time_budget_is_exceeded_even_below_question_count() -> None:
    """The safety valve: a candidate deep in clarifications, still short of
    `_QUESTIONS_THIS_PHASE`, must not run the interview forever."""
    state = {
        "current_q_idx": 1,
        "followup_count": 0,
        "dimension_coverage": {},
        "started_at": _iso_minutes_ago(41),
    }
    assert decide_next(state) == "exit"


def test_decide_next_with_no_started_at_falls_back_to_question_count_only() -> None:
    """`started_at` absent (defensive -- should always be set by
    `ask_question`'s question 1) must not crash the decision; it just can't
    apply the time-based exit."""
    state = {"current_q_idx": 1, "followup_count": 0, "dimension_coverage": {}}
    assert decide_next(state) == "ask"


@pytest.mark.parametrize(
    "coverage",
    [
        {},
        {"business_model_fluency": 1},
        {"business_model_fluency": 1, "market_accuracy": 1, "decision_quality": 1,
         "structural_clarity": 1, "point_of_view": 1},
    ],
)
def test_decide_next_does_not_gate_on_dimension_coverage(coverage: dict) -> None:
    """Spec §2c: coverage is read, not yet a gate -- scores don't exist
    until Phase 4. Pins that varying it, holding q_idx and time fixed,
    never changes the outcome in this phase."""
    state = {"current_q_idx": 1, "followup_count": 0, "dimension_coverage": coverage}
    assert decide_next(state) == "ask"


def test_decide_next_asserts_followup_count_is_zero() -> None:
    """Positive control for the internal assertion: no probe edge exists in
    this graph (spec §2c), so a nonzero followup_count means a real bug --
    something wrote to a field this graph has no edge to act on. Must
    raise loudly, not silently ignore it."""
    state = {"current_q_idx": 1, "followup_count": 1, "dimension_coverage": {}}
    with pytest.raises(AssertionError):
        decide_next(state)


# ═══════════════════════════════════════════════════════════════════════
# Live: graph-level fixtures, same shape as test_confirm_level.py's
# `graph_sessions` -- a real `sessions` row is required because
# `ask_question` and `answer_clarification_node` write `agent_events` and
# `transcript_turns`, both FK'd to `sessions`.
# ═══════════════════════════════════════════════════════════════════════

LEVEL = "PM"

CASE_WORLD = {
    "company": {"name": "Palewell Analytics", "one_line": "usage analytics for mid-market SaaS"},
    "market": {"description": "B2B analytics", "size_usd": "$2.1B"},
    "metrics": {"arr_usd": "$6.4M", "customer_count": 340, "monthly_churn_pct": 4.6},
    "situation": {
        "prompt": "Should Palewell Analytics build a native mobile dashboard this quarter?",
        "tension": "Mobile usage is rising but engineering capacity is fixed.",
        "options": ["Build mobile now", "Ship a mobile web view", "Defer to next quarter"],
        "constraints": ["No net-new headcount this quarter"],
        "leadership_belief": "Leadership believes mobile is table stakes for renewal.",
    },
    "supporting_facts": [
        "Monthly churn is 4.6%, the highest of any month since launch.",
        "340 paying customers as of this quarter.",
    ],
}

QUESTION_PLAN = [
    {
        "idx": 0,
        "question": "Given Palewell Analytics' 4.6% monthly churn, how would you prioritize the mobile dashboard decision?",
        "intent": "surfaces prioritization under a fixed constraint",
        "primary_dimension": "decision_quality",
        "probe_angles": ["What tradeoff would you make first?"],
        "grounded_in": ["Monthly churn is 4.6%, the highest of any month since launch."],
        "minutes": 8,
    },
    {
        "idx": 1,
        "question": "How would you validate demand for a native mobile dashboard at Palewell Analytics before committing engineering time?",
        "intent": "surfaces validation instincts",
        "primary_dimension": "structural_clarity",
        "probe_angles": ["What signal would change your mind?"],
        "grounded_in": ["340 paying customers as of this quarter."],
        "minutes": 8,
    },
    {
        "idx": 2,
        "question": "If Palewell Analytics' leadership is wrong that mobile is table stakes, how would you know?",
        "intent": "surfaces point of view under disagreement",
        "primary_dimension": "point_of_view",
        "probe_angles": ["What would falsify leadership's belief?"],
        "grounded_in": ["Leadership believes mobile is table stakes for renewal."],
        "minutes": 8,
    },
]


def _config(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}


@pytest.fixture
def loop_sessions() -> Iterator[Callable[[], str]]:
    """Mints a session already past `plan_interview` -- `sessions`,
    `resumes` (unused by this loop but present for symmetry), `case_worlds`
    are not required by the loop's own nodes, so only `sessions` is seeded;
    `case_world` and `question_plan` are injected straight into the initial
    state passed to `graph.ainvoke`, the same way `test_confirm_level.py`
    seeds `resume_text` rather than driving the Resume Analyst for real.
    """
    created: list[str] = []

    def make() -> str:
        session_id = str(uuid.uuid4())
        conn = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "insert into sessions (id, status) values (%s, 'created')", (session_id,)
                )
            conn.commit()
        finally:
            conn.close()
        created.append(session_id)
        return session_id

    yield make

    if not created:
        return
    conn = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
    try:
        with conn.cursor() as cur:
            for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
                cur.execute(f"delete from {table} where thread_id = any(%s)", (created,))
            cur.execute("delete from sessions where id = any(%s)", (created,))
        conn.commit()
    finally:
        conn.close()


def _ok_llm_calls(caplog: pytest.LogCaptureFixture) -> list[str]:
    """Copied from `test_confirm_level.py`'s helper of the same name --
    only `outcome=ok` records, never every `llm_call` line, so a legitimate
    validate-retry does not read as a duplicate call. See that file's
    docstring for the full reasoning."""
    return [
        record.getMessage()
        for record in caplog.records
        if record.name == "app.llm"
        and record.getMessage().startswith("llm_call")
        and "outcome=ok" in record.getMessage()
    ]


def _initial_state(session_id: str) -> dict:
    return {
        "session_id": session_id,
        "case_world": CASE_WORLD,
        "question_plan": QUESTION_PLAN,
        "assessed_level": LEVEL,
    }


async def _start_at_the_loop(graph, config: dict, session_id: str) -> dict:
    """Drives the real graph to its first `await_candidate` pause without
    paying for the three agents upstream of the loop.

    `build_graph`'s entry point is `level_candidate`, so handing
    `_initial_state` straight to `ainvoke` starts the Resume Analyst and
    dies on `KeyError: 'resume_text'` -- which is how these three tests were
    originally written, and they had never been run (fixed 2026-08-05).

    Seeding the checkpoint `as_node="plan_interview"` instead is the right
    shape rather than merely a working one: LangGraph resumes from the real
    `plan_interview -> ask_question` edge, so the loop's own wiring is still
    under test. Only the three upstream agents are skipped, and their cost
    is ~11,000 `deep` tokens per run that would buy this file nothing --
    the same reasoning `test_confirm_level.py` uses when it seeds
    `resume_text` rather than driving an upload for real.
    """
    await graph.aupdate_state(config, _initial_state(session_id), as_node="plan_interview")
    return await graph.ainvoke(None, config)


@pytest.mark.live
async def test_the_loop_asks_two_to_three_questions_and_exits(
    checkpointer: AsyncPostgresSaver, loop_sessions: Callable[[], str]
) -> None:
    """End-to-end shape of the loop: starts at `ask_question`, pauses at
    `await_candidate` after question 1 with ZERO LLM calls (spec §2a --
    nothing to bridge from yet), then two plain answers drive it through
    questions 2 and 3, then exits with no further interrupt."""
    session_id = loop_sessions()
    graph = build_graph(checkpointer, interviewer_role="fast")
    config = _config(session_id)

    started = await _start_at_the_loop(graph, config, session_id)
    assert "__interrupt__" in started, "graph did not pause at await_candidate for question 1"
    q1 = started["__interrupt__"][0].value
    assert q1["kind"] == "question"
    assert q1["text"] == QUESTION_PLAN[0]["question"], "question 1 was not emitted verbatim"

    r2 = await graph.ainvoke(Command(resume={"type": "answer", "text": "I'd ship the web view first."}), config)
    assert "__interrupt__" in r2, "graph did not pause for question 2"
    q2 = r2["__interrupt__"][0].value
    assert q2["kind"] == "question"
    assert QUESTION_PLAN[1]["question"] in q2["text"], "question 2 was not present verbatim"

    r3 = await graph.ainvoke(Command(resume={"type": "answer", "text": "I'd run a two-week beta."}), config)
    assert "__interrupt__" in r3, "graph did not pause for question 3"
    q3 = r3["__interrupt__"][0].value
    assert QUESTION_PLAN[2]["question"] in q3["text"]

    final = await graph.ainvoke(Command(resume={"type": "answer", "text": "I'd track renewal rate."}), config)
    assert "__interrupt__" not in final, "the loop should have exited after 3 questions"
    assert final["current_q_idx"] == 3


@pytest.mark.live
async def test_a_clarifying_question_does_not_advance_current_q_idx(
    checkpointer: AsyncPostgresSaver, loop_sessions: Callable[[], str]
) -> None:
    """A clarification must not consume a question slot (spec §8's open
    question, resolved "no" for Phase 3): `current_q_idx` stays at 1 (the
    count after question 1 was asked) through a full clarify/answer round
    on the SAME question."""
    session_id = loop_sessions()
    graph = build_graph(checkpointer, interviewer_role="fast")
    config = _config(session_id)

    await _start_at_the_loop(graph, config, session_id)
    state = await graph.aget_state(config)
    assert state.values["current_q_idx"] == 1

    clarified = await graph.ainvoke(
        Command(resume={"type": "clarify", "text": "How big is Palewell's customer base?"}), config
    )
    assert "__interrupt__" in clarified
    answer_payload = clarified["__interrupt__"][0].value
    assert answer_payload["kind"] == "clarification"

    state_after_clarify = await graph.aget_state(config)
    assert state_after_clarify.values["current_q_idx"] == 1, (
        "a clarification advanced current_q_idx -- it must consume no question slot"
    )


@pytest.mark.live
async def test_await_candidate_does_not_redo_the_clarification_call_when_the_real_answer_resumes(
    checkpointer: AsyncPostgresSaver,
    loop_sessions: Callable[[], str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """THE trap named for story 3.2. `falsify_single_call.py` (story 1.4)
    already proves the general single-interrupt property can fail; this is
    the LOOPING case PHASE-3-SPEC.md 3.2 says needs its own proof:
    `answer_clarification_node`'s LLM call must fire exactly once, even
    though `await_candidate` (immediately downstream, and the node that
    pauses again right after it) gets resumed a SECOND time in the same
    question's turn -- once to deliver the clarification, once more to
    deliver the real answer. A duplicated `answer_clarification` call would
    be invisible in `messages`/`transcript_turns` (both would still read as
    exactly one clarification exchange); only `app.llm`'s call log sees it.
    Assert there, never on state -- same rule as test_confirm_level.py's
    equivalent test, restated in the docstring `falsify_looping_interrupt.py`
    exists to prove is not vacuous.

    Drives all the way to question 3 (2 bridge calls) THEN clarifies (1
    call, total 3) so that the final real answer triggers `decide_next` ->
    "exit" with NO further legitimate call to muddy the count -- isolating
    the one question this test asks: did the resume re-fire the
    clarification call. It must stay at 3.
    """
    session_id = loop_sessions()
    graph = build_graph(checkpointer, interviewer_role="fast")
    config = _config(session_id)

    with caplog.at_level(logging.INFO, logger="app.llm"):
        await _start_at_the_loop(graph, config, session_id)
        assert len(_ok_llm_calls(caplog)) == 0, "question 1 must cost zero LLM calls"

        await graph.ainvoke(Command(resume={"type": "answer", "text": "I'd ship the web view first."}), config)
        assert len(_ok_llm_calls(caplog)) == 1, "question 2's bridge should be the first LLM call"

        await graph.ainvoke(Command(resume={"type": "answer", "text": "I'd run a two-week beta."}), config)
        assert len(_ok_llm_calls(caplog)) == 2, "question 3's bridge should be the second LLM call"

        await graph.ainvoke(
            Command(resume={"type": "clarify", "text": "How big is Palewell's customer base?"}), config
        )
        calls_after_clarify = len(_ok_llm_calls(caplog))
        assert calls_after_clarify == 3, (
            f"expected exactly one answer_clarification call (3 total), got {calls_after_clarify}"
        )

        # The real answer resumes `await_candidate` a SECOND time for this
        # SAME (final) question, and `current_q_idx` is already 3, so
        # `decide_next` exits with NO further ask_question/bridge call. If
        # `await_candidate` (or anything upstream of it on this resume)
        # re-ran `answer_clarification_node`'s LLM call, this count would
        # jump to 4 here -- it must not.
        final = await graph.ainvoke(Command(resume={"type": "answer", "text": "About 340 customers."}), config)
        assert "__interrupt__" not in final, "the loop should have exited after question 3's real answer"
        calls_after_real_answer = len(_ok_llm_calls(caplog))
        assert calls_after_real_answer == 3, (
            "resuming await_candidate with the real answer re-ran an LLM call -- "
            f"expected the clarification count to stay at 3, got {calls_after_real_answer}"
        )
