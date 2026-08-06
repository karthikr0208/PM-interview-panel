"""Story 3.5.1: the transcript holds candidate turns, not just the
Interviewer's own.

Before this story, only `ask_question`'s question and
`answer_clarification_node`'s answer wrote a `transcript_turns` row -- a
finished interview stored 3 questions + 1 clarification and ZERO candidate
answers. `0001_initial_schema.sql` already declared `role` as `interviewer |
candidate | system` and `kind` as `question | followup | answer | clarify |
meta`, so this was a missing write, not a missing column, and needs no
migration.

🔴 Story 3.5.4 reshaped the loop this file drives, from 2-3 pre-planned
questions asked in sequence to ONE question probed live
(`_QUESTIONS_THIS_PHASE = 1`, `_PROBES_THIS_PHASE = 8`):
`ask_question -> await_candidate -> route_input ->
{answer_clarification_node, decide_next} -> {ask_question, ask_probe,
exit}`. `question_plan`'s single entry now carries a `probe_ladder` (a list
of `{"angle", "primary_dimension"}` dicts), not the old `probe_angles`, and
`decide_next` returns `"ask" | "probe" | "exit"` through the new `ask_probe`
node between `decide_next` and `await_candidate`. The fixtures and resume
sequences below were rewritten to that shape; the transcript PROPERTIES
under test did not change and are still the point of this file.

🔴 Deviation from the brief that spawned this story, recorded here because
the test below (`test_the_final_answer_gets_a_row_even_though_ask_probe_
never_runs_again`) is the evidence for it: the brief proposed writing the
candidate's ANSWER in `ask_question`. That is wrong. `route_input`'s "answer"
edge lands on `_decide_next_node` first, not `ask_question` or `ask_probe`
-- and on the FINAL answer, `decide_next()` returns "exit" straight to END
without ever calling `ask_probe` again (`test_conduct_loop.py`'s own
`test_the_loop_asks_the_one_question_then_probes_and_exits_at_the_probe_count_boundary`
already proves this shape). Writing the candidate's last answer in
`ask_question` or `ask_probe` would silently drop it. `_decide_next_node` is
the correct place: it is the node that runs immediately after EVERY
"answer" resume, whether the loop is about to probe again or exit. See
`app/graph/build.py`'s module banner comment and `_decide_next_node`'s own
docstring for the full reasoning.

Live tests only (this file has no offline half) -- every assertion needs the
real Postgres-backed transcript_turns table and the real graph. Same
graph-level fixture shape as `test_conduct_loop.py`'s `loop_sessions`,
copied rather than imported per that file's own precedent of not sharing
test-only fixtures across modules.

🔴 Per story 3.5.4: every resume below that lands on "probe" (not "exit")
now costs a real `fast` `generate_probe` LLM call, unlike the old
`ask_question`, which was fully deterministic. This file was already
`pytest.mark.live`-only before this story, so that cost is not new in kind,
only in where it is spent.
"""

from __future__ import annotations

import uuid
from typing import Callable, Iterator

import httpx
import psycopg
import pytest
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command

from app.config import settings
from app.graph.build import build_graph
from app.supabase_client import rest_insert

pytestmark = pytest.mark.live

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

# 🔴 ONE question now (THREE DECISIONS #3), carrying a `probe_ladder` --
# `question_plan` stays "a list of dicts", but the list always has length 1
# as of story 3.5.3/3.5.4. Ladder shape and angle wording matched to
# `test_conduct_loop.py`'s `QUESTION_PLAN` fixture rather than invented
# fresh, per that file's convention.
QUESTION_PLAN = [
    {
        "idx": 0,
        "question": "Given Palewell Analytics' 4.6% monthly churn, how would you prioritize the mobile dashboard decision?",
        "intent": "surfaces prioritization under a fixed constraint",
        "primary_dimension": "decision_quality",
        "probe_ladder": [
            {"angle": "What tradeoff would you make first?", "primary_dimension": "decision_quality"},
            {"angle": "What signal would change your mind?", "primary_dimension": "structural_clarity"},
            {"angle": "What would falsify leadership's belief?", "primary_dimension": "point_of_view"},
            {"angle": "How does Palewell Analytics actually make money today?", "primary_dimension": "business_model_fluency"},
            {"angle": "What is the biggest risk to the churn number specifically?", "primary_dimension": "market_accuracy"},
            {"angle": "How would you sequence this against the fixed headcount constraint?", "primary_dimension": "decision_quality"},
        ],
        "grounded_in": ["Monthly churn is 4.6%, the highest of any month since launch."],
        "minutes": 40,
    },
]

LEVEL = "PM"


def _config(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}


def _initial_state(session_id: str) -> dict:
    return {
        "session_id": session_id,
        "case_world": CASE_WORLD,
        "question_plan": QUESTION_PLAN,
        "assessed_level": LEVEL,
    }


async def _start_at_the_loop(graph, config: dict, session_id: str) -> dict:
    """Copied from `test_conduct_loop.py`'s helper of the same name -- see
    its docstring for why seeding the checkpoint `as_node="plan_interview"`
    is the right shape rather than merely a working one."""
    await graph.aupdate_state(config, _initial_state(session_id), as_node="plan_interview")
    return await graph.ainvoke(None, config)


@pytest.fixture
def loop_sessions() -> Iterator[Callable[[], str]]:
    """Copied from `test_conduct_loop.py`'s fixture of the same name.
    `transcript_turns` rows cascade on `sessions` delete
    (`0001_initial_schema.sql`'s `on delete cascade`), so no separate
    cleanup for that table is needed."""
    created: list[str] = []

    def make() -> str:
        session_id = str(uuid.uuid4())
        conn = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "insert into sessions (id, status) values (%s, 'created')", (session_id,)
                )
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


def _transcript_rows(session_id: str) -> list[tuple[int, str, str, str]]:
    """(idx, role, kind, content), ordered by idx -- a plain connection, not
    the checkpointer's dict_row factory, matching `conftest.py`'s `conn`
    fixture (not used directly here since this file's assertions run after
    the live graph calls, and a fresh connection avoids any read-transaction
    visibility question `test_confirm_level.py`'s `conn.rollback()` comment
    flags for the shared fixture)."""
    conn = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "select idx, role, kind, content from transcript_turns "
                "where session_id = %s order by idx",
                (session_id,),
            )
            return cur.fetchall()
    finally:
        conn.close()


async def test_candidate_answer_writes_a_transcript_row(
    checkpointer: AsyncPostgresSaver, loop_sessions: Callable[[], str]
) -> None:
    """Acceptance box 1: a candidate answer produces a row with
    role='candidate', kind='answer', and the exact text the candidate sent."""
    session_id = loop_sessions()
    graph = build_graph(checkpointer, interviewer_role="fast")
    config = _config(session_id)

    await _start_at_the_loop(graph, config, session_id)
    answer_text = "I'd ship the web view first, then measure engagement before building native."
    await graph.ainvoke(Command(resume={"type": "answer", "text": answer_text}), config)

    rows = _transcript_rows(session_id)
    candidate_rows = [r for r in rows if r[1] == "candidate"]
    assert len(candidate_rows) == 1, f"expected exactly one candidate row, got {candidate_rows}"
    idx, role, kind, content = candidate_rows[0]
    assert role == "candidate"
    assert kind == "answer"
    assert content == answer_text


async def test_candidate_clarifying_question_writes_a_transcript_row(
    checkpointer: AsyncPostgresSaver, loop_sessions: Callable[[], str]
) -> None:
    """Acceptance box 2: a candidate clarifying question produces a row with
    role='candidate', kind='clarify'."""
    session_id = loop_sessions()
    graph = build_graph(checkpointer, interviewer_role="fast")
    config = _config(session_id)

    await _start_at_the_loop(graph, config, session_id)
    clarify_text = "How big is Palewell's customer base?"
    await graph.ainvoke(Command(resume={"type": "clarify", "text": clarify_text}), config)

    rows = _transcript_rows(session_id)
    candidate_rows = [r for r in rows if r[1] == "candidate"]
    assert len(candidate_rows) == 1, f"expected exactly one candidate row, got {candidate_rows}"
    idx, role, kind, content = candidate_rows[0]
    assert role == "candidate"
    assert kind == "clarify"
    assert content == clarify_text


async def test_question_one_has_no_preceding_candidate_row(
    checkpointer: AsyncPostgresSaver, loop_sessions: Callable[[], str]
) -> None:
    """Acceptance box 3: question 1 produces NO candidate row -- nothing
    preceded it. Pins the guard in both `_decide_next_node` and the
    `ask_question`-was-never-the-write-site conclusion: at the moment the
    graph first pauses, the ONLY row in `transcript_turns` is the
    Interviewer's own opening question."""
    session_id = loop_sessions()
    graph = build_graph(checkpointer, interviewer_role="fast")
    config = _config(session_id)

    await _start_at_the_loop(graph, config, session_id)

    rows = _transcript_rows(session_id)
    assert len(rows) == 1, f"expected exactly one row after question 1, got {rows}"
    idx, role, kind, content = rows[0]
    assert idx == 0
    assert role == "interviewer"
    assert kind == "question"
    assert content == QUESTION_PLAN[0]["question"]


async def test_the_final_answer_gets_a_row_even_though_ask_probe_never_runs_again(
    checkpointer: AsyncPostgresSaver,
    loop_sessions: Callable[[], str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The specific case that falsifies the brief's original proposal
    (write the candidate answer inside `ask_question`, or now `ask_probe`).
    After the LAST probe's answer, `decide_next()` returns "exit" straight to
    END -- `ask_probe` never runs again, so if the candidate write lived
    there, this exact answer would never get a row. It must, because
    `_decide_next_node` (not `ask_question` or `ask_probe`) owns the write and
    runs on every "answer" resume including the last one.

    🔴 `_PROBES_THIS_PHASE` is patched to 2, and that is a budget decision
    with a reason, not a shortcut. The property under test is the BOUNDARY --
    what happens on the resume after the final probe -- and a boundary is a
    boundary at 2 as much as at 8. Production's 8 costs 8 `fast` calls per
    run of this test, each carrying a growing transcript, which is most of a
    whole interview's ~47,000 tokens spent on an assertion that does not
    depend on the count. Patching the constant (rather than hardcoding a
    smaller number here) keeps the exit condition living in exactly ONE
    place, which is PHASE-3-SPEC 3.2's requirement.
    """
    probes = 2
    monkeypatch.setattr("app.graph.build._PROBES_THIS_PHASE", probes)
    session_id = loop_sessions()
    graph = build_graph(checkpointer, interviewer_role="fast")
    config = _config(session_id)

    await _start_at_the_loop(graph, config, session_id)
    for probe_number in range(1, probes + 1):
        await graph.ainvoke(
            Command(resume={"type": "answer", "text": f"Answer number {probe_number}."}), config
        )
    final_answer = "I'd track renewal rate as the falsifying signal."
    final = await graph.ainvoke(Command(resume={"type": "answer", "text": final_answer}), config)

    assert "__interrupt__" not in final, "the loop should have exited at the probe count boundary"

    rows = _transcript_rows(session_id)
    last_row = rows[-1]
    idx, role, kind, content = last_row
    assert role == "candidate", f"the final answer never got a row: last row was {last_row}"
    assert kind == "answer"
    assert content == final_answer


async def test_full_interview_transcript_alternates_with_no_gaps_in_idx(
    checkpointer: AsyncPostgresSaver,
    loop_sessions: Callable[[], str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Acceptance box 4: turns alternate interviewer/candidate, and `idx`
    has no gaps, across a finished one-question interview (no clarifications
    in this run -- `test_candidate_clarifying_question_writes_a_transcript_row`
    covers that kind separately).

    `_PROBES_THIS_PHASE` patched to 2 for the budget reason given in the test
    above: alternation and idx contiguity are properties of the WRITE ORDER,
    which does not vary with how many probes are asked."""
    probes = 2
    monkeypatch.setattr("app.graph.build._PROBES_THIS_PHASE", probes)
    session_id = loop_sessions()
    graph = build_graph(checkpointer, interviewer_role="fast")
    config = _config(session_id)

    await _start_at_the_loop(graph, config, session_id)
    for probe_number in range(1, probes + 1):
        await graph.ainvoke(
            Command(resume={"type": "answer", "text": f"Answer number {probe_number}."}), config
        )
    final = await graph.ainvoke(Command(resume={"type": "answer", "text": "I'd track renewal rate."}), config)
    assert "__interrupt__" not in final

    rows = _transcript_rows(session_id)
    idxs = [r[0] for r in rows]
    assert idxs == list(range(len(rows))), f"idx has a gap or duplicate: {idxs}"

    roles = [r[1] for r in rows]
    assert roles == ["interviewer", "candidate"] * (len(roles) // 2), (
        f"transcript did not alternate interviewer/candidate: {roles}"
    )
    # 1 question + `probes` probes interviewer rows; `probes` probe answers
    # plus 1 final answer candidate rows. Derived from the patched constant
    # rather than hardcoded, so this stays honest if the probe count moves.
    expected = (1 + probes) + (probes + 1)
    assert len(rows) == expected, (
        f"expected 1 question + {probes} probes + {probes + 1} answers = {expected} rows, "
        f"got {len(rows)}: {rows}"
    )


async def test_a_replayed_candidate_write_conflicts_rather_than_duplicates(
    loop_sessions: Callable[[], str],
) -> None:
    """Acceptance box 5 / the 409 question, resolved by direct observation
    rather than by trusting the brief's reasoning.

    Neither `_decide_next_node` nor `answer_clarification_node` contains an
    `interrupt()` -- LangGraph's "re-run the whole node from the top on
    resume" rule applies only to INTERRUPTING nodes (`await_candidate`,
    `confirm_level`). These two are plain downstream nodes: within one
    `graph.ainvoke(Command(resume=...))` call they each run exactly once,
    which `test_conduct_loop.py`'s
    `test_await_candidate_does_not_redo_the_clarification_call_when_the_real_answer_resumes`
    already demonstrates for `answer_clarification_node`'s LLM call (fires
    exactly once across a resume cycle that touches `await_candidate`
    twice), and this file's own tests above never see a duplicate row
    across a full 3-question interview.

    The genuine risk named in the brief is a true REPLAY at the HTTP layer
    -- a client retrying `/session/{id}/interview/reply` after a request
    that actually succeeded server-side, landing the same write twice. That
    is not reachable through the graph's normal resume mechanics (the
    second attempt would resume a DIFFERENT, later interrupt, not re-fire
    the same write at the same idx) except under genuine concurrent
    duplicate submission. Rather than fabricate that race, this test proves
    the actual safety net directly: two inserts at the same `(session_id,
    idx)` -- exactly what a duplicated candidate-answer write would attempt
    -- and confirms the SECOND one raises (`unique (session_id, idx)`),
    never silently duplicates. `rest_insert`'s `resp.raise_for_status()`
    is what turns that unique violation into a raised
    `httpx.HTTPStatusError` (Postgres reports 23505; PostgREST surfaces
    that as 409) rather than a silent no-op -- so a replayed resume
    conflicts loudly, which is what the acceptance box asks for. No
    idempotent-insert fallback (`Prefer: resolution=ignore-duplicates`) was
    added, because the acceptance box wants a CONFLICT here, not a
    silently-ignored duplicate.
    """
    session_id = loop_sessions()
    payload = {
        "session_id": session_id,
        "idx": 0,
        "role": "candidate",
        "kind": "answer",
        "content": "first write",
    }

    first = await rest_insert("transcript_turns", payload)
    assert first["idx"] == 0

    with pytest.raises(httpx.HTTPStatusError) as excinfo:
        await rest_insert("transcript_turns", {**payload, "content": "replayed write"})

    assert excinfo.value.response.status_code == 409, (
        f"expected a 409 conflict from the unique(session_id, idx) constraint, "
        f"got {excinfo.value.response.status_code}: {excinfo.value.response.text}"
    )
