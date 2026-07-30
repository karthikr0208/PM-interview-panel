"""FastAPI entrypoint. Story 0.7 adds /skeleton/start and /skeleton/resume,
driving `app.graph.skeleton.build_skeleton_graph` across two separate HTTP
requests — the real interview routes (/session/*, /turn) arrive in Phase 1+
once `skeleton.py` is deleted.
"""

from __future__ import annotations

import asyncio
import sys

# Windows' default ProactorEventLoop makes psycopg's async mode raise
# `InterfaceError: Psycopg cannot use the 'ProactorEventLoop' to run in
# async mode`, which the lifespan below would hit the moment it opens an
# AsyncPostgresSaver.
#
# This guard does NOT fix that for `uvicorn app.main:app` on its own:
# uvicorn's `Server.run()` calls `asyncio.run()`, which creates the event
# loop under whatever policy is already active BEFORE this module is
# imported — so a swap here runs too late for that path. What actually makes
# `make dev-api` work is `--reload`: it makes uvicorn spawn a child process
# and run its own `asyncio_setup()` in that child, before the child's
# `asyncio.run()`, independent of anything in this file. Confirmed by running
# plain `uvicorn app.main:app` (no --reload), which fails with the
# InterfaceError above.
#
# The guard still earns its place because `app.main` is also imported
# directly outside uvicorn's CLI (tests, any future non-uvicorn entry point),
# where it runs before any loop exists and is not too late. It is harmless
# either way. On Render (Linux) the selector loop is already the default, so
# the deployed start command is unaffected regardless. See DEV-STATE
# § Decisions 2026-07-30; tests/conftest.py does the same swap for the same
# reason, and tests/test_api.py's `_running_app()` documents the uvicorn-CLI
# ordering problem this guard cannot solve.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command
from pydantic import BaseModel

from app.config import settings
from app.graph.skeleton import build_skeleton_graph

# Matches tests/test_interrupt.py's INITIAL_STATE — skeleton.py itself is
# story 0.6's frozen module, so this stays local rather than adding an export
# to it for a single caller.
_INITIAL_STATE = {"messages": [], "turn_count": 0}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Opens ONE `AsyncPostgresSaver` for the app's whole life and holds it on
    `app.state`. Opening one per request would open a Supabase pooler
    connection per request. Does NOT call `.setup()` — that is
    `scripts/init_db.py`'s job, run once, never on app startup.
    """
    async with AsyncPostgresSaver.from_conn_string(settings.supabase_db_url) as saver:
        app.state.checkpointer = saver
        app.state.graph = build_skeleton_graph(saver)
        yield


app = FastAPI(title="PM Interview Panel API", lifespan=lifespan)

# ALLOWED_ORIGINS is a comma-separated list in .env; config.py has already
# split and validated it. Wide open here would defeat the point of naming an
# allowlist at all.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


class ResumeRequest(BaseModel):
    session_id: str
    reply: str


def _config(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}


@app.post("/skeleton/start")
async def skeleton_start() -> dict:
    """Starts one skeleton session. `session_id` doubles as the graph's
    `thread_id` — nothing about this session lives anywhere but Postgres, so
    a second request against this same id can land on a different process
    entirely, which is exactly what story 0.7 proves.
    """
    session_id = str(uuid.uuid4())
    result = await app.state.graph.ainvoke(_INITIAL_STATE, _config(session_id))
    if "__interrupt__" not in result:
        raise HTTPException(500, "graph did not pause at await_reply")
    return {"session_id": session_id, "interrupt": result["__interrupt__"][0].value}


@app.post("/skeleton/resume")
async def skeleton_resume(body: ResumeRequest) -> dict:
    """Resumes a paused session from its Postgres checkpoint. 404 covers both
    an unknown `session_id` and one already run to completion — `.next` is
    empty in both cases, and `Command(resume=...)` against either would not
    be resuming anything.
    """
    config = _config(body.session_id)
    state = await app.state.graph.aget_state(config)
    if not state.next:
        raise HTTPException(404, f"no paused session for session_id={body.session_id!r}")
    result = await app.state.graph.ainvoke(Command(resume=body.reply), config)
    return {"session_id": body.session_id, "turn_count": result["turn_count"]}
