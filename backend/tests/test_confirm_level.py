"""Story 1.4: `level_candidate` -> `confirm_level`, the first real interrupt
on the REAL graph (`app.graph.build.build_graph`, not the story 0.6
skeleton).

THE load-bearing test in this file is
`test_resume_analyst_llm_call_fires_exactly_once_across_the_confirm_cycle`.
Same reasoning as `tests/test_interrupt.py`'s equivalent: LangGraph re-runs
an interrupting node from the top on resume, not from the `interrupt()`
line, so a doubled call would burn the Resume Analyst's rate budget on
every single confirmation with no exception raised and no state corruption
to notice -- `sessions.level` would still look right. Only the call log
(`app/llm.py`) sees a duplicate. Assert there, never on state
(PHASE-1-SPEC.md 1.4, DEV-STATE 2026-07-30).

Every live test in this file runs the Resume Analyst on `role="fast"`,
never the spec's production default `role="deep"`. The property under test
here is graph mechanics (does a node re-run, does a correction reach
state), which is model-independent -- and `deep`'s daily token budget was
recorded exhausted (199,325/200,000) on the day this file was written.
`app/graph/build.py`'s `build_graph(..., resume_analyst_role=...)`
parameter exists for exactly this: production (`app/main.py`'s lifespan)
never passes it and gets `deep`; this file always does and gets `fast`.

Two groups of fixtures/tests, mirroring `tests/test_resume_upload.py`'s
split:
  - Graph-level, via `build_graph` + the Postgres checkpointer directly
    (`tests/conftest.py`'s fixtures) -- proves the interrupt/resume
    mechanics and the single-call guarantee.
  - HTTP-level, via a real `TestClient(app)` with the app's own real
    `interview_graph` swapped for a `role="fast"` one on the SAME
    checkpointer the lifespan opened -- proves the actual routes persist
    `sessions.level` and correctly distinguish a correction from an
    acceptance, which is logic that lives in `app/main.py`'s route
    handlers, not in the graph itself.

Residue: every session this file creates (and anything cascading from it --
resumes, agent_events, per `on delete cascade` in
0001_initial_schema.sql) is deleted in teardown, along with this thread's
own checkpoint rows, same pattern as `tests/conftest.py`'s `thread_ids` and
`tests/test_resume_upload.py`'s session cleanup.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Callable, Iterator

import httpx
import psycopg
import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command

from app.config import settings
from app.graph.build import build_graph
from app.main import app

pytestmark = pytest.mark.live

LEVELS = ("APM", "PM", "Senior PM", "GPM")

# Short on purpose (CLAUDE.md's rate-limit rules): the system prompt alone is
# ~2,900 tokens, and this file's point is graph mechanics, not levelling
# quality -- that is the golden suite's job (backend/tests/golden/resume_analyst/).
SHORT_RESUME = (
    "Jordan Kim\n"
    "Product Manager, Northwind Logistics, 2021-2024\n\n"
    "Owned the shipment tracking surface end to end for a B2B logistics platform. "
    "Set the roadmap for three quarters and cut delay-reporting time from 46 hours "
    "to 9 hours by shipping a new event pipeline."
)


def _a_different_level(level: str) -> str:
    return next(candidate for candidate in LEVELS if candidate != level)


def _config(session_id: str) -> dict:
    return {"configurable": {"thread_id": session_id}}


def _ok_llm_calls(caplog: pytest.LogCaptureFixture) -> list[str]:
    """Only `outcome=ok` records -- never every `llm_call` line.

    A legitimate validate-retry inside `analyse_resume` logs `outcome=empty`
    or `outcome=invalid` for its failed attempt and THEN `outcome=ok` for
    the same logical call once it succeeds (`app/llm.py`'s
    `_LoggedStructured`). Counting every `llm_call` record would fail a
    correct retry; counting only `ok` records still catches a doubled node
    execution, because a genuine double-call produces two `ok` records
    (or one `ok` plus a second failure), never one.
    """
    return [
        record.getMessage()
        for record in caplog.records
        if record.name == "app.llm"
        and record.getMessage().startswith("llm_call")
        and "outcome=ok" in record.getMessage()
    ]


# ═══════════════════════════════════════════════════════════════════════
# Graph-level fixtures and tests -- build_graph() + the Postgres
# checkpointer directly, no HTTP layer.
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
def graph_sessions() -> Iterator[Callable[[str | None], str]]:
    """Mints a session id that doubles as the graph's `thread_id` (matching
    production -- ARCHITECTURE.md §4), inserts a real `sessions` row for it
    (required: `agent_events.session_id` and `resumes.session_id` are both
    foreign keys to `sessions`, so `level_candidate`'s writes would fail
    with a FK violation against an id with no backing row), and optionally
    seeds a `resumes` row with the given `parsed_text`.

    `user_id` is left NULL -- these tests drive the graph directly, never
    through the HTTP auth layer, so there is no real identity to attribute
    the session to. Cleanup cascades resumes/agent_events via
    `on delete cascade` and separately clears this thread's own checkpoint
    rows, matching `tests/conftest.py`'s `thread_ids`.
    """
    created: list[str] = []

    def make(parsed_text: str | None) -> str:
        session_id = str(uuid.uuid4())
        conn = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "insert into sessions (id, status) values (%s, 'created')", (session_id,)
                )
                if parsed_text is not None:
                    cur.execute(
                        "insert into resumes (session_id, storage_path, parsed_text) "
                        "values (%s, %s, %s)",
                        (session_id, f"{session_id}/resume.pdf", parsed_text),
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


async def test_ainvoke_runs_level_candidate_then_pauses_at_confirm_level(
    checkpointer: AsyncPostgresSaver,
    graph_sessions: Callable[[str | None], str],
    conn: psycopg.Connection,
) -> None:
    session_id = graph_sessions(SHORT_RESUME)
    graph = build_graph(checkpointer, resume_analyst_role="fast")

    result = await graph.ainvoke(
        {"session_id": session_id, "resume_text": SHORT_RESUME}, _config(session_id)
    )

    assert "__interrupt__" in result, f"graph did not pause; keys were {sorted(result)}"
    payload = result["__interrupt__"][0].value
    assert payload["assessed_level"] in LEVELS, payload
    assert payload["level_rationale"], "no rationale in the interrupt payload"
    assert isinstance(payload["low_confidence_fields"], list)
    assert isinstance(payload["candidate_profile"], dict)

    state = await graph.aget_state(_config(session_id))
    assert state.next == ("confirm_level",), f"expected paused at confirm_level, got {state.next}"

    # level_candidate's side effects (AGENT-RESUME-ANALYST-SPEC.md §1): one
    # agent_events row on start, one on completion, and the resumes.profile
    # write. Queried directly, not inferred from the graph's return value --
    # analyse_resume itself is a pure function, so these prove the NODE did
    # its job, not just the agent.
    conn.rollback()  # end the read transaction so this thread's inserts are visible
    with conn.cursor() as cur:
        cur.execute(
            "select status, summary from agent_events where session_id = %s order by created_at",
            (session_id,),
        )
        events = cur.fetchall()
    assert [e[0] for e in events] == ["started", "done"], events
    assert all(e[1] for e in events), f"agent_events written with no plain-language summary: {events}"

    with conn.cursor() as cur:
        cur.execute("select profile from resumes where session_id = %s", (session_id,))
        (profile,) = cur.fetchone()
    assert profile is not None, "level_candidate did not write resumes.profile"


async def test_command_resume_carries_the_candidates_level_into_state(
    checkpointer: AsyncPostgresSaver, graph_sessions: Callable[[str | None], str]
) -> None:
    """Graph-level half of PHASE-1-SPEC.md 1.4's third acceptance box: the
    correction reaches STATE via `interrupt()`'s return. The HTTP-level test
    below (`test_confirm_route_persists_a_correction_to_sessions_level`)
    covers the other half -- persistence to `sessions.level`, which is the
    route handler's job, not `confirm_level`'s (confirm_level may contain
    nothing but `interrupt()` and its return; see CLAUDE.md).
    """
    session_id = graph_sessions(SHORT_RESUME)
    graph = build_graph(checkpointer, resume_analyst_role="fast")
    config = _config(session_id)

    started = await graph.ainvoke(
        {"session_id": session_id, "resume_text": SHORT_RESUME}, config
    )
    original_level = started["__interrupt__"][0].value["assessed_level"]
    corrected_level = _a_different_level(original_level)

    resumed = await graph.ainvoke(Command(resume=corrected_level), config)

    assert "__interrupt__" not in resumed, "graph paused a second time instead of finishing"
    assert resumed["assessed_level"] == corrected_level, (
        f"the resumed value never reached state: expected {corrected_level!r}, "
        f"got {resumed['assessed_level']!r}"
    )


async def test_resume_analyst_llm_call_fires_exactly_once_across_the_confirm_cycle(
    checkpointer: AsyncPostgresSaver,
    graph_sessions: Callable[[str | None], str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """THE test of story 1.4. See the module docstring."""
    session_id = graph_sessions(SHORT_RESUME)
    graph = build_graph(checkpointer, resume_analyst_role="fast")
    config = _config(session_id)

    with caplog.at_level(logging.INFO, logger="app.llm"):
        started = await graph.ainvoke(
            {"session_id": session_id, "resume_text": SHORT_RESUME}, config
        )
        calls_at_pause = _ok_llm_calls(caplog)
        original_level = started["__interrupt__"][0].value["assessed_level"]

        resumed = await graph.ainvoke(Command(resume=original_level), config)
        calls_after_resume = _ok_llm_calls(caplog)

    assert len(calls_at_pause) == 1, (
        f"expected exactly one successful Resume Analyst call before the pause, got {calls_at_pause}"
    )
    assert len(calls_after_resume) == 1, (
        "confirm_level re-ran level_candidate's LLM call on resume -- the constraint the "
        f"confirm cycle rests on is broken. Calls: {calls_after_resume}"
    )
    assert resumed["assessed_level"] == original_level


# ═══════════════════════════════════════════════════════════════════════
# HTTP-level fixtures and tests -- real routes, real Supabase Auth, the
# app's real `interview_graph` swapped to `role="fast"` on its own
# Postgres checkpointer.
# ═══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class Identity:
    user_id: str
    access_token: str


def _sign_up_anonymous() -> Identity:
    resp = httpx.post(
        f"{settings.supabase_url}/auth/v1/signup",
        headers={"apikey": settings.supabase_anon_key, "Content-Type": "application/json"},
        json={},
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    return Identity(user_id=body["user"]["id"], access_token=body["access_token"])


def _delete_user(user_id: str) -> None:
    resp = httpx.delete(
        f"{settings.supabase_url}/auth/v1/admin/users/{user_id}",
        headers={
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
        },
        timeout=30,
    )
    assert resp.status_code in (200, 404), f"failed to delete auth user {user_id}: {resp.text}"


def _auth_header(identity: Identity) -> dict[str, str]:
    return {"Authorization": f"Bearer {identity.access_token}"}


def _delete_session_service(session_id: str) -> None:
    conn = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
    try:
        with conn.cursor() as cur:
            cur.execute("delete from sessions where id = %s", (session_id,))
        conn.commit()
    finally:
        conn.close()


def _seed_parsed_text(session_id: str, parsed_text: str) -> None:
    """Inserts a `resumes` row directly, bypassing the upload route -- this
    file is about the level/confirm routes, not extraction (story 1.2 owns
    that, and `tests/test_resume_upload.py` already covers it). The direct
    DB connection authenticates as `postgres` and bypasses RLS entirely, so
    this works regardless of which identity owns the session.
    """
    conn = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "insert into resumes (session_id, storage_path, parsed_text) values (%s, %s, %s)",
                (session_id, f"{session_id}/resume.pdf", parsed_text),
            )
        conn.commit()
    finally:
        conn.close()


def _session_level(session_id: str) -> tuple[str | None, str | None]:
    conn = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
    try:
        with conn.cursor() as cur:
            cur.execute("select level, status from sessions where id = %s", (session_id,))
            return cur.fetchone()
    finally:
        conn.close()


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    """One TestClient for the module -- it runs `app.main`'s real lifespan
    (opens the real `AsyncPostgresSaver`, builds the real `deep`-role
    `interview_graph`) on entry. The autouse fixture below immediately
    swaps that graph for a `role="fast"` one on the SAME checkpointer,
    before any test in this file runs.
    """
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module", autouse=True)
def use_fast_role_for_resume_analyst(client: TestClient) -> None:
    """See the module docstring's budget note. Production
    (`app/main.py`'s lifespan) always builds `interview_graph` with the
    spec's default `role="deep"`; this swap is test-only and touches
    nothing any deployed process runs.
    """
    client.app.state.interview_graph = build_graph(
        client.app.state.checkpointer, resume_analyst_role="fast"
    )


@pytest.fixture(scope="module")
def identities() -> Iterator[tuple[Identity, Identity]]:
    a = _sign_up_anonymous()
    b = _sign_up_anonymous()
    assert a.user_id != b.user_id, "two signups minted the same identity"
    try:
        yield a, b
    finally:
        _delete_user(a.user_id)
        _delete_user(b.user_id)


@pytest.fixture
def leveled_session(
    client: TestClient, identities: tuple[Identity, Identity]
) -> Iterator[Callable[[], str]]:
    """Creates a session through the real `POST /session` route (so
    `user_id` is genuinely owned by identity `a`, the way `_authorize_session`
    requires) and seeds it with `SHORT_RESUME` as `parsed_text`, ready for
    `POST /session/{id}/level`. Cleanup cascades resumes/agent_events and
    clears this thread's checkpoint rows.
    """
    created: list[str] = []

    def make() -> str:
        a, _ = identities
        resp = client.post("/session", headers=_auth_header(a))
        assert resp.status_code == 200, resp.text
        session_id = resp.json()["session_id"]
        _seed_parsed_text(session_id, SHORT_RESUME)
        created.append(session_id)
        return session_id

    yield make

    conn = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
    try:
        with conn.cursor() as cur:
            for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
                cur.execute(f"delete from {table} where thread_id = any(%s)", (created,))
        conn.commit()
    finally:
        conn.close()
    for session_id in created:
        _delete_session_service(session_id)


def test_start_level_route_returns_the_resume_analysis_shape(
    client: TestClient,
    identities: tuple[Identity, Identity],
    leveled_session: Callable[[], str],
) -> None:
    a, _ = identities
    session_id = leveled_session()

    resp = client.post(f"/session/{session_id}/level", headers=_auth_header(a))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["assessed_level"] in LEVELS, body
    assert body["level_rationale"]
    assert isinstance(body["low_confidence_fields"], list)
    assert isinstance(body["candidate_profile"], dict)


def test_confirm_route_accepting_the_assessed_level_is_not_a_correction(
    client: TestClient,
    identities: tuple[Identity, Identity],
    leveled_session: Callable[[], str],
) -> None:
    a, _ = identities
    session_id = leveled_session()

    start = client.post(f"/session/{session_id}/level", headers=_auth_header(a))
    assert start.status_code == 200, start.text
    assessed_level = start.json()["assessed_level"]

    confirm = client.post(
        f"/session/{session_id}/level/confirm",
        headers=_auth_header(a),
        json={"level": assessed_level},
    )
    assert confirm.status_code == 200, confirm.text
    body = confirm.json()
    assert body["corrected"] is False, body
    assert body["level"] == assessed_level

    level, status = _session_level(session_id)
    assert level == assessed_level, f"sessions.level was not persisted: {level!r}"
    assert status == "leveled"


def test_confirm_route_persists_a_correction_to_sessions_level(
    client: TestClient,
    identities: tuple[Identity, Identity],
    leveled_session: Callable[[], str],
) -> None:
    """THE acceptance box this pair of HTTP tests exists for: a correction
    is both distinguishable from an acceptance (`corrected: true` here vs.
    `false` above) and lands in `sessions.level` as the CORRECTED value, not
    the originally assessed one.
    """
    a, _ = identities
    session_id = leveled_session()

    start = client.post(f"/session/{session_id}/level", headers=_auth_header(a))
    assert start.status_code == 200, start.text
    assessed_level = start.json()["assessed_level"]
    corrected_level = _a_different_level(assessed_level)

    confirm = client.post(
        f"/session/{session_id}/level/confirm",
        headers=_auth_header(a),
        json={"level": corrected_level},
    )
    assert confirm.status_code == 200, confirm.text
    body = confirm.json()
    assert body["corrected"] is True, body
    assert body["level"] == corrected_level

    level, status = _session_level(session_id)
    assert level == corrected_level, f"sessions.level holds the wrong value: {level!r}"
    assert level != assessed_level
    assert status == "leveled"


def test_confirm_route_404s_when_nothing_is_paused_for_the_session(
    client: TestClient,
    identities: tuple[Identity, Identity],
    leveled_session: Callable[[], str],
) -> None:
    """No LLM cost: `/level` was never called, so there is nothing to
    resume. Same `.next`-emptiness check `/skeleton/resume` already uses."""
    a, _ = identities
    session_id = leveled_session()

    resp = client.post(
        f"/session/{session_id}/level/confirm",
        headers=_auth_header(a),
        json={"level": "PM"},
    )
    assert resp.status_code == 404, resp.text


def test_start_level_route_rejects_a_session_owned_by_another_identity(
    client: TestClient,
    identities: tuple[Identity, Identity],
    leveled_session: Callable[[], str],
) -> None:
    """No LLM cost: authorization fails before the graph is ever touched."""
    _, b = identities
    session_id = leveled_session()

    resp = client.post(f"/session/{session_id}/level", headers=_auth_header(b))
    assert resp.status_code == 403, resp.text
