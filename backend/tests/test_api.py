"""Story 0.7: interrupt/resume across two separate HTTP requests.

The load-bearing test in this file is
`test_resume_continues_after_the_process_is_torn_down_and_rebuilt`. Everything
else is scaffolding around it.

Why a subprocess and not a rebuilt `TestClient`: a fresh `TestClient(app)` over
the same imported module-level `app` object proves nothing about story 0.7 —
the `AsyncPostgresSaver` connection opened by `lifespan` and any module-level
state would still be alive in this process either way. Only a genuinely
separate OS process discards that, which is the property the story exists to
prove. `import_config_subprocess` in conftest.py is the existing precedent for
this in this codebase.

Marked `live`: every test here starts a real `uvicorn` process that opens a
real `AsyncPostgresSaver` against Supabase, and the start/resume tests drive
the skeleton graph's real NVIDIA call. Nothing here is mocked, on purpose —
mocking either would defeat the point of the phase.
"""

from __future__ import annotations

import contextlib
import socket
import subprocess
import time
from pathlib import Path
from typing import Callable, Iterator

import httpx
import psycopg
import pytest
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config import settings
from app.graph.skeleton import build_skeleton_graph

pytestmark = pytest.mark.live

BACKEND_DIR = Path(__file__).resolve().parent.parent
VENV_PYTHON = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"


@pytest.fixture
def session_ids() -> Iterator[Callable[[str], None]]:
    """Deletes checkpoint rows for every `session_id` this file's tests
    observed, same cleanup as conftest.py's `thread_ids` fixture and for the
    same reason — this project tracks the 500MB free-tier cap against
    checkpoint volume, so test residue is a real if slow leak.

    Not `thread_ids` itself: that fixture *mints* a thread_id up front, but
    `/skeleton/start` mints `session_id` server-side, so this one
    *registers* an id after the response reveals it. One caller (this file),
    so it lives here rather than in conftest.py per CLAUDE.md § Style.

    Deletes `checkpoint_writes` and `checkpoint_blobs` before `checkpoints`
    (children before the row they reference) and never touches
    `checkpoint_migrations` — see conftest.py's `thread_ids` for why.
    """
    observed: list[str] = []

    def register(session_id: str) -> None:
        observed.append(session_id)

    yield register

    if not observed:
        return
    connection = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
    try:
        with connection.cursor() as cur:
            for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
                cur.execute(f"delete from {table} where thread_id = any(%s)", (observed,))
        connection.commit()
    finally:
        connection.close()


def _free_port() -> int:
    # Binding to port 0 and reading back the OS-assigned port avoids picking a
    # fixed port that a previous test's subprocess has not yet released.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextlib.contextmanager
def _running_app() -> Iterator[str]:
    """Launches `app.main:app` under a real `uvicorn` subprocess: a fresh
    interpreter, fresh import state, fresh everything except what
    `AsyncPostgresSaver` has written to Postgres. Yields the base URL once
    `/health` answers, and always terminates the process on the way out —
    so two calls to this in sequence are two genuinely separate processes,
    never overlapping.
    """
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    # NOT `python -m uvicorn app.main:app`: uvicorn's CLI calls
    # `asyncio.run()` (which creates the event loop under whatever policy is
    # already active) *before* it imports app.main, so app/main.py's own
    # platform guard runs too late to matter — confirmed by running that
    # exact command and hitting psycopg's ProactorEventLoop InterfaceError.
    # uvicorn only swaps to the selector policy itself when `--reload` or
    # `--workers>1` spawns a child process, which brings its own process-
    # teardown complexity this test does not want. Setting the policy here,
    # before `uvicorn.run()` is even called, sidesteps both: `asyncio.run()`
    # picks up whatever policy is current at the moment it creates the loop.
    bootstrap = (
        "import asyncio, sys\n"
        "if sys.platform == 'win32':\n"
        "    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())\n"
        "import uvicorn\n"
        f"uvicorn.run('app.main:app', host='127.0.0.1', port={port})\n"
    )
    proc = subprocess.Popen(
        [str(VENV_PYTHON), "-c", bootstrap],
        cwd=BACKEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.monotonic() + 20
        last_error: Exception | None = None
        healthy = False
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                output = proc.stdout.read() if proc.stdout else ""
                raise RuntimeError(f"uvicorn exited early (code {proc.returncode}):\n{output}")
            try:
                response = httpx.get(f"{base_url}/health", timeout=1)
                if response.status_code == 200:
                    healthy = True
                    break
            except httpx.TransportError as exc:
                last_error = exc
            time.sleep(0.3)
        if not healthy:
            raise RuntimeError(f"uvicorn never became healthy on {base_url}: {last_error}")
        yield base_url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)


def test_health_returns_ok() -> None:
    with _running_app() as base_url:
        response = httpx.get(f"{base_url}/health", timeout=5)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_resume_continues_after_the_process_is_torn_down_and_rebuilt(
    session_ids: Callable[[str], None],
) -> None:
    """THE test of story 0.7. `/skeleton/start` runs in one uvicorn process;
    that process is fully terminated (see `_running_app`'s `finally`) before a
    second, independent uvicorn process is even spawned to handle
    `/skeleton/resume`. Nothing survives between them except the Postgres
    checkpoint — an in-memory saver would pass every other test in this file
    and fail only this one.
    """
    with _running_app() as base_url:
        start_response = httpx.post(f"{base_url}/skeleton/start", timeout=30)
    assert start_response.status_code == 200
    session_id = start_response.json()["session_id"]
    session_ids(session_id)

    with _running_app() as base_url_2:
        resume_response = httpx.post(
            f"{base_url_2}/skeleton/resume",
            json={"session_id": session_id, "reply": "I would start by segmenting the users."},
            timeout=30,
        )
    assert resume_response.status_code == 200
    body = resume_response.json()
    assert body["session_id"] == session_id
    assert body["turn_count"] == 1, f"expected exactly one turn, got {body}"


async def test_get_state_next_reflects_pause_then_completion(
    checkpointer: AsyncPostgresSaver,
    session_ids: Callable[[str], None],
) -> None:
    """`graph.get_state(config).next` is what `/skeleton/resume` itself checks
    to tell a paused session from an unknown or finished one (see the 404
    branch in `app/main.py`). Checked here directly against the same Postgres
    checkpoint the two subprocesses above wrote to, independent of either
    process, using the fixture from `tests/conftest.py`.
    """
    graph = build_skeleton_graph(checkpointer)

    with _running_app() as base_url:
        start_response = httpx.post(f"{base_url}/skeleton/start", timeout=30)
    session_id = start_response.json()["session_id"]
    session_ids(session_id)
    config = {"configurable": {"thread_id": session_id}}

    paused = await graph.aget_state(config)
    assert paused.next == ("await_reply",), f"expected paused at await_reply, got {paused.next}"

    with _running_app() as base_url_2:
        resume_response = httpx.post(
            f"{base_url_2}/skeleton/resume",
            json={"session_id": session_id, "reply": "done"},
            timeout=30,
        )
    assert resume_response.status_code == 200

    finished = await graph.aget_state(config)
    assert finished.next == (), f"expected a finished graph, got next={finished.next}"


def test_cors_preflight_rejects_unlisted_origin_and_allows_the_configured_one() -> None:
    """A simple GET/POST with a disallowed `Origin` returns HTTP 200 with the
    `access-control-allow-origin` header merely absent — the browser enforces
    CORS, not the server. Only a preflight `OPTIONS` actually returns
    non-200. Asserting non-200 on a simple request would encode a false pass
    against correct code. See DEV-STATE § Decisions 2026-07-30.
    """
    with _running_app() as base_url:
        disallowed = httpx.options(
            f"{base_url}/skeleton/start",
            headers={
                "Origin": "http://evil.example.com",
                "Access-Control-Request-Method": "POST",
            },
            timeout=5,
        )
        allowed = httpx.options(
            f"{base_url}/skeleton/start",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
            },
            timeout=5,
        )
    assert disallowed.status_code == 400, disallowed.text
    assert "access-control-allow-origin" not in disallowed.headers

    assert allowed.status_code == 200
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
