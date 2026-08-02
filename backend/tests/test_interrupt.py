"""Story 0.6: interrupt and resume on the two-node skeleton graph.

Story 1.7 (delete the Phase 0 scaffolding) removed this file's former
load-bearing test, `test_llm_call_fires_exactly_once_across_interrupt_and_resume`
-- its property is now asserted against the real graph by
`test_confirm_level.py::test_resume_analyst_llm_call_fires_exactly_once_across_the_confirm_cycle`.
The three tests remaining here were left in place because no test in
`test_confirm_level.py` asserts their specific properties: that
`build_skeleton_graph` attaches the real Postgres checkpointer (not
`MemorySaver`), and that raw `checkpoints` rows land in Postgres per node.
See DEV-STATE for the coverage map story 1.7 produced. Deleting them, and
`app/graph/skeleton.py` itself, is deferred pending that decision.

Marked `live` for the same reason as test_checkpointer.py: these hit the real
Supabase project over the session pooler, and `ask_something` hits the real
NVIDIA endpoint. Mocking either would defeat the point of the phase.
Fixtures (`conn`, `checkpointer`, `thread_ids`) come from conftest.py.
"""

from __future__ import annotations

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


def test_graph_compiles_with_the_postgres_checkpointer(
    checkpointer: AsyncPostgresSaver,
) -> None:
    graph = build_skeleton_graph(checkpointer)
    assert graph.checkpointer is checkpointer
    assert not isinstance(graph.checkpointer, MemorySaver), (
        "MemorySaver hides the stateless-HTTP bugs story 0.7 exists to catch"
    )


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
