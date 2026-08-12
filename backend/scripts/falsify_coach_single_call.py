"""Does story 5.3's single-call assertion actually GATE?

    backend/.venv/Scripts/python.exe backend/scripts/falsify_coach_single_call.py

Takes no arguments. Costs ~2 `fast` calls. Exit 0 = the assertion can detect
the bug; exit 2 = it is VACUOUS and story 5.3 is not done.

Same treatment `falsify_single_call.py` (story 1.4) and
`falsify_evaluate_single_call.py` (story 4.3) give their own single-call
assertions, and for the same reason: a call-counter that cannot fail is not a
measurement. The Coach's duplicate is the quietest of the three: it writes to
`coach_reports`, a table with `unique (session_id, idx)` (0005_coach_reports.sql),
so a second `generate_coach_report` call would either collide on that
constraint (visible) or -- if the caller retried into a fresh `idx` range --
silently double the improvements a candidate reads. Either way, only
`app.llm`'s call log sees the CALL happen twice; this script proves it can.

Builds the WRONG graph -- the coach call placed ABOVE `interrupt()` in the
same node, the exact bug CLAUDE.md's load-bearing rule exists to prevent --
drives one start/resume cycle, and applies test_conduct_loop.py's own
`_ok_llm_calls(agent=...)` counting logic to it, filtered to `agent="coach"`
specifically (never a total): story 4.3's near-miss is on record for exactly
this reason -- doubling the expected count instead of filtering by agent
would have made the assertion unable to say WHICH agent duplicated.

EXPECTED: the wrong graph logs 2 `outcome=ok` records tagged `agent=coach`
for ONE session, so the assertion that demands exactly 1 goes RED. If it
logs 1, the assertion cannot detect the bug it exists to detect.

Runs on `fast` with a deliberately tiny case world and a single scored
dimension: the property under test is model-independent graph mechanics, and
`generate_coach_report`'s own call is real work regardless of world size, so
there is nothing to gain from a bigger one.

Does NOT touch `app/graph/build.py` -- the wrong graph is built entirely
inside this script, same as the two scripts before it. The real
`coach_report` node stays on `decide_next`'s one-time "exit" edge, never
revisited by the loop.
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

from app.agents.coach import generate_coach_report  # noqa: E402
from app.config import settings  # noqa: E402
from app.graph.state import InterviewState  # noqa: E402
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # noqa: E402
from langgraph.graph import END, StateGraph  # noqa: E402
from langgraph.types import Command, interrupt  # noqa: E402

# Small on purpose, same reasoning as the two prior scripts' worlds: the
# property under test is graph mechanics, not prompt quality, and a bigger
# world only spends more of the shared TPM budget for no extra signal.
CASE_WORLD = {
    "company": {"name": "Palewell Analytics", "one_line": "usage analytics for mid-market SaaS"},
    "market": {"description": "B2B analytics", "size_usd": "$2.1B"},
    "situation": {
        "prompt": "Should Palewell Analytics build a native mobile dashboard this quarter?",
        "tension": "Mobile usage is rising but engineering capacity is fixed.",
        "options": ["Build mobile now", "Ship a mobile web view", "Defer to next quarter"],
    },
    "metrics": {"arr_usd": "$6.4M", "customer_count": 340, "monthly_churn_pct": 4.6},
}
QUESTION = "What is Palewell Analytics' biggest threat over the next three years?"
LEVEL = "PM"

# One scored dimension (a quote for a 'moment' improvement) plus four
# unscored ones (material for 'gap' improvements) -- `generate_coach_report`
# raises if BOTH `available_quotes` and `unevidenced_dimensions` are empty,
# and this shape keeps it well clear of that guard either way.
EVALUATIONS = [
    {
        "turn_idx": 0,
        "dimension_scores": [
            {
                "dimension": "decision_quality",
                "score": 2,
                "evidence_quote": (
                    "I would ship the mobile web view first because it reaches every one of "
                    "the 340 customers this quarter without new headcount."
                ),
                "reasoning": "Names a choice but never says what would change the decision.",
            }
        ],
        "not_assessed": ["business_model_fluency", "market_accuracy", "structural_clarity", "point_of_view"],
    }
]

# 75s, same constant and same reasoning as `tests/test_conduct_loop.py`'s
# `_MIN_SECONDS_BETWEEN_LLM_CALLS`: COACH_MAX_TOKENS alone (4096) is already
# 51% of the 8,000 TPM ceiling, and this script's system prompt is the
# longest of any agent in this codebase, so two coach calls back to back are
# a materially larger pair than the evaluator script's 21s was sized for.
# 75s clears a full 60s rolling window with margin rather than trying to
# split the ceiling between two large requests.
_SECONDS_BETWEEN_CALLS = 75.0


class _Counter(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def ok_calls(self, agent: str) -> list[str]:
        # Filtered by agent, never a total -- story 4.3's near-miss is on
        # record for exactly this reason (see module docstring).
        return [
            r.getMessage()
            for r in self.records
            if r.name == "app.llm"
            and r.getMessage().startswith("llm_call")
            and "outcome=ok" in r.getMessage()
            and f"agent={agent}" in r.getMessage()
        ]


async def broken_node(state: InterviewState) -> dict:
    """THE BUG, on purpose: the coach call above interrupt() in the same
    node. This is the shape `coach_report_node` would be if `decide_next`'s
    "exit" edge pointed at a node the loop could revisit, instead of the
    real graph's one-time edge into a node with no outgoing edge back into
    the loop."""
    report = await generate_coach_report(
        state["case_world"], QUESTION, LEVEL, EVALUATIONS, role="fast"
    )
    value = interrupt({"improvements": len(report.improvements)})
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
            await graph.ainvoke({"session_id": session_id, "case_world": CASE_WORLD}, cfg)
            at_pause = len(handler.ok_calls("coach"))

            await asyncio.sleep(_SECONDS_BETWEEN_CALLS)
            await graph.ainvoke(Command(resume={"type": "answer", "text": "done"}), cfg)
            after = len(handler.ok_calls("coach"))

        print(f"\nWRONG graph (coach call above interrupt, same node), ONE session")
        print(f"  agent=coach outcome=ok records at pause       : {at_pause}")
        print(f"  agent=coach outcome=ok records after resume   : {after}")
        print(f"\n  assertion 'exactly 1 per session' -> "
              f"{'PASSES (VACUOUS - CANNOT DETECT THE BUG)' if after == 1 else 'FAILS as it must'}")
        if after == 1:
            print("\n  \U0001f534 The wrong graph called the Coach only ONCE. The single-call")
            print("     assertion proves nothing, and a duplicate coach call would still be")
            print("     invisible to a reader of coach_reports if the second call ever wrote")
            print("     one. Story 5.3 is not done.")
        rc = 0 if after != 1 else 2
    finally:
        conn = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
        try:
            with conn.cursor() as cur:
                for t in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
                    cur.execute(f"delete from {t} where thread_id = %s", (session_id,))
                # coach_reports cascades off sessions, and `generate_coach_report`
                # is a pure function that writes nothing itself -- counted below
                # rather than assumed, same as the evaluator script's residue check.
                cur.execute("delete from sessions where id = %s", (session_id,))
            conn.commit()
            with conn.cursor() as cur:
                cur.execute("select count(*) from sessions where id = %s", (session_id,))
                sessions_left = cur.fetchone()[0]
                cur.execute(
                    "select count(*) from coach_reports where session_id = %s", (session_id,)
                )
                coach_reports_left = cur.fetchone()[0]
                print(f"\n  residue: sessions rows = {sessions_left}, "
                      f"coach_reports rows = {coach_reports_left}")
        finally:
            conn.close()
    return rc


if __name__ == "__main__":
    # psycopg async cannot run on Windows' default ProactorEventLoop.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    sys.exit(asyncio.run(main()))
