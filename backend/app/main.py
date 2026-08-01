"""FastAPI entrypoint. Story 0.7 adds /skeleton/start and /skeleton/resume,
driving `app.graph.skeleton.build_skeleton_graph` across two separate HTTP
requests. Story 1.2 adds the first real routes, /session and
/session/{id}/resume, independent of the skeleton graph. Story 1.4 adds
/session/{id}/level and /session/{id}/level/confirm, driving the real graph
(`app.graph.build.build_graph`) across its first interrupt. The skeleton
routes are deleted in story 1.7, once 1.4's routes and a UI exercising them
(1.6) replace them.
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
from typing import AsyncIterator, Literal

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command
from pydantic import BaseModel

from app.config import settings
from app.graph.build import build_graph
from app.graph.skeleton import build_skeleton_graph
from app.resume import CONTENT_TYPES, MAX_RESUME_BYTES, ResumeValidationError, extract_text
from app.supabase_client import (
    AuthTokenError,
    StorageError,
    delete_object,
    rest_insert,
    rest_select_one,
    rest_update,
    upload_object,
    validate_bearer_token,
)

RESUMES_BUCKET = "resumes"

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
        # The real interview graph, alongside the skeleton above rather than
        # replacing it -- story 1.7 deletes the skeleton and its routes only
        # after this one is verified. Production default (`deep`) is
        # implicit; tests override `app.state.interview_graph` directly
        # rather than threading a role parameter through this route layer.
        app.state.interview_graph = build_graph(saver)
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


# ── Story 1.2: real session + resume-upload routes ──────────────────────
# Independent of the skeleton graph above — story 1.7 deletes everything
# above this line without touching anything below it.


async def _authorize_session(session_id: str, authorization: str) -> str:
    """Resolves the caller's identity and confirms it owns `session_id`.

    Three callers share this exact check (upload, start-level, confirm-
    level): validate the bearer token, look up the session, 404 if it does
    not exist, 403 if it belongs to someone else. Returns the caller's
    `user_id` for callers that want it (none do today, but a 403 without it
    would still need the lookup). See `upload_resume`'s docstring for why
    this check exists beyond RLS: the backend connects with the service
    role, which bypasses RLS entirely, so nothing else stops one candidate
    reading or resuming another's session by guessing its id.
    """
    try:
        user_id = await validate_bearer_token(authorization)
    except AuthTokenError as exc:
        raise HTTPException(401, str(exc)) from exc

    session_row = await rest_select_one("sessions", "id", session_id, select="user_id")
    if session_row is None:
        raise HTTPException(404, f"No session with id {session_id!r}.")
    if session_row["user_id"] != user_id:
        raise HTTPException(403, "This session does not belong to the calling identity.")
    return user_id


async def _read_limited(file: UploadFile, max_bytes: int) -> bytes:
    """Reads `file` in chunks, aborting as soon as the running total exceeds
    `max_bytes`, so an oversized upload is rejected without ever buffering
    more than max_bytes (+ one chunk) into memory. Enforcing this by reading
    a client-declared Content-Length header would trust the client; this
    counts the bytes actually received instead.
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(65536)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                400,
                f"File exceeds the {max_bytes // (1024 * 1024)}MB limit. "
                "Please upload a smaller file.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


@app.post("/session")
async def create_session(authorization: str = Header(...)) -> dict:
    """Creates a session row owned by the calling identity.

    `user_id` MUST come from the caller's validated JWT, never from a
    client-supplied value: the backend connects with the service role, which
    bypasses RLS, so an unvalidated uid would let anyone create a session
    owned by anyone. See PHASE-1-SPEC.md 1.2's design question.
    """
    try:
        user_id = await validate_bearer_token(authorization)
    except AuthTokenError as exc:
        raise HTTPException(401, str(exc)) from exc

    row = await rest_insert("sessions", {"user_id": user_id, "status": "created"})
    return {"session_id": row["id"]}


@app.post("/session/{session_id}/resume")
async def upload_resume(
    session_id: str,
    authorization: str = Header(...),
    file: UploadFile = File(...),
) -> dict:
    """Accepts a PDF or DOCX resume, extracts its text, stores the file in
    the private `resumes` bucket, and writes `storage_path` + `parsed_text`.

    Beyond PHASE-1-SPEC.md 1.2's literal acceptance boxes (which only name
    `/session` for the auth check), this route also validates the caller and
    confirms they own `session_id` before accepting anything. Story 1.1 spent
    real effort making sure a browser cannot read another session's rows;
    leaving this route wide open to any caller who knows a session_id would
    reopen a version of the same hole from the write side. Extending the same
    check costs one extra query.
    """
    await _authorize_session(session_id, authorization)

    content = await _read_limited(file, MAX_RESUME_BYTES)
    if not content:
        raise HTTPException(400, "The uploaded file is empty.")

    try:
        kind, parsed_text = extract_text(content)
    except ResumeValidationError as exc:
        raise HTTPException(400, str(exc)) from exc

    storage_path = f"{session_id}/resume.{kind}"
    try:
        await upload_object(RESUMES_BUCKET, storage_path, content, CONTENT_TYPES[kind])
    except StorageError as exc:
        raise HTTPException(502, str(exc)) from exc

    try:
        resume_row = await rest_insert(
            "resumes",
            {"session_id": session_id, "storage_path": storage_path, "parsed_text": parsed_text},
        )
    except Exception:
        # The upload above succeeded; if the DB write fails, do not leave an
        # orphan object behind in storage for something that never became a
        # resumes row. Best-effort — see supabase_client.delete_object.
        await delete_object(RESUMES_BUCKET, storage_path)
        raise

    return {"resume_id": resume_row["id"], "storage_path": storage_path}


# ── Story 1.4: level_candidate -> confirm_level, the first real interrupt ──
# Independent of the skeleton graph -- story 1.7 deletes everything above the
# story 1.2 marker without touching anything below it.


class LevelCorrectionRequest(BaseModel):
    # Same four values as AGENT-RESUME-ANALYST-SPEC.md's schema and the
    # frontend's `Level` type (frontend/src/lib/types.ts) -- an out-of-
    # vocabulary level is a 422 at the request boundary, not a value that
    # reaches the graph and `sessions.level`.
    level: Literal["APM", "PM", "Senior PM", "GPM"]


@app.post("/session/{session_id}/level")
async def start_level_assessment(session_id: str, authorization: str = Header(...)) -> dict:
    """Runs the Resume Analyst (`level_candidate`) and returns the payload
    the graph paused at `confirm_level` with -- shaped exactly like the
    frontend's `ResumeAnalysis` (`frontend/src/lib/types.ts`), so the
    browser can hand this response straight to `ConfirmationScreen`.

    If a session's graph has already started (a retried request, a double
    click), this returns the SAME interrupt payload from the existing
    checkpoint rather than invoking the graph again -- the Resume Analyst's
    LLM call is not free, and a second run would burn it a second time for
    nothing new to show the candidate.
    """
    await _authorize_session(session_id, authorization)

    config = _config(session_id)
    existing = await app.state.interview_graph.aget_state(config)
    if existing.interrupts:
        return existing.interrupts[0].value

    resume_row = await rest_select_one("resumes", "session_id", session_id, select="parsed_text")
    if resume_row is None or not resume_row.get("parsed_text"):
        raise HTTPException(404, "No resume text found for this session. Upload a resume first.")

    result = await app.state.interview_graph.ainvoke(
        {"session_id": session_id, "resume_text": resume_row["parsed_text"]}, config
    )
    if "__interrupt__" not in result:
        raise HTTPException(500, "The graph did not pause at confirm_level as expected.")
    return result["__interrupt__"][0].value


@app.post("/session/{session_id}/level/confirm")
async def confirm_level_route(
    session_id: str,
    body: LevelCorrectionRequest,
    authorization: str = Header(...),
) -> dict:
    """Resumes the paused `confirm_level` interrupt with the candidate's
    chosen level, persists it to `sessions.level`, and reports whether it
    differed from the level the Resume Analyst originally assessed.

    404 covers both an unknown `session_id` and one with no paused level
    confirmation (never started, or already confirmed) -- `.next` is empty
    in both cases, matching `/skeleton/resume`'s existing pattern.
    """
    await _authorize_session(session_id, authorization)

    config = _config(session_id)
    state = await app.state.interview_graph.aget_state(config)
    if not state.next:
        raise HTTPException(
            404, f"No paused level confirmation for session_id={session_id!r}."
        )
    original_level = state.values.get("assessed_level")

    result = await app.state.interview_graph.ainvoke(Command(resume=body.level), config)
    confirmed_level = result["assessed_level"]
    corrected = confirmed_level != original_level

    await rest_update("sessions", "id", session_id, {"level": confirmed_level, "status": "leveled"})

    return {"session_id": session_id, "level": confirmed_level, "corrected": corrected}
