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
built incrementally across Phases 1-5. Stories 2.3 and 2.6 add
`generate_case_world` (the Case Architect) and `plan_interview` (the
Planner), chained after `confirm_level`. Story 3.2 adds the conduct loop --
`ask_question`, `await_candidate`, `route_input`, `answer_clarification_node`,
`decide_next` -- so the graph now pauses a SECOND kind of interrupt, this one
inside a loop rather than a single pause-and-resume. See that section's own
banner comment below for the loop's shape and its `transcript_turns.idx`
scheme.

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
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Literal

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from app.agents.case_architect import generate_case_world as _generate_case_world
from app.agents.interviewer import answer_clarification as _answer_clarification
from app.agents.interviewer import compose_question, transition_for
from app.agents.planner import plan_interview as _plan_interview
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

_CASE_WORLD_STARTED_SUMMARY = "Building the case for your interview."
_CASE_WORLD_DONE_SUMMARY = "Built the case for your interview."
_CASE_WORLD_ERROR_SUMMARY = "Ran into a problem building the case."

_PLAN_STARTED_SUMMARY = "Planning interview questions."
_PLAN_DONE_SUMMARY = "Planned interview questions."
_PLAN_ERROR_SUMMARY = "Ran into a problem planning the interview."

_ASK_STARTED_SUMMARY = "Asking the next interview question."
_ASK_DONE_SUMMARY = "Asked the next interview question."
# No _ASK_ERROR_SUMMARY: `ask_question` became fully deterministic on
# 2026-08-05 and has no failure mode to report. Kept out rather than kept
# unused -- an error summary nothing can emit is a promise the UI would
# never see honoured.

_CLARIFY_STARTED_SUMMARY = "Answering your clarifying question."
_CLARIFY_DONE_SUMMARY = "Answered your clarifying question."
_CLARIFY_ERROR_SUMMARY = "Ran into a problem answering your clarifying question."


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


def _make_generate_case_world(
    role: Role = "fast",
) -> Callable[[InterviewState], Awaitable[dict]]:
    """Factory, same reasoning as `_make_level_candidate`: tests build a
    graph on `role="fast"` (or any other role) without touching production's
    default. Story 2.3's brief supersedes AGENT-CASE-ARCHITECT-SPEC.md §1's
    `deep` default as of 2026-08-02 -- `build_graph`'s own default matches.
    """

    async def generate_case_world(state: InterviewState) -> dict:
        """Runs the Case Architect and writes `case_world` to state.

        Owns every side effect the agent spec assigns to this node (§1):
        one `agent_events` row on start, one on completion (or error), and
        the `case_worlds` insert (the audit copy -- the working copy lives
        in graph state). `generate_case_world` (the agent function) stays
        pure, with none of these -- the golden cases call it directly with
        no session and no database.

        Reads `assessed_level` from STATE, never from `candidate_profile` --
        `confirm_level`, immediately upstream, may have overwritten it with
        the candidate's correction. Trap named in the brief: an agent that
        infers the level from the profile instead would silently discard
        every correction, and no golden case would catch it, since golden
        cases pass a level directly and never exercise the correction path.
        """
        session_id = state["session_id"]
        started = time.perf_counter()

        await rest_insert(
            "agent_events",
            {
                "session_id": session_id,
                "agent": "case_architect",
                "status": "started",
                "summary": _CASE_WORLD_STARTED_SUMMARY,
            },
        )

        try:
            case_world = await _generate_case_world(
                state["assessed_level"], state["candidate_profile"], role=role
            )
        except Exception:
            await rest_insert(
                "agent_events",
                {
                    "session_id": session_id,
                    "agent": "case_architect",
                    "status": "error",
                    "summary": _CASE_WORLD_ERROR_SUMMARY,
                },
            )
            raise

        duration_ms = int((time.perf_counter() - started) * 1000)
        world_dict = case_world.model_dump()

        await rest_insert("case_worlds", {"session_id": session_id, "world": world_dict})

        await rest_insert(
            "agent_events",
            {
                "session_id": session_id,
                "agent": "case_architect",
                "status": "done",
                "summary": _CASE_WORLD_DONE_SUMMARY,
                "duration_ms": duration_ms,
            },
        )

        return {"case_world": world_dict}

    return generate_case_world


def _make_plan_interview(
    role: Role = "fast",
) -> Callable[[InterviewState], Awaitable[dict]]:
    """Factory, same reasoning as `_make_level_candidate` and
    `_make_generate_case_world`. Story 2.6's brief supersedes
    AGENT-PLANNER-SPEC.md §1's `deep` default as of 2026-08-02 --
    `build_graph`'s own default matches.
    """

    async def plan_interview(state: InterviewState) -> dict:
        """Runs the Planner and writes `question_plan` to state.

        Owns every side effect the agent spec assigns to this node (§1):
        one `agent_events` row on start, one on completion (or error). No
        table insert -- the spec lists none for this agent; `question_plan`
        lives only in graph state. `plan_interview` (the agent function)
        stays pure, with none of these.

        Reads `case_world` from state and passes it through unchanged.
        `case_world` is NOT part of this node's return dict -- it was
        already written once, by `generate_case_world`, and stays immutable
        for the rest of the graph (ARCHITECTURE §2). Returning it here,
        even with the same value, would be a second write to the field the
        whole architecture depends on staying untouched downstream.
        """
        session_id = state["session_id"]
        started = time.perf_counter()

        await rest_insert(
            "agent_events",
            {
                "session_id": session_id,
                "agent": "planner",
                "status": "started",
                "summary": _PLAN_STARTED_SUMMARY,
            },
        )

        try:
            plan = await _plan_interview(
                state["assessed_level"], state["case_world"], role=role
            )
        except Exception:
            await rest_insert(
                "agent_events",
                {
                    "session_id": session_id,
                    "agent": "planner",
                    "status": "error",
                    "summary": _PLAN_ERROR_SUMMARY,
                },
            )
            raise

        duration_ms = int((time.perf_counter() - started) * 1000)

        await rest_insert(
            "agent_events",
            {
                "session_id": session_id,
                "agent": "planner",
                "status": "done",
                "summary": _PLAN_DONE_SUMMARY,
                "duration_ms": duration_ms,
            },
        )

        return {"question_plan": [q.model_dump() for q in plan.questions]}

    return plan_interview


# ═══════════════════════════════════════════════════════════════════════
# Story 3.2: the conduct loop. Five graph waypoints, per PHASE-3-SPEC.md:
#
#   plan_interview -> ask_question -> await_candidate -> route_input
#       clarify -> answer_clarification_node -> await_candidate
#       answer  -> decide_next
#           ask  -> ask_question
#           exit -> END
#
# `transcript_turns.idx` is `len(state["messages"])` at the moment a node
# writes its OWN utterance -- i.e. the index the message it is about to
# append will occupy once merged. `messages` only ever grows in this loop
# (both the candidate's and the Interviewer's turns are appended to it, via
# `add_messages`), so this is monotonic and unique per session without a
# separate counter field. Only the Interviewer's own generated utterances
# are mirrored into `transcript_turns` (ask_question's question,
# answer_clarification_node's answer) -- the candidate's words live in
# `messages`, durable via the Postgres checkpointer, which is this phase's
# "transcript in state" (PHASE-3-SPEC.md's own "Done when" bar). Phase 4
# will need to decide how the Evaluator sources the candidate's raw answer
# text; deferred rather than guessed at here. See story 3.2's final report.
# ═══════════════════════════════════════════════════════════════════════


def _make_ask_question(
    role: Role = "fast",
) -> Callable[[InterviewState], Awaitable[dict]]:
    """Factory, same reasoning as the three above: tests build a graph on
    `role="fast"` (or any other role) without touching production's
    default. AGENT-INTERVIEWER-SPEC.md §1 and §8 both land on `fast` as the
    production default already -- this parameter exists for symmetry with
    the other three roles and so a future measurement can change it at the
    call site without touching this function's body.
    """

    async def ask_question(state: InterviewState) -> dict:
        """The only node that composes an utterance the candidate reads,
        and as of 2026-08-05 it is FULLY DETERMINISTIC: **zero LLM calls,
        on every question, always.**

        It used to spend one `fast` call on a bridge line for question 2+.
        That call was measured to be a constant function -- six materially
        different candidate answers produced the same sentence with the
        words shuffled -- so it was replaced by `transition_for`, a rotating
        set of source strings. The em-dash ban on this surface is now
        STATICALLY enforced by `tests/test_user_facing_copy.py` rather than
        merely prompted, which matters because prompting had already failed
        twice on that exact rule. See DEV-STATE § Decisions 2026-08-05.

        The planned question text is never regenerated: `compose_question`
        copies it byte for byte from `question_plan` (spec §2a's central
        rule).

        Consequence worth carrying: `answer_clarification_node` is now the
        ONLY LLM call in the entire conduct loop, which is what the
        call-count assertions in `tests/test_conduct_loop.py` rest on.

        Owns every side effect this node is responsible for: one
        `agent_events` row on start, one on completion (or error), and one
        `transcript_turns` row for the composed question. Sets
        `started_at` only on question 1 -- every later call leaves it
        alone, so `decide_next`'s elapsed-time read is stable across the
        whole loop.
        """
        session_id = state["session_id"]
        q_idx = state.get("current_q_idx", 0)
        planned = state["question_plan"][q_idx]

        started = time.perf_counter()
        await rest_insert(
            "agent_events",
            {
                "session_id": session_id,
                "agent": "interviewer",
                "status": "started",
                "summary": _ASK_STARTED_SUMMARY,
            },
        )

        # No try/except around this any more: `transition_for` is total
        # (a tuple index and a modulo) and cannot fail, so an error branch
        # here would be unreachable code pretending to be a guard. The
        # `agent_events` error row it used to write covered the bridge's
        # LLM call, which no longer exists.
        question_text = compose_question(planned["question"], transition_for(q_idx))
        duration_ms = int((time.perf_counter() - started) * 1000)

        idx = len(state.get("messages") or [])
        await rest_insert(
            "transcript_turns",
            {
                "session_id": session_id,
                "idx": idx,
                "role": "interviewer",
                "kind": "question",
                "content": question_text,
            },
        )
        await rest_insert(
            "agent_events",
            {
                "session_id": session_id,
                "agent": "interviewer",
                "status": "done",
                "summary": _ASK_DONE_SUMMARY,
                "duration_ms": duration_ms,
            },
        )

        dimension_coverage = dict(state.get("dimension_coverage") or {})
        dimension = planned["primary_dimension"]
        dimension_coverage[dimension] = dimension_coverage.get(dimension, 0) + 1

        update: dict = {
            "messages": [AIMessage(content=question_text, additional_kwargs={"kind": "question"})],
            "current_q_idx": q_idx + 1,
            "dimension_coverage": dimension_coverage,
        }
        if q_idx == 0:
            update["started_at"] = datetime.now(timezone.utc).isoformat()
        return update

    return ask_question


def await_candidate(state: InterviewState) -> dict:
    """`interrupt()` and its return. Nothing else, ever -- see module
    docstring and CLAUDE.md "Rules that must never be broken". LangGraph
    re-runs this ENTIRE node from the top on every resume, so anything
    computed above the `interrupt()` line would silently re-run on every
    single candidate turn for the rest of the interview -- the exact bug
    `scripts/falsify_looping_interrupt.py` demonstrates against a
    deliberately wrong graph.

    The payload surfaces the LAST thing state already holds -- the question
    just asked, or the clarification answer just given -- by reading
    `messages[-1]`, exactly like `confirm_level`'s payload above: a pure
    read of an already-computed value, not a new computation. `kind`
    (written by `ask_question` / `answer_clarification_node` into each
    message's `additional_kwargs`) tells the caller which of the two this
    is, so the HTTP layer can distinguish "here is the next question" from
    "here is your clarification answer; the original question is still
    owed."

    The resumed value -- `{"type": "answer"|"clarify", "text": str}` -- is
    written to BOTH `messages` (the durable, checkpointer-backed
    transcript) and `last_input` (so `route_input` and the next node can
    read the type/text without re-deriving it from `messages`). Both come
    straight from `value`; nothing above the `interrupt()` line computed
    either.
    """
    existing = state.get("messages") or []
    last_message = existing[-1] if existing else None
    value = interrupt(
        {
            "kind": (last_message.additional_kwargs or {}).get("kind") if last_message else None,
            "text": last_message.content if last_message else None,
            "current_q_idx": state.get("current_q_idx", 0),
        }
    )
    return {
        "messages": [HumanMessage(content=value.get("text", ""))],
        "last_input": value,
    }


def route_input(state: InterviewState) -> Literal["clarify", "answer"]:
    """Conditional edge off `await_candidate`. Deterministic: reads the
    type of the just-resumed payload from `last_input`, which
    `await_candidate`'s own return already wrote -- no computation of its
    own beyond a dict lookup. Defaults to "answer" on a missing/unknown
    type rather than raising, matching this graph's uniform failure
    behaviour of not stalling the interview on a malformed client payload.
    """
    reply_type = (state.get("last_input") or {}).get("type")
    return "clarify" if reply_type == "clarify" else "answer"


def _make_answer_clarification_node(
    role: Role = "fast",
) -> Callable[[InterviewState], Awaitable[dict]]:
    """Factory, same reasoning as the others above."""

    async def answer_clarification_node(state: InterviewState) -> dict:
        """Answers ONE clarifying question from `case_world` alone, writes
        its own `transcript_turns` row and `agent_events` rows, appends its
        answer to `messages`, then routes back to `await_candidate` -- the
        candidate still owes an answer to the planned question, and
        `current_q_idx` has NOT advanced past it (only `ask_question`
        advances it).

        Reads the still-pending planned question from
        `question_plan[current_q_idx - 1]` -- `current_q_idx` already
        points PAST the question currently on the table, because
        `ask_question` increments it the moment it asks.
        """
        session_id = state["session_id"]
        clarifying_question = (state.get("last_input") or {}).get("text", "")
        pending_idx = max(state.get("current_q_idx", 1) - 1, 0)
        planned_question = state["question_plan"][pending_idx]["question"]

        started = time.perf_counter()
        await rest_insert(
            "agent_events",
            {
                "session_id": session_id,
                "agent": "interviewer",
                "status": "started",
                "summary": _CLARIFY_STARTED_SUMMARY,
            },
        )

        try:
            result = await _answer_clarification(
                state["case_world"], planned_question, clarifying_question, role=role
            )
        except Exception:
            await rest_insert(
                "agent_events",
                {
                    "session_id": session_id,
                    "agent": "interviewer",
                    "status": "error",
                    "summary": _CLARIFY_ERROR_SUMMARY,
                },
            )
            raise

        duration_ms = int((time.perf_counter() - started) * 1000)

        idx = len(state.get("messages") or [])
        await rest_insert(
            "transcript_turns",
            {
                "session_id": session_id,
                "idx": idx,
                "role": "interviewer",
                # Neither "question" nor "answer" (the candidate's own kind,
                # never written by this agent) nor "followup" (Phase 3
                # builds no probe edge) -- "meta" is the honest bucket for
                # an aside answering a clarification, not advancing the plan.
                "kind": "meta",
                "content": result.answer,
            },
        )
        await rest_insert(
            "agent_events",
            {
                "session_id": session_id,
                "agent": "interviewer",
                "status": "done",
                "summary": _CLARIFY_DONE_SUMMARY,
                "duration_ms": duration_ms,
            },
        )

        return {
            "messages": [AIMessage(content=result.answer, additional_kwargs={"kind": "clarification"})],
        }

    return answer_clarification_node


# The ONE place the exit condition lives (PHASE-3-SPEC.md 3.2's 🔴
# requirement). Phase 3 asks 2-3 questions, never the plan's full 5-7 --
# CLAUDE.md's portfolio calibration, restated at the top of PHASE-3-SPEC.md.
_QUESTIONS_THIS_PHASE = 3

# Safety valve, not the primary exit path: at 2-3 questions this almost
# never fires, but a candidate who spends a long time on clarifications
# should not turn a 45-minute interview into an unbounded one.
_TIME_BUDGET_MINUTES = 40


def _decide_next_node(state: InterviewState) -> dict:
    """No-op body. Exists only because LangGraph's conditional-edge
    `path_map` values must name a real node: `route_input`'s "answer"
    branch needs a destination before `decide_next` (below)'s own outgoing
    conditional edge -- registered under this SAME node name -- can read
    state and choose ask/exit. Writes nothing: this phase mirrors only the
    Interviewer's own utterances into `transcript_turns` (see the module
    banner above), and this node exists between two of the candidate's, not
    the Interviewer's.
    """
    return {}


def decide_next(state: InterviewState) -> Literal["ask", "exit"]:
    """Deterministic Python, NO LLM call, no I/O -- pure enough to test
    directly against a bare dict, offline. Reads `followup_count`, elapsed
    time (from `started_at`) and `dimension_coverage` from state, per
    PHASE-3-SPEC.md 3.2's acceptance box.

    `followup_count` MUST be 0 for the whole of Phase 3: no probe edge
    exists in this graph (AGENT-INTERVIEWER-SPEC.md §2c -- probing needs
    answer quality, a score Phase 4 produces, and building it now would be
    unfalsifiable). Asserted rather than merely read: a nonzero value here
    means something wrote to a field this graph has no edge to act on,
    which is a real bug worth surfacing loudly, not absorbing silently.

    `dimension_coverage` is read but does not gate the decision in this
    phase. Phase 3 fills it from the ASKED question's `primary_dimension`
    (the Planner's own field, `ask_question`'s write) rather than from a
    score, because no score exists yet (PHASE-3-SPEC.md's opening section).
    Deciding "have we covered enough" needs that same score to know whether
    a question was answered adequately, so coverage stays informational
    here; Phase 4 is expected to replace the SOURCE without changing this
    function's shape.

    The exit condition lives in exactly ONE place: `_QUESTIONS_THIS_PHASE`.
    """
    followup_count = state.get("followup_count", 0)
    assert followup_count == 0, (
        "decide_next assumes no probe edge exists in Phase 3 (spec §2c), but "
        f"followup_count={followup_count} -- something wrote to a field this "
        "graph has no edge to act on"
    )
    _ = state.get("dimension_coverage", {})  # read; not yet gated on, see docstring

    if state.get("current_q_idx", 0) >= _QUESTIONS_THIS_PHASE:
        return "exit"

    started_at = state.get("started_at")
    if started_at:
        elapsed = datetime.now(timezone.utc) - datetime.fromisoformat(started_at)
        if elapsed >= timedelta(minutes=_TIME_BUDGET_MINUTES):
            return "exit"

    return "ask"


def build_graph(
    checkpointer: BaseCheckpointSaver,
    *,
    resume_analyst_role: Role = "deep",
    case_architect_role: Role = "fast",
    planner_role: Role = "deep",
    interviewer_role: Role = "fast",
) -> Any:
    """Compiles level_candidate -> confirm_level -> generate_case_world ->
    plan_interview -> ask_question -> await_candidate -> ... -> END (the
    conduct loop, story 3.2) with the given checkpointer attached.

    `checkpointer` must be an `AsyncPostgresSaver` (session pooler, port
    5432) in every environment including local dev. Never `MemorySaver` —
    it hides the entire class of stateless-HTTP bugs this architecture is
    built to surface. See CLAUDE.md "Rules that must never be broken".

    `resume_analyst_role` exists for tests only -- production callers
    (`app/main.py`'s lifespan) never pass it, so they get the spec's
    default of `deep`.

    `case_architect_role` defaults to `fast`: its agent spec says `deep`, but
    that default is superseded as of 2026-08-02 (see CLAUDE.md's portfolio
    calibration) and it was measured passing its golden smoke on `fast` on
    2026-08-04.

    `planner_role` is back to `deep`, and it is the one agent the calibration
    does NOT apply to. Measured 2026-08-04: `fast` fails Groq's strict schema
    validation on `QuestionPlan` twice in a row, so this is a correctness
    constraint, not a quality preference. See `plan_interview`'s docstring and
    DEV-STATE § Decisions 2026-08-04. Kept as parameters, not hardcoded, so
    production can switch either at the call site without touching this
    function's body.

    `interviewer_role` defaults to `fast` -- the one agent where
    ARCHITECTURE §4's table and the portfolio calibration agree
    (AGENT-INTERVIEWER-SPEC.md §1/§8): it is the only agent that runs while
    a candidate is watching a cursor.
    """
    graph = StateGraph(InterviewState)
    graph.add_node("level_candidate", _make_level_candidate(resume_analyst_role))
    graph.add_node("confirm_level", confirm_level)
    graph.add_node("generate_case_world", _make_generate_case_world(case_architect_role))
    graph.add_node("plan_interview", _make_plan_interview(planner_role))
    graph.add_node("ask_question", _make_ask_question(interviewer_role))
    graph.add_node("await_candidate", await_candidate)
    graph.add_node("answer_clarification_node", _make_answer_clarification_node(interviewer_role))
    graph.add_node("decide_next", _decide_next_node)
    graph.set_entry_point("level_candidate")
    graph.add_edge("level_candidate", "confirm_level")
    graph.add_edge("confirm_level", "generate_case_world")
    graph.add_edge("generate_case_world", "plan_interview")
    graph.add_edge("plan_interview", "ask_question")
    graph.add_edge("ask_question", "await_candidate")
    graph.add_conditional_edges(
        "await_candidate",
        route_input,
        {"clarify": "answer_clarification_node", "answer": "decide_next"},
    )
    graph.add_edge("answer_clarification_node", "await_candidate")
    graph.add_conditional_edges("decide_next", decide_next, {"ask": "ask_question", "exit": END})
    return graph.compile(checkpointer=checkpointer)
