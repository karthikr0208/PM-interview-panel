"""Story 0.5: the Postgres checkpointer — the substrate every later phase
depends on. If a checkpoint row does not really land after each node, or RLS
does not really block anon/authenticated, both are invisible failures right
up until Phase 3's actual interview state (resume text, full transcript,
every evaluation) leaks or silently vanishes mid-interview.

Every test here is marked `live` and hits the real Supabase project over the
session pooler. Deselect with `-m "not live"`.

Two pitfalls already discovered today, both handled in `conftest.py`, which
owns the `conn` / `checkpointer` / `thread_ids` fixtures used below:
  1. Windows' default ProactorEventLoop makes psycopg's async mode raise
     `InterfaceError: Psycopg cannot use the 'ProactorEventLoop'`. The policy
     swap must happen before any AsyncPostgresSaver is touched, so it runs at
     conftest import time, same as scripts/init_db.py.
  2. AsyncPostgresSaver sets a `dict_row` row factory on its own connection.
     Every verification query in this file goes through the `conn` fixture's
     *separate* plain connection, which returns normal tuples — the same
     reason test_schema.py does it, and the same reason cleanup must bypass
     RLS through that plain connection rather than the checkpointer's.
"""

from __future__ import annotations

from typing import Callable, TypedDict

import psycopg
import pytest
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, StateGraph

pytestmark = pytest.mark.live

# checkpoint_migrations is LangGraph's own version tracker — never truncated
# by cleanup below, but still asserted to exist alongside the other three.
CHECKPOINT_TABLES = ("checkpoints", "checkpoint_writes", "checkpoint_blobs", "checkpoint_migrations")


class CounterState(TypedDict):
    counter: int


def _increment(state: CounterState) -> dict:
    return {"counter": state["counter"] + 1}


def _build_counter_graph(checkpointer: AsyncPostgresSaver):
    """Minimal 2-node graph — `a` then `b`, each incrementing `counter` by
    one — matching PHASE-0-SPEC.md story 0.6's `SkeletonState` shape.
    Deliberately not the real interview graph; this file only needs enough
    structure to prove checkpoint rows land in Postgres after each node.
    """
    graph = StateGraph(CounterState)
    graph.add_node("a", _increment)
    graph.add_node("b", _increment)
    graph.set_entry_point("a")
    graph.add_edge("a", "b")
    graph.add_edge("b", END)
    return graph.compile(checkpointer=checkpointer)


async def test_setup_is_idempotent_and_creates_all_tables(
    checkpointer: AsyncPostgresSaver, conn: psycopg.Connection
) -> None:
    await checkpointer.setup()
    await checkpointer.setup()  # second run must not raise — this is the box being ticked

    with conn.cursor() as cur:
        cur.execute(
            "select tablename from pg_tables where schemaname = 'public' and tablename = any(%s)",
            (list(CHECKPOINT_TABLES),),
        )
        found = {row[0] for row in cur.fetchall()}
    assert found == set(CHECKPOINT_TABLES), f"expected {CHECKPOINT_TABLES}, found {found}"


def test_rls_enabled_on_every_checkpoint_table(conn: psycopg.Connection) -> None:
    """LangGraph creates these tables WITHOUT row level security; init_db.py
    enables it afterward. `anon`/`authenticated` hold default grants in
    `public`, so an unprotected checkpoint table is a total read (and, per
    init_db.py's measurement, write/delete) exposure of every interview's
    resume text, transcript, and evaluations."""
    with conn.cursor() as cur:
        cur.execute(
            "select tablename, rowsecurity from pg_tables "
            "where schemaname = 'public' and tablename = any(%s)",
            (list(CHECKPOINT_TABLES),),
        )
        rows = dict(cur.fetchall())
    assert set(rows) == set(CHECKPOINT_TABLES), f"missing tables: {set(CHECKPOINT_TABLES) - set(rows)}"
    for table, enabled in rows.items():
        assert enabled is True, f"RLS is not enabled on {table}"


async def test_rls_denies_anon_and_authenticated_with_a_real_checkpoint(
    checkpointer: AsyncPostgresSaver,
    conn: psycopg.Connection,
    thread_ids: Callable[[], str],
) -> None:
    """`rowsecurity = true` alone (the test above) does not prove the data is
    hidden — it would not catch a policy accidentally opening the table back
    up later. This proves it empirically, against a checkpoint written by a
    real graph, not a hand-inserted row.

    RLS with zero policies *filters* rows for a denied role rather than
    raising — asserting "an exception was thrown" would be testing the wrong
    behavior. Row counts are the correct assertion.
    """
    thread_id = thread_ids()
    graph = _build_counter_graph(checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    await graph.ainvoke({"counter": 0}, config)

    with conn.cursor() as cur:
        cur.execute("select count(*) from checkpoints where thread_id = %s", (thread_id,))
        assert cur.fetchone()[0] > 0, "checkpoint row not visible to the connecting (service) role"

        cur.execute("set local role anon")
        cur.execute("select count(*) from checkpoints where thread_id = %s", (thread_id,))
        assert cur.fetchone()[0] == 0, "anon can read a checkpoint RLS with no policies should hide"

        cur.execute("set local role authenticated")
        cur.execute("select count(*) from checkpoints where thread_id = %s", (thread_id,))
        assert cur.fetchone()[0] == 0, "authenticated can read a checkpoint RLS with no policies should hide"

        cur.execute("reset role")
    conn.rollback()


async def test_checkpoint_row_exists_after_each_node(
    checkpointer: AsyncPostgresSaver,
    conn: psycopg.Connection,
    thread_ids: Callable[[], str],
) -> None:
    """Queried directly against Postgres, not inferred from LangGraph's own
    API — the acceptance box this proves is that the rows are really there,
    not merely that the client claims they are."""
    thread_id = thread_ids()
    graph = _build_counter_graph(checkpointer)
    config = {"configurable": {"thread_id": thread_id}}

    result = await graph.ainvoke({"counter": 0}, config)
    assert result["counter"] == 2, "both nodes should have run"

    with conn.cursor() as cur:
        cur.execute("select count(*) from checkpoints where thread_id = %s", (thread_id,))
        count = cur.fetchone()[0]
    assert count > 1, f"expected more than one checkpoint (one per node), found {count}"


async def test_thread_id_isolation(
    checkpointer: AsyncPostgresSaver, thread_ids: Callable[[], str]
) -> None:
    """Two different thread_ids must not see each other's state — the same
    property that will keep two candidates' concurrent interviews apart."""
    graph = _build_counter_graph(checkpointer)
    thread_a, thread_b = thread_ids(), thread_ids()
    config_a = {"configurable": {"thread_id": thread_a}}
    config_b = {"configurable": {"thread_id": thread_b}}

    await graph.ainvoke({"counter": 0}, config_a)
    await graph.ainvoke({"counter": 100}, config_b)

    state_a = await graph.aget_state(config_a)
    state_b = await graph.aget_state(config_b)

    assert state_a.values["counter"] == 2, "thread A's state was contaminated by thread B"
    assert state_b.values["counter"] == 102, "thread B's state was contaminated by thread A"
