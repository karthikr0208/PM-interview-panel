"""Does story 3.2's LOOPING single-call assertion actually GATE?

    backend/.venv/Scripts/python.exe backend/scripts/falsify_looping_interrupt.py

Takes no arguments. Costs a few `fast` calls. Exit 0 = the assertion can
detect the bug; exit 2 = it is VACUOUS and story 3.2 is not done.


`falsify_single_call.py` (story 1.4) proves the single-call guarantee can
fail for ONE interrupt. That is not the same proof for a LOOPING one --
PHASE-3-SPEC.md 3.2 says so explicitly: "a loop that re-runs ask_question on
resume looks correct from state -- the transcript still reads sensibly. Only
the call log shows the duplicate." This script is that sibling.

Builds the WRONG graph -- `answer_clarification` (since 2026-08-05 the ONLY
LLM call anywhere in the conduct loop, because `ask_question` became fully
deterministic when the bridge was deleted) placed ABOVE `interrupt()`, in
the SAME node, INSIDE a two-turn loop -- drives two full turns, and confirms
the wrong graph logs MORE `outcome=ok` records than a correctly-built loop
would for the same number of turns.

Reasoning for "correctly built": a correct loop calls `answer_clarification`
exactly once per clarification and does NOT repeat that call when
`await_candidate` is resumed with the real answer -- so N clarifications
cost exactly N calls. The broken graph calls it on EVERY pass through its
single merged node, including the pass LangGraph re-runs on each resume, so
N turns cost 2N calls.

🔴 THE CORRECT SIDE IS NOT ASSERTED HERE, AND THAT IS THE POINT OF THE
PAIRING. This script only ever runs the WRONG graph, so "a correct loop logs
2" is reasoned, not observed. The observation lives in
`tests/test_conduct_loop.py::test_await_candidate_does_not_redo_the_clarification_call_when_the_real_answer_resumes`,
which drives the REAL graph and pins the count. **Neither half is a proof on
its own** -- and on 2026-08-05 the test half was found dead (it had never
run, and died on `KeyError: 'resume_text'`), leaving this script looking
like a complete proof when it was not. Run both.

EXPECTED for `_TURNS = 2`: correct = 2, wrong = 4. If the wrong graph's
final count equals 2 (the correct count), the assertion this script exists
to falsify cannot tell a duplicated call from a clean one, and exits 2.

Runs on `fast`, same reasoning as `falsify_single_call.py`: the property
under test is graph mechanics, model-independent, and `deep`'s daily budget
is not this script's to spend.
"""
from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from pathlib import Path
from typing import TypedDict

import psycopg

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.agents.interviewer import answer_clarification  # noqa: E402
from app.config import settings  # noqa: E402
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # noqa: E402
from langgraph.graph import END, StateGraph  # noqa: E402
from langgraph.types import Command, interrupt  # noqa: E402

_TURNS = 2

# Minimal, hand-written, and deliberately tiny: this script measures graph
# mechanics, not answer quality, so the world only has to be non-empty
# enough for `answer_clarification` to accept it.
_WORLD = {
    "company": {"name": "Palewell Analytics"},
    "metrics": {"customer_count": 340, "monthly_churn_pct": 4.6},
    "supporting_facts": ["340 paying customers as of this quarter."],
}


class _LoopState(TypedDict, total=False):
    q_idx: int
    last_answer: str


class _Counter(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def ok_calls(self) -> list[str]:
        # Copied verbatim in spirit from tests/test_confirm_level.py::_ok_llm_calls
        # and falsify_single_call.py's identical helper.
        return [
            r.getMessage()
            for r in self.records
            if r.name == "app.llm"
            and r.getMessage().startswith("llm_call")
            and "outcome=ok" in r.getMessage()
        ]


async def broken_loop_node(state: _LoopState) -> dict:
    """THE BUG, on purpose: `answer_clarification` (a real per-turn LLM
    call) placed ABOVE `interrupt()`, in the SAME node, inside a loop -- the
    exact shape CLAUDE.md's load-bearing rule exists to prevent, and the
    exact shape a merged `answer_clarification_node`/`await_candidate` would
    take if someone "simplified" the real graph by folding them into one
    node."""
    q_idx = state.get("q_idx", 0)
    await answer_clarification(
        _WORLD,
        "How would you prioritize the mobile dashboard decision?",
        "How many customers does Palewell Analytics have?",
        role="fast",
    )
    answer = interrupt({"q_idx": q_idx})
    return {"q_idx": q_idx + 1, "last_answer": answer}


def decide(state: _LoopState) -> str:
    return "ask" if state.get("q_idx", 0) < _TURNS else "exit"


async def main() -> int:
    thread_id = str(uuid.uuid4())

    handler = _Counter()
    logging.getLogger("app.llm").addHandler(handler)
    logging.getLogger("app.llm").setLevel(logging.INFO)

    rc = 1
    async with AsyncPostgresSaver.from_conn_string(settings.supabase_db_url) as cp:
        g = StateGraph(_LoopState)
        g.add_node("ask", broken_loop_node)
        g.set_entry_point("ask")
        g.add_conditional_edges("ask", decide, {"ask": "ask", "exit": END})
        graph = g.compile(checkpointer=cp)

        cfg = {"configurable": {"thread_id": thread_id}}

        await graph.ainvoke({}, cfg)
        after_q1 = len(handler.ok_calls())

        await graph.ainvoke(Command(resume="answer to question 0"), cfg)
        after_q2 = len(handler.ok_calls())

        await graph.ainvoke(Command(resume="answer to question 1"), cfg)
        final = len(handler.ok_calls())

    expected_correct = _TURNS  # one clarification call per turn, never repeated on resume

    print("\nWRONG graph (answer_clarification above interrupt, inside a 2-turn loop)")
    print(f"  outcome=ok records after turn 1's pause        : {after_q1}")
    print(f"  outcome=ok records after turn 1's resume+pause : {after_q2}")
    print(f"  outcome=ok records after turn 2's resume+exit  : {final}")
    print(f"\n  a correctly-built {_TURNS}-turn loop would log exactly {expected_correct}")
    print(
        f"  assertion 'exactly {expected_correct} across the loop' -> "
        + ("PASSES (VACUOUS -- CANNOT DETECT THE BUG)" if final == expected_correct else "FAILS as it must")
    )
    rc = 0 if final != expected_correct else 2

    conn = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
    try:
        with conn.cursor() as cur:
            for t in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
                cur.execute(f"delete from {t} where thread_id = %s", (thread_id,))
        conn.commit()
        with conn.cursor() as cur:
            cur.execute("select count(*) from checkpoints where thread_id = %s", (thread_id,))
            print(f"\n  residue: checkpoints rows for this thread = {cur.fetchone()[0]}")
    finally:
        conn.close()

    return rc


if __name__ == "__main__":
    # psycopg async cannot run on Windows' default ProactorEventLoop.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    sys.exit(asyncio.run(main()))
