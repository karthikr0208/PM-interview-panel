"""Story 0.6: interrupt and resume on the two-node skeleton graph.

The load-bearing test in this file is
`test_llm_call_fires_exactly_once_across_interrupt_and_resume`. Everything
else here is scaffolding around it.

Why it is load-bearing: on resume LangGraph re-runs the interrupting node
from the top, not from the `interrupt()` line. Every candidate answer in
Phase 3 goes through exactly this cycle, so a node that does work above its
own `interrupt()` would burn a duplicate LLM call and double-count the turn
on every single answer — against a 40 RPM ceiling, and with no error to
notice. Proving the property here costs one nano call. Debugging it in
Phase 3 costs a phase.

Marked `live` for the same reason as test_checkpointer.py: these hit the real
Supabase project over the session pooler, and `ask_something` hits the real
NVIDIA endpoint. Mocking either would defeat the point of the phase.
Fixtures (`conn`, `checkpointer`, `thread_ids`) come from conftest.py.
"""

from __future__ import annotations

import logging
from typing import Callable

import psycopg
import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command

from app.graph.skeleton import build_skeleton_graph

pytestmark = pytest.mark.live

INITIAL_STATE = {"messages": [], "turn_count": 0}


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _llm_calls(caplog: pytest.LogCaptureFixture) -> list[str]:
    """Every line `app/llm.py` logs per call, from story 0.2's rate-limit log.

    Counting the log rather than patching the client is deliberate: it asserts
    against the same record that will be used to watch the 40 RPM ceiling in
    production, so a change that made the log stop reflecting reality would
    fail here too.
    """
    return [
        record.getMessage()
        for record in caplog.records
        if record.name == "app.llm" and record.getMessage().startswith("llm_call")
    ]


def test_graph_compiles_with_the_postgres_checkpointer(
    checkpointer: AsyncPostgresSaver,
) -> None:
    graph = build_skeleton_graph(checkpointer)
    assert graph.checkpointer is checkpointer
    assert not isinstance(graph.checkpointer, MemorySaver), (
        "MemorySaver hides the stateless-HTTP bugs story 0.7 exists to catch"
    )


async def test_ainvoke_runs_to_the_interrupt_and_returns_its_payload(
    checkpointer: AsyncPostgresSaver, thread_ids: Callable[[], str]
) -> None:
    graph = build_skeleton_graph(checkpointer)
    result = await graph.ainvoke(INITIAL_STATE, _config(thread_ids()))

    assert "__interrupt__" in result, f"graph did not pause; keys were {sorted(result)}"
    payload = result["__interrupt__"][0].value
    assert payload["question"], "the interrupt payload carried no question"


async def test_command_resume_makes_interrupt_return_the_passed_value(
    checkpointer: AsyncPostgresSaver, thread_ids: Callable[[], str]
) -> None:
    """`interrupt()` returning the resumed value is what carries a candidate's
    answer into graph state. Asserted on the message the node built from that
    return value, not on the return value itself, since the node is the only
    thing that ever sees it."""
    graph = build_skeleton_graph(checkpointer)
    config = _config(thread_ids())
    answer = "I would start by segmenting the users before touching the roadmap."

    await graph.ainvoke(INITIAL_STATE, config)
    resumed = await graph.ainvoke(Command(resume=answer), config)

    assert "__interrupt__" not in resumed, "graph paused a second time instead of finishing"
    assert any(
        getattr(message, "content", None) == answer for message in resumed["messages"]
    ), "the resumed value never reached state"


async def test_get_state_next_is_the_paused_node(
    checkpointer: AsyncPostgresSaver, thread_ids: Callable[[], str]
) -> None:
    """`.next` is how story 0.7's API will tell a paused session from a
    finished one across two separate HTTP requests."""
    graph = build_skeleton_graph(checkpointer)
    config = _config(thread_ids())

    await graph.ainvoke(INITIAL_STATE, config)
    paused = await graph.aget_state(config)
    assert paused.next == ("await_reply",), f"expected to be paused at await_reply, got {paused.next}"

    await graph.ainvoke(Command(resume="done"), config)
    finished = await graph.aget_state(config)
    assert finished.next == (), f"expected a finished graph, got next={finished.next}"


async def test_checkpoint_rows_land_after_each_node(
    checkpointer: AsyncPostgresSaver,
    conn: psycopg.Connection,
    thread_ids: Callable[[], str],
) -> None:
    """Queried directly against Postgres, not inferred from LangGraph's API.

    That `ask_something`'s result is durable *before* the pause is the whole
    mechanism behind the idempotency test below: the node is checkpointed as
    complete, so a resume has no reason to re-run it.
    """
    thread_id = thread_ids()
    graph = build_skeleton_graph(checkpointer)
    config = _config(thread_id)

    await graph.ainvoke(INITIAL_STATE, config)
    with conn.cursor() as cur:
        cur.execute("select count(*) from checkpoints where thread_id = %s", (thread_id,))
        while_paused = cur.fetchone()[0]
    assert while_paused > 1, f"expected a checkpoint per node, found {while_paused}"

    await graph.ainvoke(Command(resume="an answer"), config)
    conn.rollback()  # end the read transaction so the resume's commits are visible
    with conn.cursor() as cur:
        cur.execute("select count(*) from checkpoints where thread_id = %s", (thread_id,))
        after_resume = cur.fetchone()[0]
    assert after_resume > while_paused, (
        f"resume wrote no new checkpoint: {while_paused} -> {after_resume}"
    )


async def test_llm_call_fires_exactly_once_across_interrupt_and_resume(
    checkpointer: AsyncPostgresSaver,
    thread_ids: Callable[[], str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """THE test of story 0.6. See the module docstring.

    **The call count is the only assertion that catches the violation, and
    that is not obvious.** Measured against a deliberately wrong graph (LLM
    call above `interrupt()` in the same node): two LLM calls, but
    `turn_count` still 1, because LangGraph discards the state writes of a
    node that interrupted and applies them only on the run that completes.
    So the damage from breaking this rule is duplicated *side effects* —
    burned rate budget, doubled external writes, doubled emitted events — not
    corrupted state, and state assertions cannot detect it. Output in
    DEV-STATE § Decisions 2026-07-30.

    `turn_count` is kept as a cheap correctness check on the state math, not
    as a second line of defence.
    """
    graph = build_skeleton_graph(checkpointer)
    config = _config(thread_ids())

    with caplog.at_level(logging.INFO, logger="app.llm"):
        await graph.ainvoke(INITIAL_STATE, config)
        calls_at_pause = _llm_calls(caplog)
        resumed = await graph.ainvoke(Command(resume="my answer"), config)
        calls_after_resume = _llm_calls(caplog)

    assert len(calls_at_pause) == 1, f"expected one call before the pause, got {calls_at_pause}"
    assert len(calls_after_resume) == 1, (
        "ask_something re-ran on resume — the constraint the conduct loop rests on is broken."
        f" Calls: {calls_after_resume}"
    )
    assert resumed["turn_count"] == 1, (
        f"turn_count was incremented {resumed['turn_count']} times across one interrupt cycle"
    )
