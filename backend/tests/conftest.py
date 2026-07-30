"""Shared fixtures. Only fixtures with a real caller live here — see CLAUDE.md.

`tests/__init__.py` makes this directory a package with no `__init__.py`
above it (backend/ has none), so pytest's import machinery inserts
backend/ into sys.path[0]. That is what lets `from app.config import ...`
resolve cleanly in every test module without a per-file sys.path hack.

The Postgres fixtures below started life inside `test_checkpointer.py` and
moved here in story 0.6, when `test_interrupt.py` became their second caller.
"""
from __future__ import annotations

import asyncio
import sys

# Must run before anything imports psycopg's async machinery, which is why it
# sits at conftest import time rather than inside a fixture: psycopg refuses
# Windows' default ProactorEventLoop with `InterfaceError: Psycopg cannot use
# the 'ProactorEventLoop' to run in async mode`. Render is Linux, where the
# selector loop is already the default, so this is local-only. See DEV-STATE
# § Decisions 2026-07-30.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import os
import subprocess
import uuid
from pathlib import Path
from typing import AsyncIterator, Callable, Iterator

import psycopg
import pytest
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config import settings

BACKEND_DIR = Path(__file__).resolve().parent.parent
VENV_PYTHON = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"


@pytest.fixture
def import_config_subprocess() -> Callable[[dict[str, str]], "subprocess.CompletedProcess[str]"]:
    """Runs `import app.config` in a fresh child process, with `overrides`
    layered on top of the current environment.

    A child process is required — config.py validates os.environ at import
    time (module level), so simulating "this variable is absent" needs a
    process where it is genuinely absent going in. Setting it to "" in the
    child's environment does that without touching the real backend/.env:
    `_read_required()` treats a blank string as missing, and
    `load_dotenv(override=False)` never repopulates a key the child's
    environment already contains, empty or not.
    """

    def run(overrides: dict[str, str]) -> "subprocess.CompletedProcess[str]":
        env = {**os.environ, **overrides}
        return subprocess.run(
            [str(VENV_PYTHON), "-c", "import app.config"],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

    return run


@pytest.fixture
def conn() -> Iterator[psycopg.Connection]:
    """A plain connection, independent of AsyncPostgresSaver's dict_row row
    factory, so verification queries return normal tuples. `finally: rollback`
    is a safety net on top of each test's own rollback, so a test that raises
    mid-transaction still leaves nothing behind."""
    connection = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


@pytest.fixture
async def checkpointer() -> AsyncIterator[AsyncPostgresSaver]:
    async with AsyncPostgresSaver.from_conn_string(settings.supabase_db_url) as saver:
        yield saver


@pytest.fixture
def thread_ids() -> Iterator[Callable[[], str]]:
    """Factory for unique thread_ids, all cleaned up in teardown regardless
    of how many a test minted. uuid4 per test (never a fixed constant) is
    what lets tests run twice in a row, or concurrently, without colliding.

    Cleanup goes through a plain connection — the role connecting via
    `supabase_db_url` bypasses RLS (it must, or even the setup step and
    LangGraph's own writes would be invisible to themselves), which is
    exactly why the RLS tests have to prove denial from a *different* role
    rather than trusting this one.

    Deletes `checkpoint_writes` and `checkpoint_blobs` before `checkpoints`
    (children before the row they reference) and never touches
    `checkpoint_migrations` — wiping that would make `.setup()` re-run
    LangGraph's internal schema migrations.
    """
    created: list[str] = []

    def make() -> str:
        thread_id = str(uuid.uuid4())
        created.append(thread_id)
        return thread_id

    yield make

    if not created:
        return
    connection = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
    try:
        with connection.cursor() as cur:
            for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
                cur.execute(f"delete from {table} where thread_id = any(%s)", (created,))
        connection.commit()
    finally:
        connection.close()
