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

Story 4.3 adds `evaluate_answer_node` (the Evaluator) on the edge between
`decide_next` and its routing conditional, so every answer is scored on the
way out of its turn INCLUDING the last one. That placement is load-bearing and
is argued in the node's own docstring; the one thing to carry from here is
that it is not in `await_candidate` and never may be.

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

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Literal

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.types import interrupt

from app.agents.evaluator import evaluate_answer
from app.agents.interviewer import answer_clarification as _answer_clarification
from app.agents.interviewer import (
    angles_match,
    compose_question,
    generate_probe,
    resolve_primary_dimension,
    select_probe_angle,
    transition_for,
)
from app.agents.planner import plan_interview as _plan_interview
from app.agents.resume_analyst import analyse_resume
from app.cases import select_case_world as _select_case_world
from app.graph.state import InterviewState
from app.llm import Role
from app.supabase_client import rest_insert, rest_select_one, rest_update
from app.text import normalize_dashes

# 🔴 Deliberately NOT "app.llm". The live tests count records on that logger
# to assert one LLM call per turn, and a graph-level record landing there
# would perturb a call count. The message does not begin `llm_call` either,
# which is the other half of what `_ok_llm_calls` filters on.
logger = logging.getLogger("app.graph")

# Plain language, never raw JSON (schema comment on agent_events;
# PHASE-1-SPEC.md 1.6b). Matches OrchestrationColumn.tsx's DEFAULT_COPY
# fallback exactly, so a candidate sees the same sentence whether the
# frontend renders this real summary or its own fallback while waiting.
_STARTED_SUMMARY = "Reading your resume and assessing a level."
_DONE_SUMMARY = "Read your resume and assessed a level."
_ERROR_SUMMARY = "Ran into a problem understanding your resume."

# 🔴 "Choosing", not "Building", since 2026-08-07. This node stopped
# GENERATING a case world on 2026-08-06: `generate_case_world` calls
# `select_case_world`, which is deterministic Python picking one of eight
# curated real companies, and makes ZERO LLM calls. "Built the case for your
# interview" described work that no longer happens. On a portfolio artifact
# whose subject IS multi-agent orchestration, an agent credited with
# generation it does not do is the first thing a reader would catch.
_CASE_WORLD_STARTED_SUMMARY = "Choosing the company for your interview."
_CASE_WORLD_DONE_SUMMARY = "Chose the company for your interview."
_CASE_WORLD_ERROR_SUMMARY = "Ran into a problem choosing the company."

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

_PROBE_STARTED_SUMMARY = "Following up on your answer."
_PROBE_DONE_SUMMARY = "Followed up on your answer."
_PROBE_ERROR_SUMMARY = "Ran into a problem following up on your answer."

_EVALUATE_STARTED_SUMMARY = "Scoring your answer against the rubric."
_EVALUATE_DONE_SUMMARY = "Scored your answer against the rubric."
_EVALUATE_ERROR_SUMMARY = "Ran into a problem scoring your answer."


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
    """Factory, kept for signature compatibility with every caller (including
    `build_graph(case_architect_role=...)`). `role` is accepted and IGNORED:
    PHASE-3.5-SPEC.md "THREE DECISIONS THIS PHASE REVERSES" #1 replaces the
    generative Case Architect with `select_case_world`
    (`app/cases/__init__.py`), a deterministic pick among eight curated,
    real-company fact sheets -- zero LLM tokens per interview, and no `role`
    to pass one to.
    """

    async def generate_case_world(state: InterviewState) -> dict:
        """Picks a curated `CaseWorld` and writes it to state.

        Owns every side effect the agent spec assigns to this node (§1):
        one `agent_events` row on start, one on completion (or error), and
        the `case_worlds` insert (the audit copy -- the working copy lives
        in graph state). `select_case_world` itself stays pure and
        synchronous, with none of these -- the offline suite calls it
        directly with no session and no database.

        Reads `assessed_level` from STATE, never from `candidate_profile` --
        `confirm_level`, immediately upstream, may have overwritten it with
        the candidate's correction. Trap named in the brief: code that
        infers the level from the profile instead would silently discard
        every correction, and no offline test would catch it, since those
        tests pass a level directly and never exercise the correction path.
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
            case_world = _select_case_world(
                state["assessed_level"], state["candidate_profile"]
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
# Story 3.2: the conduct loop. Six graph waypoints as of story 3.5.4, per
# PHASE-3.5-SPEC.md "THREE DECISIONS" #3:
#
#   plan_interview -> ask_question -> await_candidate -> route_input
#       clarify -> answer_clarification_node -> await_candidate
#       answer  -> decide_next
#           ask   -> ask_question   (only ever fires once -- one question)
#           probe -> ask_probe -> await_candidate
#           exit  -> END
#
# 🔴 Story 3.5.4 reopens this loop: `question_plan` now holds exactly ONE
# question (`_QUESTIONS_THIS_PHASE = 1`), and the rubric coverage that used
# to come from asking 3 different questions now comes from PROBING the one
# question 6-8 times against what the candidate actually said. `ask_probe`
# is a second LLM-calling node alongside `answer_clarification_node` --
# `answer_clarification` is no longer the ONLY LLM call in the loop.
#
# `transcript_turns.idx` is `len(state["messages"])` at the moment a node
# writes its OWN utterance -- i.e. the index the message it is about to
# append will occupy once merged. `messages` only ever grows in this loop
# (both the candidate's and the Interviewer's turns are appended to it, via
# `add_messages`), so this is monotonic and unique per session without a
# separate counter field.
#
# 🔴 Story 3.5.1: BOTH sides of the conversation are mirrored into
# `transcript_turns` now, not just the Interviewer's. Before this story only
# ask_question's question and answer_clarification_node's answer got a row,
# so a finished interview stored 3 questions + 1 clarification and ZERO
# candidate answers -- a schema-shaped gap the DDL never had (`role` and
# `kind` already covered `candidate`/`answer`/`clarify`), just a missing
# write. Phase 4's Evaluator reads the candidate's answer from here.
#
# The candidate's own turn is written by the node that runs IMMEDIATELY
# after `await_candidate`'s resume, at `idx = len(messages) - 1` --
# `await_candidate`'s return already merged the candidate's HumanMessage
# into `messages` before that next node runs, so the row is for the turn
# that just arrived, not the next one:
#   - clarify path: `answer_clarification_node` (also still writes its own
#     "meta" answer at the unchanged `idx = len(messages)`)
#   - answer path: `_decide_next_node`, NOT `ask_question` or `ask_probe`.
#     `route_input`'s "answer" edge always lands on `_decide_next_node`
#     first, whether the loop is about to probe again or exit -- and once
#     `decide_next()` returns "exit", END is reached straight from
#     `_decide_next_node` without ever calling `ask_probe` again. Writing
#     the candidate's last answer in `ask_question` or `ask_probe` would
#     silently drop it. `await_candidate` itself stays untouched -- it may
#     still contain nothing but `interrupt()` and its return.
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

        This node itself still costs zero LLM calls, always -- as of story
        3.5.4 it just is not the ONLY node in the loop that ever ran an LLM
        call any more: `ask_probe` (below) is the interview's real per-turn
        call, `answer_clarification_node` its clarification-turn one.

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
        # `normalize_dashes` at the BOUNDARY, never inside `compose_question`
        # -- that function emits the Planner's question byte for byte by
        # contract, and normalising in the agents would make the golden
        # suites' `no_dash_variants` assertions vacuous. See `app/text.py`.
        question_text = normalize_dashes(
            compose_question(planned["question"], transition_for(q_idx))
        )
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
    # 🔴 The candidate's turn carries its KIND, added 2026-08-08 after a live
    # interview quoted a candidate's CLARIFYING QUESTION back to them as their
    # own position: "You said OpenAI is a straightforward for-profit company
    # answerable to shareholders" -- a false premise the candidate had merely
    # ASKED about, and which `answer_clarification` had already correctly
    # refused. `route_input` knew the difference; `messages` threw it away, so
    # every reader downstream saw one undifferentiated candidate turn.
    #
    # Same `additional_kwargs["kind"]` channel `ask_question` and
    # `answer_clarification_node` already use on the interviewer's side, so
    # this adds a convention rather than inventing one. Still a pure read of
    # `value` BELOW the interrupt -- no computation moves above that line.
    return {
        "messages": [
            HumanMessage(
                content=value.get("text", ""),
                additional_kwargs={
                    "kind": (
                        "clarifying_question"
                        if value.get("type") == "clarify"
                        else "answer"
                    )
                },
            )
        ],
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
        """Answers ONE clarifying question from `case_world` PLUS
        `improvised_facts` (PHASE-3.5-SPEC.md "THREE DECISIONS" #2 -- the
        refusal branch is gone; a silent case world now gets an INVENTED,
        stated-as-given answer instead), writes its own `transcript_turns`
        row and `agent_events` rows, appends its answer to `messages`, then
        routes back to `await_candidate` -- the candidate still owes an
        answer to the planned question, and `current_q_idx` has NOT
        advanced past it (only `ask_question` advances it).

        Reads the still-pending planned question from
        `question_plan[current_q_idx - 1]` -- `current_q_idx` already
        points PAST the question currently on the table, because
        `ask_question` increments it the moment it asks.

        Story 3.5.1: also writes the CANDIDATE's clarifying question to
        `transcript_turns` -- this node is the one that runs immediately
        after `await_candidate`'s resume on the clarify path, per the
        module banner comment above. `idx = len(messages) - 1` because
        `await_candidate`'s return already merged the candidate's
        HumanMessage before this node runs; this node's OWN row (the
        Interviewer's answer, below) keeps its unchanged `idx =
        len(messages)`, one higher.

        🔴 Story 3.5.4: appends to `improvised_facts` ONLY when
        `result.improvised_fact` is non-empty -- NEVER when `can_answer` is
        False. Measured live 2026-08-06: asking about the SAME fact a
        second time returns `can_answer=True` with an EMPTY
        `improvised_fact`, because the fact is now established (it is
        already in the `improvised_facts` list the model was given). Keying
        this off `can_answer` would re-append the same fact on every
        repeat, and `improvised_facts` is append-only with no dedupe --
        `state["improvised_facts"]` would grow one entry per repeat asking
        of a fact already recorded.
        """
        session_id = state["session_id"]
        clarifying_question = (state.get("last_input") or {}).get("text", "")
        pending_idx = max(state.get("current_q_idx", 1) - 1, 0)
        planned_question = state["question_plan"][pending_idx]["question"]

        candidate_idx = len(state.get("messages") or []) - 1
        await rest_insert(
            "transcript_turns",
            {
                "session_id": session_id,
                "idx": candidate_idx,
                "role": "candidate",
                "kind": "clarify",
                "content": clarifying_question,
            },
        )

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
                state["case_world"],
                planned_question,
                clarifying_question,
                role=role,
                improvised_facts=state.get("improvised_facts") or [],
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

        # Boundary normalisation -- see `app/text.py` for why it is here and
        # not in the agent. `improvised_fact` gets it too: it is replayed
        # into every later clarification prompt, so a raw dash there would
        # keep re-entering the model's input for the rest of the interview.
        answer_text = normalize_dashes(result.answer)
        improvised_fact = normalize_dashes(result.improvised_fact)

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
                "content": answer_text,
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

        update: dict = {
            "messages": [AIMessage(content=answer_text, additional_kwargs={"kind": "clarification"})],
        }
        if improvised_fact:
            update["improvised_facts"] = [improvised_fact]
        return update

    return answer_clarification_node


def _messages_to_turns(messages: list) -> list[dict]:
    """Converts graph state's `messages` (LangChain `AIMessage` /
    `HumanMessage` objects) into the turn shape `generate_probe` expects:
    `[{"role": "interviewer"|"candidate", "text": str}]`.

    🔴 Two mismatches live here, both silent if got wrong: `messages` holds
    LangChain message OBJECTS, not dicts, and their attribute is `.content`
    -- the DB rows this project also calls "turns" use `"content"` as a
    dict KEY, not `"text"`. `generate_probe` wants `"text"`. A converter
    that silently produced empty strings (e.g. reading the wrong attribute)
    would leave every probe responding to nothing, and -- because a probe
    reads as plausible prose either way -- nothing downstream would notice.
    Unit-tested directly in `tests/test_conduct_loop.py` for exactly that
    reason: non-empty text, and the role mapping, both pinned.

    `HumanMessage` is always the candidate (nothing else ever produces one
    in this graph); everything else (`AIMessage`, question or probe or
    clarification) is the interviewer. Order is preserved; nothing is
    filtered or windowed here -- `generate_probe`'s own
    `_windowed_transcript` does that, so this stays a pure, total format
    conversion.

    🔴 `kind` carries "clarifying_question" or "answer" through to the probe,
    added 2026-08-08. `role` is deliberately UNCHANGED: `_covered_probe_count`
    counts `role == "interviewer"` turns and would silently mis-count if the
    candidate's role string started varying, so the new information arrives as
    an ADDITIONAL key rather than a changed one. Absent on interviewer turns,
    and readers must treat a missing `kind` as "answer" -- old checkpoints
    written before this date replay without it.
    """
    return [
        {
            "role": "candidate" if isinstance(m, HumanMessage) else "interviewer",
            "text": m.content,
            **(
                {"kind": (m.additional_kwargs or {}).get("kind", "answer")}
                if isinstance(m, HumanMessage)
                else {}
            ),
        }
        for m in messages
    ]


def _make_ask_probe(
    role: Role = "fast",
) -> Callable[[InterviewState], Awaitable[dict]]:
    """Factory, same reasoning as the three above."""

    async def ask_probe(state: InterviewState) -> dict:
        """The interview's real per-turn LLM call (story 3.5.4): pushes on
        whatever the candidate just said about the ONE planned question,
        via `generate_probe`. Mirrors `ask_question`'s three side effects
        (an `agent_events` "started" row, a `transcript_turns` row, an
        `agent_events` "done" row) and its error handling matches
        `answer_clarification_node`'s -- this IS a real LLM call and CAN
        fail, unlike `ask_question`, which stopped being able to on
        2026-08-05.

        `question_plan` holds exactly one question now
        (`_QUESTIONS_THIS_PHASE = 1`), so `question_plan[0]` is read
        directly rather than indexed by `current_q_idx` -- there is no
        second question this could ever mean.

        `primary_dimension` is NOT asked of the model -- resolved in Python
        by `resolve_primary_dimension` from `result.angle_used` against the
        planned `probe_ladder`, same split as `ask_question`'s own
        dimension-coverage write and `planner.py`'s `_first_dimension`.
        Coverage is read from the FULL `messages` list (via
        `_messages_to_turns`), not the windowed transcript `generate_probe`
        itself uses internally for its token budget -- `resolve_primary_dimension`
        needs the true count of probes already asked, not the last few.

        Increments `followup_count` -- as of this story, `decide_next`'s
        PRIMARY driver, not a field with no edge to act on.
        """
        session_id = state["session_id"]
        planned = state["question_plan"][0]
        main_question = planned["question"]
        probe_ladder = planned["probe_ladder"]
        turns = _messages_to_turns(state.get("messages") or [])
        improvised_facts = state.get("improvised_facts") or []

        started = time.perf_counter()
        await rest_insert(
            "agent_events",
            {
                "session_id": session_id,
                "agent": "interviewer",
                "status": "started",
                "summary": _PROBE_STARTED_SUMMARY,
            },
        )

        # 🔴 The angle is CHOSEN HERE, in Python, before the call -- Karthik's
        # call of 2026-08-07. `dimension_coverage` had been tracked since
        # story 3.5.4 and read by nothing, so nothing steered toward what was
        # uncovered and a real interview ended with 2 of 5 rubric dimensions
        # at ZERO. See `select_probe_angle`.
        required_angle = select_probe_angle(probe_ladder, state.get("dimension_coverage"))

        try:
            result = await generate_probe(
                state["case_world"],
                improvised_facts,
                main_question,
                probe_ladder,
                turns,
                role=role,
                required_angle=required_angle,
            )
        except Exception:
            await rest_insert(
                "agent_events",
                {
                    "session_id": session_id,
                    "agent": "interviewer",
                    "status": "error",
                    "summary": _PROBE_ERROR_SUMMARY,
                },
            )
            raise

        # Boundary normalisation -- see `app/text.py`.
        probe_text = normalize_dashes(result.probe)

        duration_ms = int((time.perf_counter() - started) * 1000)

        idx = len(state.get("messages") or [])
        await rest_insert(
            "transcript_turns",
            {
                "session_id": session_id,
                "idx": idx,
                "role": "interviewer",
                # The DDL's enum name for this turn kind is "followup", not
                # "probe" (0001_initial_schema.sql:51) -- "probe" is the
                # frontend-facing label carried on the AIMessage below, kept
                # as its own separate word deliberately (see that field's
                # comment).
                "kind": "followup",
                "content": probe_text,
            },
        )
        await rest_insert(
            "agent_events",
            {
                "session_id": session_id,
                "agent": "interviewer",
                "status": "done",
                "summary": _PROBE_DONE_SUMMARY,
                "duration_ms": duration_ms,
            },
        )

        # The dimension is known BEFORE the call now, so it is taken from the
        # angle Python required rather than inferred back out of what the
        # model returned. `resolve_primary_dimension`'s positional fallback is
        # exactly what produced the skew this replaces: it inferred "covered"
        # from how many probes had been asked, never from the counter.
        #
        # `result.angle_used` is still the only evidence the model OBEYED, so
        # a mismatch is logged rather than silently accepted. It is not raised
        # on: a disobeyed angle is a worse probe, not a broken interview, and
        # failing a candidate's turn over it would be the wrong trade.
        dimension = required_angle["primary_dimension"]
        if not angles_match(result.angle_used, required_angle["angle"]):
            logger.info(
                "probe_angle_ignored required=%r returned=%r dimension=%s",
                required_angle["angle"], result.angle_used, dimension,
            )
        dimension_coverage = dict(state.get("dimension_coverage") or {})
        dimension_coverage[dimension] = dimension_coverage.get(dimension, 0) + 1

        return {
            # "kind": "probe", not "followup" -- `await_candidate` surfaces
            # this straight through `additional_kwargs` to the HTTP layer
            # (app/main.py's `next["kind"]`) so the frontend can tell a
            # probe apart from the opening question (story 3.5.5's job).
            "messages": [AIMessage(content=probe_text, additional_kwargs={"kind": "probe"})],
            "followup_count": state.get("followup_count", 0) + 1,
            "dimension_coverage": dimension_coverage,
        }

    return ask_probe


# The ONE place the exit condition lives (PHASE-3-SPEC.md 3.2's 🔴
# requirement, carried forward by PHASE-3.5-SPEC.md 3.5.4). `_QUESTIONS_THIS_PHASE`
# is now 1 (THREE DECISIONS #3: one question, probed live, not 3 pre-planned
# questions) and `_PROBES_THIS_PHASE` is the new primary boundary.
_QUESTIONS_THIS_PHASE = 1

# 🔴 CUT 8 -> 4 on 2026-08-08, Karthik's call after sitting the full eight
# live. Two reasons, one of them a measured defect rather than a preference:
#
# 1. Eight is too long for a portfolio demo nobody sits daily.
# 2. Probes 6, 7 and 8 RECYCLED probes 1, 2 and 3. Observed live: probe 6
#    reopened probe 1's compute-commitments framing verbatim ("With the
#    massive compute commitments already signed"), probe 7 reopened probe 2's
#    Google-TPU subject, probe 8 reopened the governance angle. The cause is
#    structural, not stylistic: `select_probe_angle` correctly sends the
#    ladder back for a SECOND visit to a dimension once all five are covered,
#    and `generate_probe` sees only a 4-turn window, so by probe 6 it cannot
#    see the probe it is about to repeat. Four probes never reach the second
#    visit, so the repetition cannot arise.
#
# 🔴 THE KNOWN COST: five rubric dimensions, four probes, so exactly ONE
# dimension gets zero evidence every interview -- by design now, where on
# 2026-08-07 it was two by accident. Phase 4's Evaluator MUST render that as
# `not_assessed` rather than a low score; PHASE-4-SPEC.md already requires
# `not_assessed` for this reason and it is now load-bearing, not defensive.
# Three probes was the alternative and was rejected: it leaves TWO dimensions
# blank, which is the exact 2026-08-07 defect the steering fix removed.
#
# Cost falls with it: ~47,000 `fast` tokens per interview at 8 probes
# (measured), so 4 roughly halves an interview and doubles how many fit in a
# 200,000/day budget.
_PROBES_THIS_PHASE = 4

# Safety valve, not the primary exit path: at 4 probes this almost never
# fires, but a candidate who spends a long time on clarifications should not
# turn a 45-minute interview into an unbounded one.
_TIME_BUDGET_MINUTES = 40


async def _decide_next_node(state: InterviewState) -> dict:
    """Exists because LangGraph's conditional-edge `path_map` values must
    name a real node: `route_input`'s "answer" branch needs a destination
    before `decide_next` (below)'s own outgoing conditional edge --
    registered under this SAME node name -- can read state and choose
    ask/exit.

    Story 3.5.1: this node, not `ask_question`, owns the candidate's
    ANSWER write to `transcript_turns` -- see the module banner comment's
    full reasoning for why `ask_question` cannot be the one (it never runs
    again after the final question's answer). `last_input` is guaranteed
    present here: this node's only inbound edge is `route_input`'s
    "answer" branch, reachable only after a real `await_candidate` resume,
    never on the interview's opening question. The `type == "answer"`
    check is still applied defensively, matching `route_input`'s own
    default-on-missing-type behaviour immediately upstream, rather than
    trusting that guarantee unconditionally.

    `idx = len(messages) - 1`, same reasoning as
    `answer_clarification_node`'s candidate write: `await_candidate`'s
    return already merged the candidate's HumanMessage into `messages`
    before this node runs.
    """
    last_input = state.get("last_input") or {}
    if last_input.get("type") == "answer" and last_input.get("text") is not None:
        idx = len(state.get("messages") or []) - 1
        await rest_insert(
            "transcript_turns",
            {
                "session_id": state["session_id"],
                "idx": idx,
                "role": "candidate",
                "kind": "answer",
                "content": last_input["text"],
            },
        )
    return {}


def decide_next(state: InterviewState) -> Literal["ask", "probe", "exit"]:
    """Deterministic Python, NO LLM call, no I/O -- pure enough to test
    directly against a bare dict, offline. Reads `current_q_idx`,
    `followup_count`, and elapsed time (from `started_at`) from state.

    PHASE-3.5-SPEC.md "THREE DECISIONS" #3: the interview is now ONE
    question, probed live, not 2-3 pre-planned questions asked in
    sequence -- so this function no longer decides "ask the next question
    or exit", it decides "probe again or exit", with "ask" surviving only
    as the one-time edge that asks the interview's single question at all.
    Phase 3's version of this function ASSERTED `followup_count == 0`,
    because no probe edge existed to ever write it. That assertion is
    gone -- `followup_count` is this function's PRIMARY driver now, not a
    field that should never move.

    `current_q_idx < _QUESTIONS_THIS_PHASE` (i.e. the one question has not
    been asked yet) -> "ask". In practice this fires exactly once per
    interview, on the very first call after `plan_interview` -- `ask_probe`
    never advances `current_q_idx`, so every later call to this function
    runs with `current_q_idx == 1` for the rest of the interview.

    `dimension_coverage` is no longer read here -- coverage now lives
    across the probe ladder (spec §3's rewrite) and is resolved by
    `ask_probe` calling `resolve_primary_dimension`, not gated on by this
    function, same as Phase 3's version never gated on it either.

    The exit condition lives in exactly TWO checks, both in THIS function,
    same shape as Phase 3 had: `_TIME_BUDGET_MINUTES` (the safety valve)
    and `_PROBES_THIS_PHASE` (the primary boundary, replacing
    `_QUESTIONS_THIS_PHASE`). Nothing else in the graph counts probes or
    checks elapsed time -- `ask_probe` increments `followup_count` and
    stops there.
    """
    if state.get("current_q_idx", 0) < _QUESTIONS_THIS_PHASE:
        return "ask"

    started_at = state.get("started_at")
    if started_at:
        elapsed = datetime.now(timezone.utc) - datetime.fromisoformat(started_at)
        if elapsed >= timedelta(minutes=_TIME_BUDGET_MINUTES):
            return "exit"

    if state.get("followup_count", 0) >= _PROBES_THIS_PHASE:
        return "exit"

    return "probe"


def _prior_scores(evaluations: list[dict] | None) -> list[dict]:
    """The Evaluator's RUNNING SUMMARY, built in Python from
    `state["answer_evaluations"]` -- never from the raw transcript.

    🔴 This is the whole reason per-answer scoring fits the 8,000 TPM ceiling.
    The full transcript measured 10,274 tokens at the last answer and did not
    fit (PHASE-4-SPEC.md § "WHAT THE LIVE INTERVIEW ALREADY DECIDED" #2). This
    is keyed by DIMENSION, so it is bounded at five entries however long the
    interview runs -- see the measured budget block above
    `_EVALUATION_SYSTEM_PROMPT` in `app/agents/evaluator.py`, which sizes the
    stress case against exactly this shape.

    Later evaluations overwrite earlier ones for the same dimension: a
    dimension revisited by a later probe is scored on better evidence, and the
    Evaluator is told to read this as the ARC of the interview, not as a list
    of every attempt.

    Three keys only. `reasoning` is deliberately dropped: it is the longest
    field on a `DimensionScore` and the budget block measures it at 438 tokens
    for five dimensions against 283 without, for context the model is being
    asked not to re-score.
    """
    by_dimension: dict[str, dict] = {}
    for evaluation in evaluations or []:
        for score in evaluation.get("dimension_scores") or []:
            by_dimension[score["dimension"]] = {
                "dimension": score["dimension"],
                "score": score["score"],
                "evidence_quote": score["evidence_quote"],
            }
    return list(by_dimension.values())


def _make_evaluate_answer_node(
    role: Role = "fast",
) -> Callable[[InterviewState], Awaitable[dict]]:
    """Factory, same reasoning as the others above.

    `fast` is MEASURED, not inherited from the portfolio calibration:
    `deep` 2/2 against `fast` 1/2 on the same two fixtures, and `fast` was kept
    anyway because one `deep` sample is not a measurement -- `deep` flaps and
    `fast` is deterministic. See DEV-STATE § Decisions 2026-08-09 and
    PHASE-4-SPEC.md §4.2.
    """

    async def evaluate_answer_node(state: InterviewState) -> dict:
        """Scores the answer `_decide_next_node` has just written to
        `transcript_turns`, one `answer_evaluations` row per SCORED dimension.

        🔴 ITS POSITION IN THE GRAPH IS THE DESIGN. It sits on the edge
        `decide_next -> evaluate_answer_node`, AFTER the answer's own
        transcript row and BEFORE `decide_next`'s routing conditional, so the
        FINAL answer is evaluated too. That is the same reason
        `_decide_next_node` rather than `ask_question` owns the answer write:
        the nodes that run on the way OUT of a turn never run again after the
        last one.

        🔴 AND IT IS NOT IN `await_candidate`, ever. LangGraph re-runs that
        node from the top on resume, so an LLM call there fires TWICE per
        answer and the duplicate is INVISIBLE in `answer_evaluations` -- the
        second call overwrites nothing and adds no row a reader could tell
        apart. Only `app.llm`'s call log would see it, which is where
        `tests/test_evaluate_answer.py` asserts and
        `scripts/falsify_evaluate_single_call.py` proves the assertion can
        fail. See the module docstring and CLAUDE.md.

        Guarded on `last_input`, defensively mirroring `_decide_next_node`
        immediately upstream: no answer text means no evaluation and NO LLM
        CALL, rather than scoring a clarifying question or an empty string.

        `turn_idx` is `len(messages) - 1`, the SAME index `_decide_next_node`
        used for the answer's own `transcript_turns` row. That link is the
        entire point of the column: a score in the scorecard traces back to the
        exact turn it was drawn from (0001_initial_schema.sql's own words), so
        it is computed the same way here rather than re-derived.

        🔴 A dimension in `not_assessed` gets NO ROW. Its absence IS the
        representation -- `score` is `not null check (score between 1 and 4)`
        and PHASE-4-SPEC.md §4.3 forbids weakening that for a sentinel. The
        reader joins against the five known dimensions and treats a missing row
        as not assessed.

        Returns a ONE-ELEMENT list because `answer_evaluations` carries an
        `operator.add` reducer (see `app/graph/state.py`). Returning a bare
        dict, or the full accumulated list, silently corrupts the running
        summary rather than raising. `turn_idx` rides along inside the dict so
        a later reader can tell one turn's evaluation from another's.
        """
        last_input = state.get("last_input") or {}
        if last_input.get("type") != "answer" or last_input.get("text") is None:
            return {}

        session_id = state["session_id"]
        turn_idx = len(state.get("messages") or []) - 1

        # `current_q_idx - 1`, NOT `current_q_idx`: `ask_question` increments it
        # the moment it asks, so it already points PAST the question on the
        # table. Same read as `answer_clarification_node`'s `pending_idx`.
        # `question_plan` has length 1 today (`_QUESTIONS_THIS_PHASE`), so this
        # is index 0 for the whole interview; clamped so a defensive
        # `current_q_idx` of 0 cannot wrap to the end of the list.
        pending_idx = max(state.get("current_q_idx", 1) - 1, 0)
        main_question = state["question_plan"][pending_idx]["question"]

        started = time.perf_counter()
        await rest_insert(
            "agent_events",
            {
                "session_id": session_id,
                "agent": "evaluator",
                "status": "started",
                "summary": _EVALUATE_STARTED_SUMMARY,
            },
        )

        try:
            # `followup_count > 0` is the correct opening/follow-up signal:
            # `ask_probe` is the only place that increments it, so it reads 0
            # on the opening answer and non-zero on every probe answer that
            # follows. Without this, the Evaluator was given `main_question`
            # for every answer including probes, so its decision_quality
            # "the question demanded a choice" guard fired every time and
            # scored every follow-up at the bottom of the range.
            result = await evaluate_answer(
                state["case_world"],
                main_question,
                last_input["text"],
                state["assessed_level"],
                _prior_scores(state.get("answer_evaluations")),
                role=role,
                is_followup=state.get("followup_count", 0) > 0,
            )
        except Exception:
            await rest_insert(
                "agent_events",
                {
                    "session_id": session_id,
                    "agent": "evaluator",
                    "status": "error",
                    "summary": _EVALUATE_ERROR_SUMMARY,
                },
            )
            raise

        duration_ms = int((time.perf_counter() - started) * 1000)

        # Boundary normalisation -- see `app/text.py`. `reasoning` is prose the
        # candidate reads on the scorecard, so it is cleaned on the way to the
        # database; `evidence_quote` is NOT, and must never be. It is checked
        # against the transcript byte for byte, and the transcript row
        # `_decide_next_node` wrote holds the candidate's text unnormalised --
        # normalising one side of that comparison and not the other would turn
        # a faithful quote into a mismatch.
        scores = [
            {
                "dimension": score.dimension,
                "score": score.score,
                "evidence_quote": score.evidence_quote,
                "reasoning": normalize_dashes(score.reasoning),
            }
            for score in result.dimension_scores
        ]

        for score in scores:
            await rest_insert("answer_evaluations", {"session_id": session_id, "turn_idx": turn_idx, **score})

        await rest_insert(
            "agent_events",
            {
                "session_id": session_id,
                "agent": "evaluator",
                "status": "done",
                "summary": _EVALUATE_DONE_SUMMARY,
                "duration_ms": duration_ms,
            },
        )

        return {
            "answer_evaluations": [
                {
                    "turn_idx": turn_idx,
                    "dimension_scores": scores,
                    "framework_narration": result.framework_narration,
                    # Kept in state though it has no column, deliberately: it
                    # is per-ANSWER and this table's grain is
                    # (turn_idx, dimension). See 0004's own comment.
                    "not_assessed": list(result.not_assessed),
                }
            ]
        }

    return evaluate_answer_node


def build_graph(
    checkpointer: BaseCheckpointSaver,
    *,
    resume_analyst_role: Role = "deep",
    case_architect_role: Role = "fast",
    planner_role: Role = "deep",
    interviewer_role: Role = "fast",
    evaluator_role: Role = "fast",
) -> Any:
    """Compiles level_candidate -> confirm_level -> generate_case_world ->
    plan_interview -> ask_question -> await_candidate -> ... -> END (the
    conduct loop, story 3.2, extended with the probe edge by story 3.5.4)
    with the given checkpointer attached.

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

    `evaluator_role` defaults to `fast`, and that default is MEASURED rather
    than inherited from the portfolio calibration: `deep` scored 2/2 against
    `fast`'s 1/2 on the same two fixtures with identical input, and `fast` was
    kept anyway -- one `deep` sample is not a measurement, `deep` flaps where
    `fast` is deterministic, and the single disagreement was a rubric
    definition question rather than a capability gap. See DEV-STATE § Decisions
    2026-08-09 and PHASE-4-SPEC.md §4.2.
    """
    graph = StateGraph(InterviewState)
    graph.add_node("level_candidate", _make_level_candidate(resume_analyst_role))
    graph.add_node("confirm_level", confirm_level)
    graph.add_node("generate_case_world", _make_generate_case_world(case_architect_role))
    graph.add_node("plan_interview", _make_plan_interview(planner_role))
    graph.add_node("ask_question", _make_ask_question(interviewer_role))
    graph.add_node("ask_probe", _make_ask_probe(interviewer_role))
    graph.add_node("await_candidate", await_candidate)
    graph.add_node("answer_clarification_node", _make_answer_clarification_node(interviewer_role))
    graph.add_node("decide_next", _decide_next_node)
    graph.add_node("evaluate_answer_node", _make_evaluate_answer_node(evaluator_role))
    graph.set_entry_point("level_candidate")
    graph.add_edge("level_candidate", "confirm_level")
    graph.add_edge("confirm_level", "generate_case_world")
    graph.add_edge("generate_case_world", "plan_interview")
    graph.add_edge("plan_interview", "ask_question")
    graph.add_edge("ask_question", "await_candidate")
    graph.add_edge("ask_probe", "await_candidate")
    graph.add_conditional_edges(
        "await_candidate",
        route_input,
        {"clarify": "answer_clarification_node", "answer": "decide_next"},
    )
    graph.add_edge("answer_clarification_node", "await_candidate")
    # 🔴 The evaluator sits BETWEEN `_decide_next_node` (which writes the
    # answer's `transcript_turns` row) and `decide_next`'s routing conditional,
    # not after it. Routing is where the interview ENDS, so an evaluator hung
    # off the "probe" branch would never see the final answer -- the same
    # reason `_decide_next_node` and not `ask_question` owns the answer write.
    # Do not fold it into `_decide_next_node`, and never into `await_candidate`.
    graph.add_edge("decide_next", "evaluate_answer_node")
    graph.add_conditional_edges(
        "evaluate_answer_node",
        decide_next,
        {"ask": "ask_question", "probe": "ask_probe", "exit": END},
    )
    return graph.compile(checkpointer=checkpointer)
