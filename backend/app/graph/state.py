"""The shared graph state. Transcribed exactly from ARCHITECTURE.md §4 (lines
179-206) — do not add fields here speculatively; every field belongs to a
named agent's contract in `docs/specs/agents/`.

There is no orchestrator agent. Routing is plain Python reading this state;
agents read state, return partial updates, and LangGraph merges and persists
the result. See ARCHITECTURE.md §3.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class InterviewState(TypedDict):
    session_id: str

    # ── Resume Analyst ─────────────────────────────────────
    resume_text: str
    candidate_profile: dict
    assessed_level: str  # APM | PM | Senior PM | GPM
    level_rationale: str
    low_confidence_fields: list[str]

    # ── Case Architect — written once, read-only after ─────
    case_world: dict

    # ── Planner ────────────────────────────────────────────
    question_plan: list[dict]

    # ── Conduct loop ───────────────────────────────────────
    messages: Annotated[list, add_messages]
    current_q_idx: int
    followup_count: int
    dimension_coverage: dict[str, int]
    started_at: str
    # The most recently resumed `await_candidate` payload, {"type":
    # "answer"|"clarify", "text": str} -- written ONLY by await_candidate's
    # return (its interrupt() value, unmodified), per AGENT-INTERVIEWER-SPEC
    # and PHASE-3-SPEC.md 3.2's own suggested shape. route_input reads
    # ["type"] to pick a branch; answer_clarification_node and ask_question
    # read ["text"] (the clarifying question, or the previous answer for the
    # bridge) -- neither re-derives it from `messages`, which stays the
    # durable transcript rather than a second data source to keep in sync.
    last_input: dict

    # ── Interviewer -- invented facts, PHASE-3.5-SPEC.md "THREE DECISIONS" #2 ─
    # Every fact `answer_clarification` INVENTS (case_world is silent, so
    # can_answer=False) lands here, verbatim, so a LATER clarification or
    # probe can repeat it exactly instead of re-inventing a different value.
    # `operator.add`, same reasoning as `answer_evaluations` below: without
    # this reducer the field would silently hold only the most recent
    # invented fact, no exception -- the whole invent-and-record design
    # (the damage was never the invention, it was a value changing between
    # minute 8 and minute 30) fails silently at minute 30. See ARCHITECTURE
    # §4 "The trap". `case_world` itself stays untouched and immutable --
    # this is a separate, append-only channel, never merged back into it.
    improvised_facts: Annotated[list[str], operator.add]

    # ── Evaluator / Coach ────────────────────────────────────
    # operator.add concatenates each evaluate_answer's one-element return list.
    # Without this reducer, answer_evaluations would silently hold only the
    # most recent evaluation — no exception, just a scorecard built from one
    # answer. See ARCHITECTURE.md §4 "The trap".
    answer_evaluations: Annotated[list[dict], operator.add]
    scorecard: dict | None
    coach_report: dict | None
