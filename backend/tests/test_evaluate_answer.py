"""Story 4.3: `evaluate_answer_node` on the edge between `decide_next` and its
routing conditional, and the `answer_evaluations` write.

Per PHASE-4-SPEC.md's test table, this file must assert: exactly one Evaluator
LLM call per answer, that the node is NOT in `await_candidate`, and that rows
land in `answer_evaluations`.

🔴 MOST OF IT IS OFFLINE, DELIBERATELY. Every property that can be observed
without a model call is asserted against the real node closure with
`app.graph.build.evaluate_answer` and `rest_insert` monkeypatched -- same
pattern as `test_conduct_loop.py`'s `recorded_inserts_no_db` fixture. That
covers the `not_assessed` rule, the `turn_idx` link, the one-element return the
`operator.add` reducer needs, the running summary, the guard, and the error
path, at zero tokens. Only two things genuinely need a model:

  - the single-call count itself, which is a property of how LangGraph re-runs
    nodes and is only visible on `app.llm`'s log;
  - that the rows survive the round trip through PostgREST and the real DDL,
    `reasoning` column included.

🔴 THE SINGLE-CALL ASSERTION IS THE ONE THAT MATTERS, and it is asserted on the
LOG, never on state or on the table. A duplicate evaluator call re-writes the
same (session_id, turn_idx, dimension) rows, so `answer_evaluations` still
reads as one evaluation per turn to anyone querying it. Nothing downstream
would notice; only the call log sees it.
`scripts/falsify_evaluate_single_call.py` proves that assertion CAN fail, by
building the wrong graph. Without that script this file's count is unfalsified.

Live tests are PACED -- `_paced()` copied from `test_conduct_loop.py`. Unpaced
live files have never produced a readable red run in this project.
"""

from __future__ import annotations

import ast
import asyncio
import inspect
import logging
import textwrap
import time
import uuid
from typing import Callable, Iterator

import psycopg
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, StateGraph
from langgraph.types import Command

from app.agents.evaluator import AnswerEvaluation, DimensionScore
from app.agents.planner import RUBRIC_DIMENSIONS
from app.config import settings
from app.graph import build as build_module
from app.graph.build import (
    _PROBES_THIS_PHASE,
    _decide_next_node,
    _make_evaluate_answer_node,
    _prior_scores,
    build_graph,
)
from app.graph.state import InterviewState

# ═══════════════════════════════════════════════════════════════════════
# Shared fixtures for the offline half. `CASE_WORLD` / `QUESTION_PLAN` are
# copied from `test_conduct_loop.py` rather than imported, matching this
# project's precedent of not sharing test-only data across modules.
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
        ],
        "grounded_in": ["Monthly churn is 4.6%, the highest of any month since launch."],
        "minutes": 40,
    },
]

SESSION_ID = "11111111-1111-1111-1111-111111111111"
ANSWER_TEXT = "I would ship the mobile web view first, because churn at 4.6% is the number that matters."


def _answer_state(**overrides: object) -> dict:
    """State as it stands when `evaluate_answer_node` runs: `await_candidate`
    has already merged the candidate's HumanMessage, and `_decide_next_node`
    has already written its `transcript_turns` row."""
    base = {
        "session_id": SESSION_ID,
        "case_world": CASE_WORLD,
        "question_plan": QUESTION_PLAN,
        "assessed_level": "PM",
        "current_q_idx": 1,
        "followup_count": 0,
        "last_input": {"type": "answer", "text": ANSWER_TEXT},
        "messages": [
            AIMessage(content=QUESTION_PLAN[0]["question"], additional_kwargs={"kind": "question"}),
            HumanMessage(content=ANSWER_TEXT, additional_kwargs={"kind": "answer"}),
        ],
        "answer_evaluations": [],
    }
    base.update(overrides)
    return base


def _evaluation(
    scored: list[tuple[str, int, str]],
    not_assessed: list[str],
    *,
    framework_narration: bool = False,
) -> AnswerEvaluation:
    return AnswerEvaluation(
        dimension_scores=[
            DimensionScore(
                dimension=dimension,
                score=score,
                evidence_quote=quote,
                reasoning=f"{dimension} reasoning.",
            )
            for dimension, score, quote in scored
        ],
        framework_narration=framework_narration,
        not_assessed=not_assessed,
    )


@pytest.fixture
def recorded_inserts_no_db(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict]]:
    """Stubs `app.graph.build.rest_insert` and records every call, so the
    node's side effects can be asserted with no database -- same fixture shape
    as `test_conduct_loop.py`'s."""
    calls: list[tuple[str, dict]] = []

    async def _fake_rest_insert(table: str, payload: dict) -> dict:
        calls.append((table, payload))
        return {**payload, "id": "stub-id"}

    monkeypatch.setattr("app.graph.build.rest_insert", _fake_rest_insert)
    return calls


def _stub_evaluator(
    monkeypatch: pytest.MonkeyPatch, evaluation: AnswerEvaluation
) -> list[tuple[tuple, dict]]:
    """Replaces `app.graph.build.evaluate_answer` with a stub returning
    `evaluation`, and records the arguments it was called with."""
    calls: list[tuple[tuple, dict]] = []

    async def _fake(*args: object, **kwargs: object) -> AnswerEvaluation:
        calls.append((args, kwargs))
        return evaluation

    monkeypatch.setattr("app.graph.build.evaluate_answer", _fake)
    return calls


# ═══════════════════════════════════════════════════════════════════════
# The graph's SHAPE -- offline, no checkpointer, no model call.
#
# `build_graph(None)` compiles without a checkpointer purely so the wiring can
# be inspected. This is NOT development against `MemorySaver` (CLAUDE.md's
# rule): the graph below is never invoked, only read.
# ═══════════════════════════════════════════════════════════════════════


def _compiled_edges() -> list[tuple[str, str, object]]:
    drawn = build_graph(None).get_graph()
    return [(edge.source, edge.target, edge.data) for edge in drawn.edges]


def test_evaluate_answer_node_is_a_registered_node() -> None:
    assert "evaluate_answer_node" in set(build_graph(None).get_graph().nodes)


def test_the_answer_write_flows_straight_into_the_evaluator() -> None:
    """`decide_next` (the NODE, which writes the answer's `transcript_turns`
    row) has exactly one outgoing edge, and it is the evaluator. An
    unconditional edge, so no routing decision can skip the scoring."""
    outgoing = [(target, data) for source, target, data in _compiled_edges() if source == "decide_next"]
    assert outgoing == [("evaluate_answer_node", None)], (
        f"decide_next's outgoing edges are {outgoing} -- the evaluator must be the only "
        "one, and unconditional"
    )


def test_routing_now_happens_after_the_evaluation_so_the_final_answer_is_scored() -> None:
    """🔴 The load-bearing ordering. The three routing branches hang off
    `evaluate_answer_node`, not off `decide_next`. If they hung off
    `decide_next` instead, the "exit" branch would leave the interview before
    the LAST answer was ever scored -- the same reason `_decide_next_node`,
    not `ask_question`, owns the answer's transcript write."""
    branches = {
        (target, data) for source, target, data in _compiled_edges() if source == "evaluate_answer_node"
    }
    assert branches == {("ask_question", "ask"), ("ask_probe", "probe"), (END, "exit")}, (
        f"the routing branches off evaluate_answer_node are {branches}"
    )


def test_await_candidate_cannot_hold_an_llm_call_at_all() -> None:
    """🔴 CLAUDE.md's single most important structural constraint. A call
    placed in `await_candidate` fires TWICE per answer, because LangGraph
    re-runs the node from the top on resume -- and in `answer_evaluations` the
    duplicate is invisible, because it rewrites the same rows.

    `await_candidate` is a plain `def`, not `async def`, so it cannot await
    anything: that is the structural guarantee, checked here rather than
    assumed."""
    assert not inspect.iscoroutinefunction(build_module.await_candidate)
    source = inspect.getsource(build_module.await_candidate)
    assert "await " not in source
    assert "evaluate_answer" not in source, "the evaluator was moved into await_candidate"
    assert "rest_insert" not in source


def test_await_candidate_computes_nothing_but_pure_reads_above_the_interrupt() -> None:
    """The general form of the rule, so a FUTURE node's work cannot creep in
    above the interrupt either: every statement before `interrupt()` may call
    nothing but `.get`, and the only statement after it is the return."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(build_module.await_candidate)))
    function = tree.body[0]
    assert isinstance(function, ast.FunctionDef)

    interrupt_at = next(
        i
        for i, statement in enumerate(function.body)
        if any(
            isinstance(node, ast.Call) and getattr(node.func, "id", None) == "interrupt"
            for node in ast.walk(statement)
        )
    )

    called = {
        getattr(node.func, "attr", getattr(node.func, "id", "?"))
        for statement in function.body[:interrupt_at]
        for node in ast.walk(statement)
        if isinstance(node, ast.Call)
    }
    assert called <= {"get"}, (
        f"await_candidate calls {sorted(called)} above its interrupt() -- every one of "
        "those re-runs on every candidate turn for the rest of the interview"
    )
    assert [type(s) for s in function.body[interrupt_at + 1 :]] == [ast.Return]


# ═══════════════════════════════════════════════════════════════════════
# _prior_scores -- the running summary, pure, offline.
#
# 🔴 This is what makes per-answer scoring fit the 8,000 TPM ceiling at all:
# the FULL transcript measured 10,274 tokens and did not fit. Keyed by
# dimension, so it is bounded at five entries however long the interview runs.
# ═══════════════════════════════════════════════════════════════════════


def test_prior_scores_is_empty_for_the_first_answer() -> None:
    assert _prior_scores([]) == []
    assert _prior_scores(None) == []


def test_prior_scores_flattens_across_evaluations() -> None:
    evaluations = [
        {"turn_idx": 1, "dimension_scores": [
            {"dimension": "market_accuracy", "score": 3, "evidence_quote": "q1", "reasoning": "r1"}
        ]},
        {"turn_idx": 3, "dimension_scores": [
            {"dimension": "decision_quality", "score": 2, "evidence_quote": "q2", "reasoning": "r2"}
        ]},
    ]
    assert _prior_scores(evaluations) == [
        {"dimension": "market_accuracy", "score": 3, "evidence_quote": "q1"},
        {"dimension": "decision_quality", "score": 2, "evidence_quote": "q2"},
    ]


def test_prior_scores_lets_a_later_evaluation_overwrite_an_earlier_one() -> None:
    """A dimension revisited by a later probe was scored on better evidence.
    The Evaluator is given this as the ARC of the interview, so it must carry
    the CURRENT reading of each dimension, not every attempt at it."""
    evaluations = [
        {"turn_idx": 1, "dimension_scores": [
            {"dimension": "point_of_view", "score": 2, "evidence_quote": "early", "reasoning": "r"}
        ]},
        {"turn_idx": 5, "dimension_scores": [
            {"dimension": "point_of_view", "score": 4, "evidence_quote": "later", "reasoning": "r"}
        ]},
    ]
    assert _prior_scores(evaluations) == [
        {"dimension": "point_of_view", "score": 4, "evidence_quote": "later"},
    ]


def test_prior_scores_stays_bounded_at_five_however_long_the_interview_runs() -> None:
    """🔴 The budget property, asserted rather than trusted. Ten turns, every
    dimension scored on every one of them, still five entries -- this is why
    the evaluator call does not grow with turn count the way the Interviewer's
    window does."""
    evaluations = [
        {
            "turn_idx": turn,
            "dimension_scores": [
                {"dimension": d, "score": 3, "evidence_quote": f"q{turn}", "reasoning": "r"}
                for d in RUBRIC_DIMENSIONS
            ],
        }
        for turn in range(10)
    ]
    summary = _prior_scores(evaluations)
    assert len(summary) == len(RUBRIC_DIMENSIONS) == 5


def test_prior_scores_carries_three_keys_and_never_the_reasoning() -> None:
    """`reasoning` is the longest field on a `DimensionScore`, and the budget
    block in `app/agents/evaluator.py` measures the difference at 438 tokens
    against 283. It is context the model is told not to re-score, so it is
    dropped rather than sent."""
    evaluations = [
        {"turn_idx": 1, "dimension_scores": [
            {"dimension": "market_accuracy", "score": 3, "evidence_quote": "q", "reasoning": "r"}
        ]},
    ]
    assert set(_prior_scores(evaluations)[0]) == {"dimension", "score", "evidence_quote"}


# ═══════════════════════════════════════════════════════════════════════
# The node closure, driven directly -- no database, no network, no LLM.
# ═══════════════════════════════════════════════════════════════════════


async def test_a_scored_dimension_gets_exactly_one_row(
    recorded_inserts_no_db: list[tuple[str, dict]], monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_evaluator(
        monkeypatch,
        _evaluation(
            [("market_accuracy", 3, "churn at 4.6% is the number that matters"),
             ("decision_quality", 2, "I would ship the mobile web view first")],
            ["business_model_fluency", "structural_clarity", "point_of_view"],
        ),
    )

    await _make_evaluate_answer_node()(_answer_state())

    rows = [payload for table, payload in recorded_inserts_no_db if table == "answer_evaluations"]
    assert [row["dimension"] for row in rows] == ["market_accuracy", "decision_quality"]
    assert all(row["session_id"] == SESSION_ID for row in rows)
    assert rows[0]["score"] == 3
    assert rows[0]["evidence_quote"] == "churn at 4.6% is the number that matters"
    assert rows[0]["reasoning"] == "market_accuracy reasoning."


async def test_a_not_assessed_dimension_gets_no_row_at_all(
    recorded_inserts_no_db: list[tuple[str, dict]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """🔴 PHASE-4-SPEC.md §4.3. `score` is `not null check (score between 1 and
    4)`, so an unassessed dimension CANNOT be a row. Its ABSENCE is the
    representation, and the reader treats a missing row as not assessed.

    The inverse is what this pins: a node that wrote a placeholder row (score
    0, or a null, or an empty quote) would satisfy every "rows landed"
    assertion in this file and quietly report a dimension nobody said anything
    about as a bottom-of-range score."""
    not_assessed = ["business_model_fluency", "structural_clarity", "point_of_view", "decision_quality"]
    _stub_evaluator(
        monkeypatch,
        _evaluation([("market_accuracy", 3, "churn at 4.6% is the number")], not_assessed),
    )

    await _make_evaluate_answer_node()(_answer_state())

    written = {
        payload["dimension"]
        for table, payload in recorded_inserts_no_db
        if table == "answer_evaluations"
    }
    assert written == {"market_accuracy"}
    assert written.isdisjoint(not_assessed), (
        f"a not_assessed dimension was written anyway: {sorted(written & set(not_assessed))}"
    )


async def test_turn_idx_is_the_same_index_the_answers_transcript_row_used(
    recorded_inserts_no_db: list[tuple[str, dict]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """🔴 The link the column exists for: 0001_initial_schema.sql's own words,
    "turn_idx references transcript_turns.idx, which is how a score in the
    scorecard links back to the exact turn it was drawn from."

    Both nodes are driven over the SAME state, in the order the graph runs
    them, and the two indexes are compared. Asserting `turn_idx == 1` against a
    literal would pass just as happily if both nodes were off by the same
    amount; this cannot."""
    _stub_evaluator(
        monkeypatch, _evaluation([("market_accuracy", 3, "churn at 4.6%")],
                                 ["business_model_fluency", "structural_clarity",
                                  "point_of_view", "decision_quality"])
    )
    state = _answer_state()

    await _decide_next_node(state)
    await _make_evaluate_answer_node()(state)

    transcript_idx = [
        payload["idx"]
        for table, payload in recorded_inserts_no_db
        if table == "transcript_turns" and payload["kind"] == "answer"
    ]
    evaluation_idx = [
        payload["turn_idx"]
        for table, payload in recorded_inserts_no_db
        if table == "answer_evaluations"
    ]
    assert transcript_idx == [1]
    assert evaluation_idx == [1]
    assert set(evaluation_idx) == set(transcript_idx), (
        "the evaluation's turn_idx does not point at the turn it scored"
    )


async def test_the_node_returns_a_one_element_list_for_the_reducer(
    recorded_inserts_no_db: list[tuple[str, dict]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`answer_evaluations` carries an `operator.add` reducer. A bare dict, or
    the full accumulated list, corrupts the running summary SILENTLY -- there
    is no exception, just a scorecard built from the wrong evaluations."""
    _stub_evaluator(
        monkeypatch,
        _evaluation([("market_accuracy", 3, "churn at 4.6%")],
                    ["business_model_fluency", "structural_clarity", "point_of_view",
                     "decision_quality"],
                    framework_narration=True),
    )

    result = await _make_evaluate_answer_node()(_answer_state())

    assert list(result) == ["answer_evaluations"]
    assert isinstance(result["answer_evaluations"], list)
    assert len(result["answer_evaluations"]) == 1
    evaluation = result["answer_evaluations"][0]
    assert evaluation["turn_idx"] == 1, "a later reader cannot tell the evaluations apart"
    assert evaluation["framework_narration"] is True
    assert evaluation["not_assessed"] == [
        "business_model_fluency", "structural_clarity", "point_of_view", "decision_quality"
    ]
    assert [s["dimension"] for s in evaluation["dimension_scores"]] == ["market_accuracy"]


async def test_the_reducer_accumulates_what_the_node_returns() -> None:
    """The return shape proven through real LangGraph merge mechanics rather
    than by assuming `state.py` wired `operator.add` the way it reads. Two
    nodes, no checkpointer, no LLM -- same approach `test_conduct_loop.py`
    takes for `improvised_facts`."""

    def first(state: InterviewState) -> dict:
        return {"answer_evaluations": [{"turn_idx": 1, "dimension_scores": []}]}

    def second(state: InterviewState) -> dict:
        return {"answer_evaluations": [{"turn_idx": 3, "dimension_scores": []}]}

    graph = StateGraph(InterviewState)
    graph.add_node("first", first)
    graph.add_node("second", second)
    graph.set_entry_point("first")
    graph.add_edge("first", "second")
    graph.add_edge("second", END)

    result = graph.compile().invoke({"session_id": SESSION_ID, "answer_evaluations": []})

    assert [e["turn_idx"] for e in result["answer_evaluations"]] == [1, 3], (
        "answer_evaluations did not accumulate -- the reducer is missing or the node "
        "returned the wrong shape"
    )


async def test_the_running_summary_reaches_the_agent(
    recorded_inserts_no_db: list[tuple[str, dict]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The node must hand `evaluate_answer` the RUNNING SUMMARY, never the raw
    transcript. Positional order is fixed by the golden suite's call site:
    (case_world, question, answer, assessed_level, prior_scores)."""
    calls = _stub_evaluator(
        monkeypatch, _evaluation([("market_accuracy", 3, "churn at 4.6%")],
                                 ["business_model_fluency", "structural_clarity",
                                  "point_of_view", "decision_quality"])
    )
    prior = [{"turn_idx": 1, "dimension_scores": [
        {"dimension": "point_of_view", "score": 2, "evidence_quote": "earlier", "reasoning": "r"}
    ]}]

    await _make_evaluate_answer_node()(_answer_state(answer_evaluations=prior))

    args, kwargs = calls[0]
    assert args[0] == CASE_WORLD
    assert args[1] == QUESTION_PLAN[0]["question"], "the evaluator was not given the main question"
    assert args[2] == ANSWER_TEXT
    assert args[3] == "PM"
    assert args[4] == [{"dimension": "point_of_view", "score": 2, "evidence_quote": "earlier"}]
    assert kwargs == {"role": "fast"}


@pytest.mark.parametrize(
    "last_input",
    [
        {"type": "clarify", "text": "How big is the customer base?"},
        {"type": "answer", "text": None},
        {},
        None,
    ],
)
async def test_nothing_but_an_answer_is_ever_scored(
    last_input: dict | None,
    recorded_inserts_no_db: list[tuple[str, dict]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The guard mirrors `_decide_next_node`'s immediately upstream. It must
    cost ZERO LLM calls and write nothing -- the stub raises, so a node that
    called through anyway fails loudly instead of quietly scoring a clarifying
    question as if it were an answer."""

    async def _must_not_be_called(*args: object, **kwargs: object) -> AnswerEvaluation:
        raise AssertionError("evaluate_answer was called for a non-answer turn")

    monkeypatch.setattr("app.graph.build.evaluate_answer", _must_not_be_called)

    result = await _make_evaluate_answer_node()(_answer_state(last_input=last_input))

    assert result == {}
    assert recorded_inserts_no_db == [], "the guarded path still wrote agent_events rows"


async def test_agent_events_bracket_the_call(
    recorded_inserts_no_db: list[tuple[str, dict]], monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_evaluator(
        monkeypatch, _evaluation([("market_accuracy", 3, "churn at 4.6%")],
                                 ["business_model_fluency", "structural_clarity",
                                  "point_of_view", "decision_quality"])
    )

    await _make_evaluate_answer_node()(_answer_state())

    events = [payload for table, payload in recorded_inserts_no_db if table == "agent_events"]
    assert [e["status"] for e in events] == ["started", "done"]
    assert all(e["agent"] == "evaluator" for e in events)
    assert events[-1]["duration_ms"] >= 0


async def test_a_failed_evaluation_writes_an_error_event_and_reraises(
    recorded_inserts_no_db: list[tuple[str, dict]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same contract as `ask_probe` and `answer_clarification_node`: this is a
    real LLM call and it can fail."""

    async def _explode(*args: object, **kwargs: object) -> AnswerEvaluation:
        raise RuntimeError("groq unavailable")

    monkeypatch.setattr("app.graph.build.evaluate_answer", _explode)

    with pytest.raises(RuntimeError):
        await _make_evaluate_answer_node()(_answer_state())

    errors = [
        payload
        for table, payload in recorded_inserts_no_db
        if table == "agent_events" and payload.get("status") == "error"
    ]
    assert len(errors) == 1
    assert errors[0]["agent"] == "evaluator"
    assert not [t for t, _ in recorded_inserts_no_db if t == "answer_evaluations"]


async def test_reasoning_is_normalised_but_the_evidence_quote_is_left_alone(
    recorded_inserts_no_db: list[tuple[str, dict]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """🔴 Two fields, two rules, and getting them the same way round is wrong
    either way. `reasoning` is prose the candidate reads on the scorecard, so
    it is normalised at the graph boundary (see `app/text.py`).
    `evidence_quote` is checked against the transcript BYTE FOR BYTE, and
    `_decide_next_node` writes the candidate's text unnormalised, so
    normalising the quote would turn a faithful copy into a mismatch."""
    quote = "churn at 4.6% — the number that matters"
    evaluation = AnswerEvaluation(
        dimension_scores=[
            DimensionScore(
                dimension="market_accuracy",
                score=3,
                evidence_quote=quote,
                reasoning="The candidate anchors on churn — the metric leadership tracks.",
            )
        ],
        framework_narration=False,
        not_assessed=["business_model_fluency", "structural_clarity", "point_of_view",
                      "decision_quality"],
    )
    _stub_evaluator(monkeypatch, evaluation)

    await _make_evaluate_answer_node()(_answer_state())

    row = next(p for t, p in recorded_inserts_no_db if t == "answer_evaluations")
    assert row["evidence_quote"] == quote, "the verbatim quote was rewritten"
    assert "—" not in row["reasoning"]
    assert row["reasoning"] == "The candidate anchors on churn, the metric leadership tracks."


# ═══════════════════════════════════════════════════════════════════════
# Live. Fixtures copied from `test_conduct_loop.py`, matching that file's own
# precedent of copying test-only fixtures rather than sharing them.
# ═══════════════════════════════════════════════════════════════════════


def _config(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}


@pytest.fixture
def eval_sessions() -> Iterator[Callable[[], str]]:
    """Mints a session already past `plan_interview`, and cleans up its
    checkpoints. `answer_evaluations`, `transcript_turns` and `agent_events`
    all cascade off `sessions`."""
    created: list[str] = []

    def make() -> str:
        session_id = str(uuid.uuid4())
        conn = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
        try:
            with conn.cursor() as cur:
                cur.execute("insert into sessions (id, status) values (%s, 'created')", (session_id,))
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
    """Copied from `test_conduct_loop.py`'s helper of the same name -- only
    `outcome=ok` records, so a legitimate validate-retry does not read as a
    duplicate call."""
    return [
        record.getMessage()
        for record in caplog.records
        if record.name == "app.llm"
        and record.getMessage().startswith("llm_call")
        and "outcome=ok" in record.getMessage()
    ]


# ~21s, copied from `test_conduct_loop.py`. See that file's block comment: the
# ceiling is 8,000 TPM, and unpaced live files in this project have never
# produced a readable red run.
_MIN_SECONDS_BETWEEN_LLM_CALLS = 21.0
_last_call_at = 0.0


async def _paced(graph, payload, config: dict) -> dict:
    """`graph.ainvoke`, throttled to stay under the per-minute token ceiling."""
    global _last_call_at
    wait = _MIN_SECONDS_BETWEEN_LLM_CALLS - (time.monotonic() - _last_call_at)
    if wait > 0:
        await asyncio.sleep(wait)
    _last_call_at = time.monotonic()
    return await graph.ainvoke(payload, config)


async def _start_at_the_loop(graph, config: dict, session_id: str, **state: object) -> dict:
    """Drives the real graph to its first `await_candidate` pause without
    paying for the three agents upstream of the loop, exactly as
    `test_conduct_loop.py` does: seeded `as_node="plan_interview"`, so LangGraph
    resumes from the real `plan_interview -> ask_question` edge and the loop's
    own wiring is still under test."""
    initial = {
        "session_id": session_id,
        "case_world": CASE_WORLD,
        "question_plan": QUESTION_PLAN,
        "assessed_level": "PM",
        **state,
    }
    await graph.aupdate_state(config, initial, as_node="plan_interview")
    return await graph.ainvoke(None, config)


def _rows(session_id: str) -> tuple[list[tuple], list[tuple]]:
    """(answer_evaluations, transcript_turns) for one session, read on a fresh
    connection after the graph has finished writing over REST."""
    conn = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "select turn_idx, dimension, score, evidence_quote, reasoning "
                "from answer_evaluations where session_id = %s order by dimension",
                (session_id,),
            )
            evaluations = cur.fetchall()
            cur.execute(
                "select idx, kind from transcript_turns where session_id = %s and kind = 'answer'",
                (session_id,),
            )
            answers = cur.fetchall()
        return evaluations, answers
    finally:
        conn.close()


@pytest.mark.live
async def test_the_final_answer_is_scored_by_exactly_one_evaluator_call(
    checkpointer: AsyncPostgresSaver,
    eval_sessions: Callable[[], str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """🔴 THE single-call assertion, and it is measured on `app.llm`'s LOG, not
    on state and not on the table. A duplicate evaluator call rewrites the same
    (session_id, turn_idx, dimension) rows, so `answer_evaluations` reads as one
    evaluation per turn either way. Only the call log sees it.
    `scripts/falsify_evaluate_single_call.py` proves this count CAN go red.

    `followup_count` is seeded at `_PROBES_THIS_PHASE`, so this answer is the
    FINAL one: `decide_next` routes straight to END and `ask_probe` never runs.
    That makes the count unambiguous -- the ONLY LLM call in the whole cycle is
    the evaluator's, so `== 1` is a direct measurement rather than a delta
    inferred against the probe.

    It also pins the ordering the wiring exists for: the last answer of the
    interview is still scored, even though nothing downstream of the routing
    conditional ever runs again.
    """
    session_id = eval_sessions()
    graph = build_graph(checkpointer, interviewer_role="fast", evaluator_role="fast")
    config = _config(session_id)

    with caplog.at_level(logging.INFO, logger="app.llm"):
        started = await _start_at_the_loop(
            graph, config, session_id, followup_count=_PROBES_THIS_PHASE
        )
        assert "__interrupt__" in started, "graph did not pause at await_candidate"
        assert len(_ok_llm_calls(caplog)) == 0, "the question must cost zero LLM calls"

        final = await _paced(graph, Command(resume={"type": "answer", "text": ANSWER_TEXT}), config)
        assert "__interrupt__" not in final, "the loop should have exited at the probe boundary"

        calls = _ok_llm_calls(caplog)
        assert len(calls) == 1, (
            f"expected exactly 1 evaluator call for 1 answer, got {len(calls)}:\n"
            + "\n".join(calls)
            + "\n-- more than one means a resumed node re-fired the evaluation, which is "
            "INVISIBLE in answer_evaluations"
        )

    evaluations, answers = _rows(session_id)
    assert answers, "the answer's transcript_turns row was never written"
    assert evaluations, "no answer_evaluations rows landed for the scored answer"

    answer_idx = {idx for idx, _ in answers}
    assert {row[0] for row in evaluations} <= answer_idx, (
        f"turn_idx {sorted({row[0] for row in evaluations})} does not match the answer's "
        f"transcript_turns.idx {sorted(answer_idx)}"
    )
    assert all(row[2] in (1, 2, 3, 4) for row in evaluations)
    assert all(row[3].strip() for row in evaluations), "a score shipped without a quote"
    assert all(row[4] and row[4].strip() for row in evaluations), (
        "reasoning is empty or null -- migration 0004 may not be applied"
    )

    state = await graph.aget_state(config)
    stored = state.values["answer_evaluations"]
    assert len(stored) == 1, f"expected one evaluation in state, got {len(stored)}"
    scored = {s["dimension"] for s in stored[0]["dimension_scores"]}
    not_assessed = set(stored[0]["not_assessed"])
    written = {row[1] for row in evaluations}

    assert written == scored, f"rows {sorted(written)} do not match scored {sorted(scored)}"
    assert written.isdisjoint(not_assessed), (
        f"a not_assessed dimension got a row: {sorted(written & not_assessed)}"
    )
    assert scored | not_assessed == set(RUBRIC_DIMENSIONS)


@pytest.mark.live
async def test_a_mid_loop_answer_is_scored_once_and_still_draws_its_probe(
    checkpointer: AsyncPostgresSaver,
    eval_sessions: Callable[[], str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The other side of the boundary: an answer that is NOT the last one.
    Two LLM calls follow it and exactly two -- the evaluator's and the probe's.
    `test_conduct_loop.py` pins the probe at exactly one per turn on its own, so
    a third record here is the evaluator having fired twice.

    This is the test that would go red if the new node were wired in a way that
    broke the probe edge, which is the named trap for touching `build.py`: the
    graph is a shared object.
    """
    session_id = eval_sessions()
    graph = build_graph(checkpointer, interviewer_role="fast", evaluator_role="fast")
    config = _config(session_id)

    with caplog.at_level(logging.INFO, logger="app.llm"):
        await _start_at_the_loop(graph, config, session_id, followup_count=0)
        assert len(_ok_llm_calls(caplog)) == 0

        result = await _paced(graph, Command(resume={"type": "answer", "text": ANSWER_TEXT}), config)

        assert "__interrupt__" in result, "the answer did not draw a probe"
        assert result["__interrupt__"][0].value["kind"] == "probe"

        calls = _ok_llm_calls(caplog)
        assert len(calls) == 2, (
            f"expected exactly 2 calls (one evaluation, one probe), got {len(calls)}:\n"
            + "\n".join(calls)
        )

    evaluations, _ = _rows(session_id)
    assert evaluations, "a mid-loop answer was not scored"
