"""Graph construction for the REAL interview graph. Module structure only —
node wiring lands in Phase 1, once agents exist.

Story 0.6's two-node skeleton is deliberately not here: it lives in
`skeleton.py` so it can be deleted whole when the real graph arrives. This
file's rule below is what that skeleton exists to prove.

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

    Node wiring grows through Phases 1-5 into the full panel. Left
    unimplemented here on purpose so this module is import-safe before any
    node exists. For Phase 0, use `app.graph.skeleton.build_skeleton_graph`.
    """
    raise NotImplementedError("Node wiring is Phase 1 — Phase 0 uses skeleton.build_skeleton_graph.")
