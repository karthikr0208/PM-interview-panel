"""Does story 4.3's single-call assertion actually GATE?

    backend/.venv/Scripts/python.exe backend/scripts/falsify_evaluate_single_call.py

Takes no arguments. Costs ~2 `fast` calls. Exit 0 = the assertion can detect
the bug; exit 2 = it is VACUOUS and story 4.3 is not done.

Same treatment `falsify_single_call.py` gives story 1.4's assertion, and for
the same reason: a call-counter that cannot fail is not a measurement. This one
exists SEPARATELY because the Evaluator's duplicate is worse than the Resume
Analyst's. A second `evaluate_answer` call writes the same (session_id,
turn_idx, dimension) rows a second time, so `answer_evaluations` still reads as
one evaluation per turn to anyone querying it -- the duplicate is invisible in
the table the story exists to fill. Only `app.llm`'s call log sees it.

Builds the WRONG graph -- the evaluator call placed ABOVE `interrupt()` in the
same node, which is the exact bug CLAUDE.md's load-bearing rule exists to
prevent -- drives one start/resume cycle for a single answer, and applies
test_evaluate_answer.py's own `outcome=ok` counting logic to it.

EXPECTED: the wrong graph logs 2 `outcome=ok` records for ONE answer, so the
assertion that demands exactly 1 goes RED. If it logs 1, the assertion cannot
detect the bug it exists to detect.

Runs on `fast` with a deliberately tiny case world and a short answer: the
property under test is model-independent graph mechanics, and the daily token
budget is not its to spend.
"""
from __future__ import annotations

import asyncio
import logging
import sys
import uuid
from pathlib import Path

import psycopg

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.agents.evaluator import evaluate_answer  # noqa: E402
from app.config import settings  # noqa: E402
from app.graph.state import InterviewState  # noqa: E402
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # noqa: E402
from langgraph.graph import END, StateGraph  # noqa: E402
from langgraph.types import Command, interrupt  # noqa: E402

# Small on purpose. The budget block in app/agents/evaluator.py measures the
# system prompt at 936 tokens and the largest real world at 1,392; this world
# keeps the two calls below comfortably inside one minute's 8,000 TPM.
CASE_WORLD = {
    "company": {"name": "Palewell Analytics", "one_line": "usage analytics for mid-market SaaS"},
    "situation": {
        "prompt": "Should Palewell Analytics build a native mobile dashboard this quarter?",
        "tension": "Mobile usage is rising but engineering capacity is fixed.",
        "options": ["Build mobile now", "Ship a mobile web view", "Defer to next quarter"],
    },
    "metrics": {"arr_usd": "$6.4M", "customer_count": 340, "monthly_churn_pct": 4.6},
}
QUESTION = "What is Palewell Analytics' biggest threat over the next three years?"
ANSWER = (
    "I would ship the mobile web view first. Churn at 4.6% is the number I care about, "
    "and a web view reaches every one of the 340 customers this quarter without new headcount."
)
LEVEL = "PM"

# ~21s, the same spacing `tests/test_conduct_loop.py::_paced` uses. Two
# evaluator requests back to back measure roughly 3,500 tokens each against an
# 8,000 TPM ceiling; a 429 on the second call would waste the first one and
# report nothing about the property under test.
_SECONDS_BETWEEN_CALLS = 21.0


class _Counter(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def ok_calls(self) -> list[str]:
        # Copied verbatim in spirit from tests/test_evaluate_answer.py::_ok_llm_calls
        return [
            r.getMessage()
            for r in self.records
            if r.name == "app.llm"
            and r.getMessage().startswith("llm_call")
            and "outcome=ok" in r.getMessage()
        ]


async def broken_node(state: InterviewState) -> dict:
    """THE BUG, on purpose: the evaluator call above interrupt() in the same
    node. This is what `evaluate_answer_node` would be if it were folded into
    `await_candidate` instead of sitting on its own edge after `decide_next`."""
    evaluation = await evaluate_answer(
        state["case_world"], QUESTION, ANSWER, state["assessed_level"], [], role="fast"
    )
    value = interrupt({"scored": [s.dimension for s in evaluation.dimension_scores]})
    return {"last_input": value}


async def main() -> int:
    session_id = str(uuid.uuid4())
    conn = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
    try:
        with conn.cursor() as cur:
            cur.execute("insert into sessions (id, status) values (%s, 'created')", (session_id,))
        conn.commit()
    finally:
        conn.close()

    handler = _Counter()
    logging.getLogger("app.llm").addHandler(handler)
    logging.getLogger("app.llm").setLevel(logging.INFO)

    rc = 1
    try:
        async with AsyncPostgresSaver.from_conn_string(settings.supabase_db_url) as cp:
            g = StateGraph(InterviewState)
            g.add_node("broken", broken_node)
            g.set_entry_point("broken")
            g.add_edge("broken", END)
            graph = g.compile(checkpointer=cp)

            cfg = {"configurable": {"thread_id": session_id}}
            await graph.ainvoke(
                {"session_id": session_id, "case_world": CASE_WORLD, "assessed_level": LEVEL}, cfg
            )
            at_pause = len(handler.ok_calls())

            await asyncio.sleep(_SECONDS_BETWEEN_CALLS)
            await graph.ainvoke(Command(resume={"type": "answer", "text": ANSWER}), cfg)
            after = len(handler.ok_calls())

        print(f"\nWRONG graph (evaluator call above interrupt, same node), ONE answer")
        print(f"  outcome=ok records at pause       : {at_pause}")
        print(f"  outcome=ok records after resume   : {after}")
        print(f"\n  assertion 'exactly 1 per answer' -> "
              f"{'PASSES (VACUOUS - CANNOT DETECT THE BUG)' if after == 1 else 'FAILS as it must'}")
        if after == 1:
            print("\n  🔴 The wrong graph scored this answer only ONCE. The single-call")
            print("     assertion in tests/test_evaluate_answer.py proves nothing, and a")
            print("     duplicate evaluator call would still be invisible in")
            print("     answer_evaluations. Story 4.3 is not done.")
        rc = 0 if after != 1 else 2
    finally:
        conn = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
        try:
            with conn.cursor() as cur:
                for t in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
                    cur.execute(f"delete from {t} where thread_id = %s", (session_id,))
                # answer_evaluations cascades off sessions, and the broken node
                # writes none of its own -- `evaluate_answer` is a pure
                # function. Counted below rather than assumed.
                cur.execute("delete from sessions where id = %s", (session_id,))
            conn.commit()
            with conn.cursor() as cur:
                cur.execute("select count(*) from sessions where id = %s", (session_id,))
                sessions_left = cur.fetchone()[0]
                cur.execute(
                    "select count(*) from answer_evaluations where session_id = %s", (session_id,)
                )
                evaluations_left = cur.fetchone()[0]
                print(f"\n  residue: sessions rows = {sessions_left}, "
                      f"answer_evaluations rows = {evaluations_left}")
        finally:
            conn.close()
    return rc


if __name__ == "__main__":
    # psycopg async cannot run on Windows' default ProactorEventLoop.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    sys.exit(asyncio.run(main()))
