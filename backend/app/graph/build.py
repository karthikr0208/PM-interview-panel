"""Graph construction for the REAL interview graph. Story 1.4 gives it its
first two nodes: `level_candidate` (the Resume Analyst) and `confirm_level`
(the first real `interrupt()`).

Story 0.6's two-node skeleton is deliberately not here: it lives in
`skeleton.py`. Story 1.7 (delete the Phase 0 scaffolding) kept it rather
than deleting it whole -- `tests/test_api.py` still has two tests proving
checkpoint state survives a full OS-process teardown/rebuild across two
separate uvicorn processes, a property nothing in `test_confirm_level.py`
asserts. Deferred pending a decision; see DEV-STATE. This file's rule below
is what that skeleton exists to prove.

The full graph (level_candidate -> confirm_level -> ... -> coach_report) is
built incrementally across Phases 1-5. Only the first two nodes exist today.

THE load-bearing rule for every node in this graph, and especially for
`confirm_level` (any node that calls `interrupt()`):

    On resume, LangGraph re-runs the ENTIRE node from the top — not from the
    interrupt() line. A node that calls interrupt() may contain NOTHING
    before it: no LLM call, no counter increment, no state write. All of
    those would silently re-execute on every resume. The node's body is
    `value = interrupt(payload); return {...using value...}` and nothing
    else. See ARCHITECTURE.md §4 and CLAUDE.md.
"""

from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from app.agents.resume_analyst import analyse_resume
from app.graph.state import InterviewState
from app.llm import Role
from app.supabase_client import rest_insert, rest_select_one, rest_update

# Plain language, never raw JSON (schema comment on agent_events;
# PHASE-1-SPEC.md 1.6b). Matches OrchestrationColumn.tsx's DEFAULT_COPY
# fallback exactly, so a candidate sees the same sentence whether the
# frontend renders this real summary or its own fallback while waiting.
_STARTED_SUMMARY = "Reading your resume and assessing a level."
_DONE_SUMMARY = "Read your resume and assessed a level."
_ERROR_SUMMARY = "Ran into a problem understanding your resume."


def _make_level_candidate(
    role: Role = "deep",
) -> Callable[[InterviewState], Awaitable[dict]]:
    """Factory rather than a bare function so tests can build a graph that
    runs the Resume Analyst on `role="fast"` — the property story 1.4 tests
    (does the node execute twice across an interrupt cycle) is model-
    independent graph mechanics, and `deep`'s daily token budget is not
    theirs to spend. Production always gets the spec's default, `deep`
    (AGENT-RESUME-ANALYST-SPEC.md §1); `build_graph`'s own default matches.
    """

    async def level_candidate(state: InterviewState) -> dict:
        """Runs the Resume Analyst and writes its four fields to state.

        Owns every side effect the agent spec assigns to this node (§1):
        one `agent_events` row on start, one on completion (or error), and
        the `resumes.profile` write. `analyse_resume` itself stays a pure
        function with none of these — the eight golden cases call it
        directly with no session and no database (see its own docstring).

        Runs exactly once per session: LangGraph only re-runs an
        *interrupting* node from the top on resume, and this node contains
        no `interrupt()`. `confirm_level`, immediately downstream, is the
        one that must stay side-effect-free.
        """
        session_id = state["session_id"]
        started = time.perf_counter()

        await rest_insert(
            "agent_events",
            {
                "session_id": session_id,
                "agent": "resume_analyst",
                "status": "started",
                "summary": _STARTED_SUMMARY,
            },
        )

        try:
            analysis = await analyse_resume(state["resume_text"], role=role)
        except Exception:
            await rest_insert(
                "agent_events",
                {
                    "session_id": session_id,
                    "agent": "resume_analyst",
                    "status": "error",
                    "summary": _ERROR_SUMMARY,
                },
            )
            raise

        duration_ms = int((time.perf_counter() - started) * 1000)
        profile = analysis.candidate_profile.model_dump()

        # One resume per session is the flow this phase builds (upload,
        # then assess) -- see PHASE-1-SPEC.md 1.6. A candidate who retries
        # an upload gets a fresh `resumes` row each time (story 1.2 inserts,
        # never upserts), so this take-the-first read is a known simplifying
        # assumption, not a guarantee, if assessment somehow starts before
        # the retry settles.
        resume_row = await rest_select_one("resumes", "session_id", session_id, select="id")
        if resume_row is not None:
            await rest_update("resumes", "id", resume_row["id"], {"profile": profile})

        await rest_insert(
            "agent_events",
            {
                "session_id": session_id,
                "agent": "resume_analyst",
                "status": "done",
                "summary": _DONE_SUMMARY,
                "duration_ms": duration_ms,
            },
        )

        return {
            "candidate_profile": profile,
            "assessed_level": analysis.assessed_level,
            "level_rationale": analysis.level_rationale,
            "low_confidence_fields": analysis.low_confidence_fields,
        }

    return level_candidate


def confirm_level(state: InterviewState) -> dict:
    """`interrupt()` and its return. Nothing else, ever -- see module
    docstring and CLAUDE.md "Rules that must never be broken".

    The payload mirrors the frontend's `ResumeAnalysis` shape
    (`frontend/src/lib/types.ts`) exactly, so `/session/{id}/level`'s route
    handler can return it to the browser unchanged. The resumed value is
    the candidate's chosen level (a plain string) -- whether that counts as
    a *correction* is for the caller to decide by comparing it against the
    `assessed_level` already in state, not this node's job: computing that
    here would be a comparison performed above the `interrupt()` line,
    which re-runs on every resume just like anything else in this node.
    """
    chosen_level = interrupt(
        {
            "candidate_profile": state["candidate_profile"],
            "assessed_level": state["assessed_level"],
            "level_rationale": state["level_rationale"],
            "low_confidence_fields": state["low_confidence_fields"],
        }
    )
    return {"assessed_level": chosen_level}


def build_graph(
    checkpointer: BaseCheckpointSaver, *, resume_analyst_role: Role = "deep"
) -> Any:
    """Compiles level_candidate -> confirm_level -> END with the given
    checkpointer attached.

    `checkpointer` must be an `AsyncPostgresSaver` (session pooler, port
    5432) in every environment including local dev. Never `MemorySaver` —
    it hides the entire class of stateless-HTTP bugs this architecture is
    built to surface. See CLAUDE.md "Rules that must never be broken".

    `resume_analyst_role` exists for tests only -- production callers
    (`app/main.py`'s lifespan) never pass it, so they get the spec's
    default of `deep`.
    """
    graph = StateGraph(InterviewState)
    graph.add_node("level_candidate", _make_level_candidate(resume_analyst_role))
    graph.add_node("confirm_level", confirm_level)
    graph.set_entry_point("level_candidate")
    graph.add_edge("level_candidate", "confirm_level")
    graph.add_edge("confirm_level", END)
    return graph.compile(checkpointer=checkpointer)
