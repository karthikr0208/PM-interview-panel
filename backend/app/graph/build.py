"""Graph construction. Module structure only — node wiring is story 0.6.

The real graph (parse_resume -> level_candidate -> confirm_level -> ... ->
coach_report) is built here once the nodes exist. Nothing below builds it yet;
this file exists so `build_graph` has a stable import path for the API layer
and for tests before the graph itself is real.

THE load-bearing rule for every node in this graph, and especially for
`await_candidate` / `confirm_level` (any node that calls `interrupt()`):

    On resume, LangGraph re-runs the ENTIRE node from the top — not from the
    interrupt() line. A node that calls interrupt() may contain NOTHING
    before it: no LLM call, no counter increment, no state write. All of
    those would silently re-execute on every resume. The node's body is
    `value = interrupt(payload); return {...using value...}` and nothing
    else. See ARCHITECTURE.md §4 and CLAUDE.md.
"""

from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import StateGraph

from app.graph.state import InterviewState


def build_graph(checkpointer: BaseCheckpointSaver) -> StateGraph:
    """Compiles the interview graph with the given checkpointer attached.

    `checkpointer` must be an `AsyncPostgresSaver` (session pooler, port 5432)
    in every environment including local dev. Never `MemorySaver` — it hides
    the entire class of stateless-HTTP bugs this architecture is built to
    surface. See CLAUDE.md "Rules that must never be broken".

    Node wiring lands in story 0.6 as a two-node skeleton, then grows through
    Phases 1-5 into the full panel. Left unimplemented here on purpose so this
    module is import-safe before any node exists.
    """
    raise NotImplementedError("Node wiring is story 0.6 — not part of the Phase 0.1 scaffold.")
