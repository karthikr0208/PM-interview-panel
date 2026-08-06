"""Story 3.2: the conduct loop, extended by story 3.5.4 with the probe edge --
`ask_question -> await_candidate -> route_input -> {answer_clarification_node,
decide_next} -> {ask_question, ask_probe, exit}`. Per PHASE-3.5-SPEC.md's test
table:

  - `await_candidate` re-runs without re-asking -- assert on `app/llm.py`'s
    call log, NEVER on state. The trap named for this exact story: a loop
    that re-runs upstream work on resume looks correct from state, because
    the transcript still reads sensibly. `test_confirm_level.py`'s single
    interrupt already proved the general principle; this file proves it for
    the LOOPING interrupt specifically -- first for a clarification
    (`falsify_looping_interrupt.py`), and as of 3.5.4 for a PROBE too, which
    that script does NOT cover (it only ever exercised `answer_clarification`,
    the only LLM call that existed in the loop before this story).
  - `route_input` splits clarify from answer -- pure, offline.
  - `_messages_to_turns` converts `messages` (LangChain message objects) into
    the `{"role", "text"}` shape `generate_probe` expects -- pure, offline,
    unit-tested directly per the brief's own named risk (a wrong attribute
    read would silently produce empty text and a probe would still look
    plausible).
  - the improvised-fact append rule: `answer_clarification_node` appends to
    `improvised_facts` on `result.improvised_fact` being non-empty, NEVER on
    `can_answer` -- pinned with fixtures that deliberately invert the normal
    correlation between the two fields, per DEV-STATE's live measurement.
  - `improvised_facts` accumulates rather than replaces -- the `operator.add`
    reducer, tested directly against a tiny two-node graph, no LLM.
  - `decide_next` is deterministic and covered at its boundaries (probe
    count, elapsed time, the one-time "ask" edge, `dimension_coverage` is
    read elsewhere and does not gate here) -- pure, offline, no graph needed.
  - the loop exits -- covered by `decide_next`'s probe-count boundary
    offline, and end to end by the live tests below.

Offline tests import `app.graph.build` directly and call `route_input` /
`decide_next` / `_messages_to_turns` with hand-built `dict`s and message
objects -- no graph, no checkpointer, no LLM. A second offline tier
monkeypatches `app.graph.build.rest_insert` (and, where needed,
`_answer_clarification` / `generate_probe`) to drive the real NODE closures
with no database and no network -- same pattern as
`test_curated_worlds.py`'s `recorded_inserts` fixture.

Live tests build a real graph via `build_graph(checkpointer,
interviewer_role="fast")`, matching `test_confirm_level.py`'s graph-level
fixtures and cleanup pattern exactly (this file's `graph_sessions` fixture
is copied from there rather than imported, matching that file's own
precedent of not sharing test-only fixtures across modules).

🔴 Per the story 3.5.4 brief: live tests below are WRITTEN, not RUN. A whole
interview now costs real `fast` tokens per probe turn (generate_probe is a
real LLM call, unlike the pre-3.5.4 `ask_question`), and this file's own
offline half is the free loop -- `pytest tests -m "not live"`.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterator

import psycopg
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, StateGraph
from langgraph.types import Command

from app.agents.interviewer import _TRANSITIONS, ClarificationAnswer, Probe, compose_question, transition_for
from app.config import settings
from app.graph.build import (
    _make_answer_clarification_node,
    _make_ask_probe,
    _messages_to_turns,
    build_graph,
    decide_next,
    route_input,
)
from app.graph.state import InterviewState

# ═══════════════════════════════════════════════════════════════════════
# transition_for / compose_question -- pure, offline, no LLM at all.
#
# These replaced `write_bridge` on 2026-08-05 after it was measured to be a
# constant function (DEV-STATE § Decisions). The tests below pin the two
# properties that made the replacement safe: question 1 still opens cold,
# and the Planner's question text still survives byte for byte.
# ═══════════════════════════════════════════════════════════════════════


def test_question_one_has_no_transition() -> None:
    """Question 1 opens the interview and has nothing to transition from --
    the same property the bridge had, kept deliberately."""
    assert transition_for(0) is None


def test_later_questions_get_a_transition() -> None:
    for q_idx in range(1, 8):
        assert transition_for(q_idx) in _TRANSITIONS


def test_consecutive_transitions_differ() -> None:
    """The defect that killed the LLM bridge was repetition: consecutive
    turns produced "Understood, thanks for sharing that. Let's continue."
    twice in a row. Rotating guarantees mechanically what prompting failed
    to deliver -- for any run shorter than the tuple, no line repeats."""
    lines = [transition_for(i) for i in range(1, len(_TRANSITIONS) + 1)]
    assert len(set(lines)) == len(lines), f"a transition repeated within one rotation: {lines}"


def test_transition_for_is_total_and_deterministic() -> None:
    """No clock, no randomness, no state: the same index always gives the
    same line, so a transcript is reproducible from `q_idx` alone."""
    assert transition_for(5) == transition_for(5)
    assert transition_for(99) in _TRANSITIONS


def test_compose_question_emits_the_planned_question_byte_for_byte() -> None:
    """Spec §2a's central rule, and the reason `ask_question` is
    deterministic at all: the Planner's string already passed five checks,
    so nothing here may alter it."""
    planned = "At Ferngrove Media, how would you weigh the 11.3% day-2 return rate?"
    assert compose_question(planned, None) == planned
    assert compose_question(planned, "Thanks. Next one.").endswith(planned)


def test_compose_question_keeps_the_transition_and_question_separate() -> None:
    """A candidate must be able to tell the acknowledgement from the
    question. Blank line, not a run-on sentence."""
    composed = compose_question("Why?", "Thanks. Next one.")
    assert composed == "Thanks. Next one.\n\nWhy?"


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
# _messages_to_turns -- pure, offline. Story 3.5.4's own named risk: graph
# state holds LangChain `AIMessage`/`HumanMessage` OBJECTS with a `.content`
# attribute, while the DB's transcript rows use `"content"` as a dict KEY and
# `generate_probe` wants `"text"` -- three different names for the same
# thing across three call sites. A converter that read the wrong one would
# silently produce empty strings, and a probe built from an empty transcript
# still reads as plausible prose, so nothing downstream would notice.
# ═══════════════════════════════════════════════════════════════════════


def test_messages_to_turns_maps_roles_and_preserves_text() -> None:
    messages = [
        AIMessage(content="What is Reddit's biggest threat?", additional_kwargs={"kind": "question"}),
        HumanMessage(content="I'd point to Discord's AI features."),
        AIMessage(content="Say more about Discord specifically.", additional_kwargs={"kind": "probe"}),
    ]
    assert _messages_to_turns(messages) == [
        {"role": "interviewer", "text": "What is Reddit's biggest threat?"},
        {"role": "candidate", "text": "I'd point to Discord's AI features."},
        {"role": "interviewer", "text": "Say more about Discord specifically."},
    ]


def test_messages_to_turns_text_is_non_empty() -> None:
    """The decisive assertion for the brief's named risk: not just that a
    `"text"` key exists, but that it actually carries the message's content
    rather than an empty string a wrong-attribute read would produce."""
    turns = _messages_to_turns([HumanMessage(content="I'd ship the web view first.")])
    assert turns[0]["text"] == "I'd ship the web view first."
    assert turns[0]["text"] != ""


def test_messages_to_turns_handles_an_empty_list() -> None:
    assert _messages_to_turns([]) == []


def test_messages_to_turns_treats_every_non_human_message_as_the_interviewer() -> None:
    """Only `HumanMessage` is ever produced by the candidate in this graph
    (see `await_candidate`'s return) -- everything else, whatever its
    `kind` (question, probe, clarification), is the interviewer's turn."""
    turns = _messages_to_turns(
        [AIMessage(content="q", additional_kwargs={"kind": "question"}), AIMessage(content="c", additional_kwargs={"kind": "clarification"})]
    )
    assert all(turn["role"] == "interviewer" for turn in turns)


# ═══════════════════════════════════════════════════════════════════════
# decide_next -- pure, offline, no LLM, no I/O. Covered at its boundaries:
# the one-time "ask" edge, the probe count, elapsed time, and a sanity check
# that dimension_coverage does NOT gate the decision (it is resolved and
# written by `ask_probe`, not read here).
#
# 🔴 Rewritten from Phase 3's version. `_QUESTIONS_THIS_PHASE` went from 3
# to 1 (THREE DECISIONS #3: one question, probed live) and `decide_next` no
# longer asserts `followup_count == 0` -- that assertion existed because no
# probe edge existed to write it; `followup_count` is now this function's
# PRIMARY driver. Both `test_decide_next_asserts_followup_count_is_zero` and
# the tests pinning the OLD `_QUESTIONS_THIS_PHASE == 3` boundary asserted
# the opposite of the intended design and are replaced below, not merely
# patched -- the property under test (a boundary pinned exactly, not just
# values comfortably either side of it) is preserved.
# ═══════════════════════════════════════════════════════════════════════


def _iso_minutes_ago(minutes: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


def test_decide_next_asks_before_the_question_is_asked() -> None:
    """`current_q_idx == 0` -- the one-time edge that fires exactly once
    per interview, before `_decide_next_node` even has a real answer to
    have recorded. In practice `decide_next` only ever runs after an
    answer, so this boundary is defensive rather than reachable in the
    compiled graph -- but it is the ONE case that must still say "ask"."""
    state = {"current_q_idx": 0, "followup_count": 0, "dimension_coverage": {}}
    assert decide_next(state) == "ask"


def test_decide_next_continues_below_the_probe_count_boundary() -> None:
    state = {"current_q_idx": 1, "followup_count": 7, "dimension_coverage": {}}
    assert decide_next(state) == "probe"


def test_decide_next_exits_exactly_at_the_probe_count_boundary() -> None:
    """`_PROBES_THIS_PHASE` is 8 -- pins the boundary itself, not just a
    value comfortably on either side of it."""
    state = {"current_q_idx": 1, "followup_count": 8, "dimension_coverage": {}}
    assert decide_next(state) == "exit"


def test_decide_next_exits_past_the_probe_count_boundary() -> None:
    state = {"current_q_idx": 1, "followup_count": 9, "dimension_coverage": {}}
    assert decide_next(state) == "exit"


def test_decide_next_continues_when_time_budget_is_not_exceeded() -> None:
    state = {
        "current_q_idx": 1,
        "followup_count": 0,
        "dimension_coverage": {},
        "started_at": _iso_minutes_ago(5),
    }
    assert decide_next(state) == "probe"


def test_decide_next_exits_when_the_time_budget_is_exceeded_even_below_the_probe_count() -> None:
    """The safety valve: a candidate deep in clarifications, still short of
    `_PROBES_THIS_PHASE`, must not run the interview forever."""
    state = {
        "current_q_idx": 1,
        "followup_count": 0,
        "dimension_coverage": {},
        "started_at": _iso_minutes_ago(41),
    }
    assert decide_next(state) == "exit"


def test_decide_next_with_no_started_at_falls_back_to_probe_count_only() -> None:
    """`started_at` absent (defensive -- should always be set by
    `ask_question`'s question 1) must not crash the decision; it just can't
    apply the time-based exit."""
    state = {"current_q_idx": 1, "followup_count": 0, "dimension_coverage": {}}
    assert decide_next(state) == "probe"


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
    """Rubric coverage now lives across the probe ladder, resolved by
    `ask_probe` calling `resolve_primary_dimension` -- `decide_next` never
    reads `dimension_coverage` at all any more. Pins that varying it,
    holding `current_q_idx` and `followup_count` fixed, never changes the
    outcome."""
    state = {"current_q_idx": 1, "followup_count": 0, "dimension_coverage": coverage}
    assert decide_next(state) == "probe"


def test_decide_next_no_longer_asserts_on_a_nonzero_followup_count() -> None:
    """Positive control for the REMOVAL: Phase 3's `decide_next` raised
    `AssertionError` on any nonzero `followup_count`, because no probe edge
    existed to write one. That assertion is gone -- a nonzero
    `followup_count` is now the ordinary, expected shape of every call to
    this function after the first probe, and must return normally."""
    state = {"current_q_idx": 1, "followup_count": 1, "dimension_coverage": {}}
    assert decide_next(state) == "probe"  # must not raise


# ═══════════════════════════════════════════════════════════════════════
# improvised_facts -- the `operator.add` reducer on `InterviewState`,
# tested directly against a tiny two-node graph (no checkpointer, no LLM,
# no I/O) so the property is proven through real LangGraph merge mechanics,
# not by calling `operator.add` and assuming state.py wired it the same way.
# ARCHITECTURE §4 "The trap": without the reducer, the second node's return
# would silently REPLACE the first node's entry rather than accumulate --
# no exception, just an invented fact silently forgotten the moment a
# second one is recorded.
# ═══════════════════════════════════════════════════════════════════════


def test_improvised_facts_reducer_accumulates_rather_than_replaces() -> None:
    def first(state: InterviewState) -> dict:
        return {"improvised_facts": ["Assume weekly active users are around 3.4 million."]}

    def second(state: InterviewState) -> dict:
        return {"improvised_facts": ["Assume monthly churn is 4.6%."]}

    graph = StateGraph(InterviewState)
    graph.add_node("first", first)
    graph.add_node("second", second)
    graph.set_entry_point("first")
    graph.add_edge("first", "second")
    graph.add_edge("second", END)
    compiled = graph.compile()

    result = compiled.invoke({"session_id": "test-session", "improvised_facts": []})

    assert result["improvised_facts"] == [
        "Assume weekly active users are around 3.4 million.",
        "Assume monthly churn is 4.6%.",
    ], "improvised_facts did not accumulate -- the reducer is missing or misapplied"


def test_improvised_facts_starts_empty_when_nothing_was_invented() -> None:
    def noop(state: InterviewState) -> dict:
        return {}

    graph = StateGraph(InterviewState)
    graph.add_node("noop", noop)
    graph.set_entry_point("noop")
    graph.add_edge("noop", END)
    compiled = graph.compile()

    result = compiled.invoke({"session_id": "test-session", "improvised_facts": []})
    assert result["improvised_facts"] == []


# ═══════════════════════════════════════════════════════════════════════
# The two node closures, driven directly with `rest_insert` (and the agent
# call) monkeypatched -- no database, no network, no LLM. Same pattern as
# `test_curated_worlds.py`'s `recorded_inserts` fixture.
# ═══════════════════════════════════════════════════════════════════════

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

# 🔴 ONE question now (THREE DECISIONS #3), carrying a `probe_ladder` --
# `question_plan` stays "a list of dicts", but the list always has length 1
# as of story 3.5.3/3.5.4.
QUESTION_PLAN = [
    {
        "idx": 0,
        "question": "What is Palewell Analytics' biggest threat over the next three years?",
        "intent": "surfaces market read and prioritization under a fixed constraint",
        "primary_dimension": "market_accuracy",
        "probe_ladder": [
            {"angle": "What tradeoff would you make first?", "primary_dimension": "decision_quality"},
            {"angle": "What signal would change your mind?", "primary_dimension": "structural_clarity"},
            {"angle": "What would falsify leadership's belief?", "primary_dimension": "point_of_view"},
            {"angle": "How does Palewell Analytics actually make money today?", "primary_dimension": "business_model_fluency"},
            {"angle": "What is the biggest risk to the churn number specifically?", "primary_dimension": "market_accuracy"},
            {"angle": "How would you sequence this against the fixed headcount constraint?", "primary_dimension": "decision_quality"},
        ],
        "grounded_in": ["Monthly churn is 4.6%, the highest of any month since launch."],
        "minutes": 40,
    },
]


@pytest.fixture
def recorded_inserts_no_db(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict]]:
    """Stubs `app.graph.build.rest_insert` and records every call, so a
    node's side effects can be asserted on with no database -- same
    fixture shape as `test_curated_worlds.py`'s `recorded_inserts`."""
    calls: list[tuple[str, dict]] = []

    async def _fake_rest_insert(table: str, payload: dict) -> dict:
        calls.append((table, payload))
        return {**payload, "id": "stub-id"}

    monkeypatch.setattr("app.graph.build.rest_insert", _fake_rest_insert)
    return calls


def _clarify_state(**overrides: object) -> dict:
    base = {
        "session_id": "11111111-1111-1111-1111-111111111111",
        "case_world": CASE_WORLD,
        "question_plan": QUESTION_PLAN,
        "current_q_idx": 1,
        "last_input": {"type": "clarify", "text": "How big is the user base?"},
        "messages": [
            AIMessage(content=QUESTION_PLAN[0]["question"], additional_kwargs={"kind": "question"}),
            HumanMessage(content="How big is the user base?"),
        ],
    }
    base.update(overrides)
    return base


async def test_improvised_fact_is_recorded_when_non_empty_even_though_can_answer_is_true(
    recorded_inserts_no_db: list[tuple[str, dict]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """🔴 The exact live-measured contract `answer_clarification_node`'s
    docstring records: `improvised_fact` non-empty is the ONLY safe append
    signal, `can_answer` is not. This fixture deliberately INVERTS the
    normal correlation (can_answer=True paired with a NON-empty
    improvised_fact) so a node that mistakenly keyed off `can_answer`
    instead would fail this test by NOT appending -- proving the branch
    really reads `result.improvised_fact`, not `result.can_answer`."""

    async def _fake_answer_clarification(*args: object, **kwargs: object) -> ClarificationAnswer:
        return ClarificationAnswer(
            can_answer=True,
            answer="Assume weekly active users are around 3.4 million.",
            grounded_in=["Palewell Analytics"],
            improvised_fact="Assume weekly active users are around 3.4 million.",
        )

    monkeypatch.setattr("app.graph.build._answer_clarification", _fake_answer_clarification)

    node = _make_answer_clarification_node()
    result = await node(_clarify_state())

    assert result.get("improvised_facts") == ["Assume weekly active users are around 3.4 million."]


async def test_improvised_fact_is_not_recorded_when_empty_even_though_can_answer_is_false(
    recorded_inserts_no_db: list[tuple[str, dict]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The other inversion: can_answer=False (the invention branch) paired
    with an EMPTY improvised_fact -- a shape the model should never
    actually produce, but the node's own rule must hold regardless of what
    can_answer says: no entry is appended for an empty string."""

    async def _fake_answer_clarification(*args: object, **kwargs: object) -> ClarificationAnswer:
        return ClarificationAnswer(
            can_answer=False,
            answer="Assume weekly active users are around 3.4 million.",
            grounded_in=["Palewell Analytics"],
            improvised_fact="",
        )

    monkeypatch.setattr("app.graph.build._answer_clarification", _fake_answer_clarification)

    node = _make_answer_clarification_node()
    result = await node(_clarify_state())

    assert "improvised_facts" not in result


async def test_ask_probe_node_increments_followup_count_and_resolves_dimension(
    recorded_inserts_no_db: list[tuple[str, dict]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Drives the real `ask_probe` closure with `generate_probe`
    monkeypatched -- no LLM, no database. Pins the node's own three
    responsibilities beyond the LLM call itself: `followup_count`
    increments, `dimension_coverage` is updated via
    `resolve_primary_dimension` (never asked of the model), and the
    returned message carries `kind: "probe"` (not "followup" -- that is the
    DB row's kind, a deliberately different word, see the node's own
    comment)."""
    ladder = QUESTION_PLAN[0]["probe_ladder"]

    async def _fake_generate_probe(*args: object, **kwargs: object) -> Probe:
        return Probe(probe="What signal would change your mind?", angle_used=ladder[1]["angle"])

    monkeypatch.setattr("app.graph.build.generate_probe", _fake_generate_probe)

    node = _make_ask_probe()
    state = {
        "session_id": "11111111-1111-1111-1111-111111111111",
        "case_world": CASE_WORLD,
        "question_plan": QUESTION_PLAN,
        "current_q_idx": 1,
        "followup_count": 0,
        "dimension_coverage": {},
        "messages": [
            AIMessage(content=QUESTION_PLAN[0]["question"], additional_kwargs={"kind": "question"}),
            HumanMessage(content="I'd ship the web view first."),
        ],
    }

    result = await node(state)

    assert result["followup_count"] == 1
    assert result["messages"][0].additional_kwargs["kind"] == "probe"
    assert result["dimension_coverage"] == {ladder[1]["primary_dimension"]: 1}

    transcript_rows = [payload for table, payload in recorded_inserts_no_db if table == "transcript_turns"]
    assert transcript_rows[-1]["kind"] == "followup", "DB kind must be the DDL's 'followup', not 'probe'"
    assert transcript_rows[-1]["content"] == "What signal would change your mind?"


async def test_ask_probe_node_writes_an_error_event_and_reraises_on_failure(
    recorded_inserts_no_db: list[tuple[str, dict]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unlike `ask_question` (fully deterministic since 2026-08-05),
    `ask_probe` makes a real LLM call and can fail -- it must log an
    `agent_events` error row and re-raise, same as `answer_clarification_node`."""

    async def _explode(*args: object, **kwargs: object) -> Probe:
        raise RuntimeError("groq unavailable")

    monkeypatch.setattr("app.graph.build.generate_probe", _explode)

    node = _make_ask_probe()
    state = {
        "session_id": "11111111-1111-1111-1111-111111111111",
        "case_world": CASE_WORLD,
        "question_plan": QUESTION_PLAN,
        "current_q_idx": 1,
        "followup_count": 0,
        "dimension_coverage": {},
        "messages": [
            AIMessage(content=QUESTION_PLAN[0]["question"], additional_kwargs={"kind": "question"}),
            HumanMessage(content="I'd ship the web view first."),
        ],
    }

    with pytest.raises(RuntimeError):
        await node(state)

    error_events = [
        payload
        for table, payload in recorded_inserts_no_db
        if table == "agent_events" and payload.get("status") == "error"
    ]
    assert len(error_events) == 1


# ═══════════════════════════════════════════════════════════════════════
# Live: graph-level fixtures, same shape as test_confirm_level.py's
# `graph_sessions` -- a real `sessions` row is required because
# `ask_question`, `ask_probe`, and `answer_clarification_node` write
# `agent_events` and `transcript_turns`, both FK'd to `sessions`.
#
# 🔴 WRITTEN, NOT RUN (story 3.5.4 brief): each probe turn is a real `fast`
# LLM call now. Do not add `@pytest.mark.live` runs of these to a session
# budget without deliberately spending it -- see CLAUDE.md's TPM/daily
# ceilings and PHASE-3.5-SPEC.md's budget section.
# ═══════════════════════════════════════════════════════════════════════

LEVEL = "PM"


def _config(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}


@pytest.fixture
def loop_sessions() -> Iterator[Callable[[], str]]:
    """Mints a session already past `plan_interview` -- `sessions`,
    `resumes` (unused by this loop but present for symmetry), `case_worlds`
    are not required by the loop's own nodes, so only `sessions` is seeded;
    `case_world` and `question_plan` are injected straight into the initial
    state passed to `graph.ainvoke`, the same way `test_confirm_level.py`
    seeds `resume_text` rather than driving an upload for real.
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
    dies on `KeyError: 'resume_text'`.

    Seeding the checkpoint `as_node="plan_interview"` instead is the right
    shape rather than merely a working one: LangGraph resumes from the real
    `plan_interview -> ask_question` edge, so the loop's own wiring is still
    under test. Only the three upstream agents are skipped.
    """
    await graph.aupdate_state(config, _initial_state(session_id), as_node="plan_interview")
    return await graph.ainvoke(None, config)


@pytest.mark.live
async def test_the_loop_asks_the_one_question_then_probes_and_exits_at_the_probe_count_boundary(
    checkpointer: AsyncPostgresSaver, loop_sessions: Callable[[], str]
) -> None:
    """End-to-end shape of the new loop (replaces Phase 3's
    `test_the_loop_asks_two_to_three_questions_and_exits`, which drove a
    3-question plan that no longer exists): the ONE question is asked with
    ZERO LLM calls (`ask_question` stayed fully deterministic), then eight
    plain answers each draw exactly one probe, and the ninth answer (the
    one that would be probe 9) exits the loop with no further interrupt --
    `_PROBES_THIS_PHASE`'s boundary, exercised across real
    `Command(resume=...)` boundaries rather than inferred from `decide_next`
    called directly."""
    session_id = loop_sessions()
    graph = build_graph(checkpointer, interviewer_role="fast")
    config = _config(session_id)

    started = await _start_at_the_loop(graph, config, session_id)
    assert "__interrupt__" in started, "graph did not pause at await_candidate for the question"
    q1 = started["__interrupt__"][0].value
    assert q1["kind"] == "question"
    assert q1["text"] == QUESTION_PLAN[0]["question"], "the question was not emitted verbatim"

    result = None
    for probe_number in range(1, 9):  # _PROBES_THIS_PHASE = 8
        result = await graph.ainvoke(
            Command(resume={"type": "answer", "text": f"Answer number {probe_number}."}), config
        )
        assert "__interrupt__" in result, f"expected a probe to follow answer {probe_number}"
        probe_payload = result["__interrupt__"][0].value
        assert probe_payload["kind"] == "probe", f"turn {probe_number} did not surface as a probe"

    state = await graph.aget_state(config)
    assert state.values["followup_count"] == 8

    final = await graph.ainvoke(Command(resume={"type": "answer", "text": "Final answer."}), config)
    assert "__interrupt__" not in final, "the loop should have exited at the probe count boundary"


@pytest.mark.live
async def test_a_clarifying_question_does_not_advance_current_q_idx(
    checkpointer: AsyncPostgresSaver, loop_sessions: Callable[[], str]
) -> None:
    """A clarification must not consume the question slot: `current_q_idx`
    stays at 1 (the count after the one question was asked) through a full
    clarify/answer round -- unchanged property from Phase 3, re-verified
    against the one-question plan."""
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
async def test_await_candidate_produces_exactly_one_llm_call_per_probe_turn(
    checkpointer: AsyncPostgresSaver,
    loop_sessions: Callable[[], str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """🔴 THE trap named for story 3.5.4. `falsify_looping_interrupt.py`
    (story 3.2) proves the general looping-interrupt single-call assertion
    CAN fail -- but it only ever exercised `answer_clarification`, the
    ONLY LLM call that existed in the loop before this story.
    `generate_probe` is a second, separate LLM-calling node
    (`ask_probe`), reached by a different conditional-edge branch
    (`decide_next`'s "probe", not `route_input`'s "clarify"), and needs
    its OWN proof: resuming `await_candidate` with the candidate's answer
    to probe N must produce exactly one more `outcome=ok` log record, not
    two -- a duplicate would be invisible in `messages`/`transcript_turns`
    (both would still read as one probe/answer exchange); only
    `app.llm`'s call log sees it. Assert there, never on state -- same
    rule as `test_confirm_level.py`'s and Phase 3's equivalent tests.
    """
    session_id = loop_sessions()
    graph = build_graph(checkpointer, interviewer_role="fast")
    config = _config(session_id)

    with caplog.at_level(logging.INFO, logger="app.llm"):
        await _start_at_the_loop(graph, config, session_id)
        assert len(_ok_llm_calls(caplog)) == 0, "the question must cost zero LLM calls"

        for turn in range(1, 4):  # a few probe turns -- enough to prove the per-turn count, not all 8
            await graph.ainvoke(
                Command(resume={"type": "answer", "text": f"Answer number {turn}."}), config
            )
            calls_so_far = len(_ok_llm_calls(caplog))
            assert calls_so_far == turn, (
                f"expected exactly {turn} generate_probe call(s) after {turn} probe turn(s), "
                f"got {calls_so_far} -- a resumed await_candidate re-fired a probe call"
            )


@pytest.mark.live
async def test_await_candidate_does_not_redo_the_clarification_call_amid_a_probe_loop(
    checkpointer: AsyncPostgresSaver,
    loop_sessions: Callable[[], str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The clarification-specific sibling of the test above, inside the new
    probe design: drives a couple of probe turns (2 `generate_probe` calls),
    then clarifies mid-loop (1 more `answer_clarification` call), then
    resumes with the REAL answer to that same probe -- which must cost
    EITHER zero calls (if `decide_next` routes straight to another probe,
    that next `ask_probe` call is counted separately below) but must, above
    all, NOT re-fire the clarification call a second time."""
    session_id = loop_sessions()
    graph = build_graph(checkpointer, interviewer_role="fast")
    config = _config(session_id)

    with caplog.at_level(logging.INFO, logger="app.llm"):
        await _start_at_the_loop(graph, config, session_id)

        await graph.ainvoke(Command(resume={"type": "answer", "text": "Answer number 1."}), config)
        await graph.ainvoke(Command(resume={"type": "answer", "text": "Answer number 2."}), config)
        calls_before_clarify = len(_ok_llm_calls(caplog))
        assert calls_before_clarify == 2, "expected exactly 2 probe calls before the clarification"

        await graph.ainvoke(
            Command(resume={"type": "clarify", "text": "How big is Palewell's customer base?"}), config
        )
        calls_after_clarify = len(_ok_llm_calls(caplog))
        assert calls_after_clarify == 3, "expected exactly 1 more call (the clarification)"

        # The real answer to the probe that was open when the candidate
        # clarified resumes `await_candidate` a SECOND time for that SAME
        # probe turn. If anything upstream of it re-ran
        # `answer_clarification_node`'s LLM call, this count would jump to
        # 4 here on the clarification alone -- it must not; the ONLY
        # legitimate increment left is the next `ask_probe` call the answer
        # itself triggers.
        await graph.ainvoke(Command(resume={"type": "answer", "text": "About 340 customers."}), config)
        calls_after_real_answer = len(_ok_llm_calls(caplog))
        assert calls_after_real_answer == 4, (
            "expected exactly 1 more call (the next probe) -- got "
            f"{calls_after_real_answer}, which means either the clarification call "
            "re-fired or the next probe call did not happen"
        )
