"""Does story 1.4's single-call assertion actually GATE?

    backend/.venv/Scripts/python.exe backend/scripts/falsify_single_call.py

Takes no arguments. Costs ~2 `fast` calls. Exit 0 = the assertion can detect
the bug; exit 2 = it is VACUOUS and story 1.4 is not done.


Story 1.3a's most important assertion passed vacuously on all eight cases, and
story 0.6's idempotency check was falsified against a deliberately wrong graph
before being trusted. Same treatment here: a call-counter that cannot fail is
not a measurement.

Builds the WRONG graph -- the LLM call placed ABOVE `interrupt()` in the same
node, which is the exact bug CLAUDE.md's load-bearing rule exists to prevent --
drives the same start/resume cycle, and applies test_confirm_level.py's own
`_ok_llm_calls` counting logic to it.

EXPECTED: the wrong graph logs 2 `outcome=ok` records, so the assertion that
demands exactly 1 goes RED. If it logs 1, the assertion cannot detect the bug
it exists to detect.

Runs on `fast` with a deliberately tiny resume: `deep` is exhausted and the
property under test is model-independent graph mechanics.
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

from app.agents.resume_analyst import analyse_resume  # noqa: E402
from app.config import settings  # noqa: E402
from app.graph.state import InterviewState  # noqa: E402
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # noqa: E402
from langgraph.graph import END, StateGraph  # noqa: E402
from langgraph.types import Command, interrupt  # noqa: E402

RESUME = (
    "Ada Byron\nProduct Manager, Loomly (2022-2024)\n"
    "Owned the notifications surface end to end and set its roadmap.\n"
    "Cut opt-outs from 12.4% to 7.1% in two quarters.\n"
)


class _Counter(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def ok_calls(self) -> list[str]:
        # Copied verbatim in spirit from tests/test_confirm_level.py::_ok_llm_calls
        return [
            r.getMessage()
            for r in self.records
            if r.name == "app.llm"
            and r.getMessage().startswith("llm_call")
            and "outcome=ok" in r.getMessage()
        ]


async def broken_node(state: InterviewState) -> dict:
    """THE BUG, on purpose: an LLM call above interrupt() in the same node."""
    analysis = await analyse_resume(state["resume_text"], role="fast")
    chosen = interrupt({"assessed_level": analysis.assessed_level})
    return {"assessed_level": chosen}


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
            await graph.ainvoke({"session_id": session_id, "resume_text": RESUME}, cfg)
            at_pause = len(handler.ok_calls())
            await graph.ainvoke(Command(resume="PM"), cfg)
            after = len(handler.ok_calls())

        print(f"\nWRONG graph (LLM call above interrupt, same node)")
        print(f"  outcome=ok records at pause       : {at_pause}")
        print(f"  outcome=ok records after resume   : {after}")
        print(f"\n  assertion 'exactly 1 across the cycle' -> "
              f"{'PASSES (VACUOUS - CANNOT DETECT THE BUG)' if after == 1 else 'FAILS as it must'}")
        rc = 0 if after != 1 else 2
    finally:
        conn = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
        try:
            with conn.cursor() as cur:
                for t in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
                    cur.execute(f"delete from {t} where thread_id = %s", (session_id,))
                cur.execute("delete from sessions where id = %s", (session_id,))
            conn.commit()
            with conn.cursor() as cur:
                cur.execute("select count(*) from sessions where id = %s", (session_id,))
                print(f"\n  residue: sessions rows for this thread = {cur.fetchone()[0]}")
        finally:
            conn.close()
    return rc


if __name__ == "__main__":
    # psycopg async cannot run on Windows' default ProactorEventLoop.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    sys.exit(asyncio.run(main()))
