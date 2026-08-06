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

import asyncio
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

# ══════════════════════════════════════════════════════════════════════════
# TPM pacing. Added 2026-08-05, after this file went 2-failed/7-passed with
# BOTH failures being `tokens per minute (TPM): Limit 8000` -- rate limiting,
# not defects, classified before being believed (CLAUDE.md).
#
# Every live test here drives the Resume Analyst on a real resume, ~3,800
# tokens per call measured from the 429 body itself ("Used 4547, Requested
# 3783"). Two of them inside one minute is already 7,600 of the 8,000 TPM
# bucket, so the file was always one test away from this and simply had
# fewer tests before.
#
# 35s, not the golden suites' 60/90: those send a whole case_world or a
# resume plus a large schema, this sends a SHORT_RESUME. 8,000/60 = 133
# tokens/sec refill, so 3,800 tokens needs ~29s of refill; 35 is that plus
# margin. The three golden suites set the precedent for pacing as an autouse
# fixture rather than a retry -- a retry would hide the pacing problem and
# spend the budget twice.
# ══════════════════════════════════════════════════════════════════════════
_PACE_SECONDS = 35


@pytest.fixture(autouse=True)
async def _pace_for_tokens_per_minute():
    yield
    await asyncio.sleep(_PACE_SECONDS)

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

    Story 3.2: this resume no longer runs the graph to completion. It now
    also drives `generate_case_world -> plan_interview -> ask_question ->
    await_candidate`, which pauses AGAIN at the interview's first question
    -- so a SECOND `__interrupt__` here is the CORRECT outcome, not a
    regression. (Before story 3.2, `plan_interview -> END` meant a resume
    finished the graph outright, which is what this test's assertion used
    to check.) `resumed["assessed_level"]` still carries the correction
    either way, because LangGraph's `ainvoke` return holds every
    accumulated state channel up to wherever it next pauses, not just the
    last node's own delta -- that is the actual property this test exists
    to prove, and it is unaffected by how much further the graph runs
    afterward.
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

    assert "__interrupt__" in resumed, (
        "graph did not pause at await_candidate for the interview's first "
        "question -- expected the conduct loop (story 3.2) to have started"
    )
    assert resumed["assessed_level"] == corrected_level, (
        f"the resumed value never reached state: expected {corrected_level!r}, "
        f"got {resumed['assessed_level']!r}"
    )


async def test_a_corrected_level_reaches_the_case_architect_and_the_planner(
    checkpointer: AsyncPostgresSaver,
    graph_sessions: Callable[[str | None], str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """🔴 The candidate's CORRECTION must drive the interview, not just land
    in state. Added 2026-08-05, on Karthik's Phase 1 gate #4 decision: PM
    seniority is company-relative (a title worth Senior PM at a services firm
    reads as PM at a product company), so **the candidate selects the level
    and the agent's guess is a default, not a verdict.** That makes this
    propagation the load-bearing property of the whole confirmation flow --
    if a correction does not reach the two agents downstream, the selector
    in `ConfirmationScreen.tsx` is decoration.

    Nothing asserted it before. `build.py`'s node docstrings CLAIM it
    ("Reads `assessed_level` from STATE, never from `candidate_profile`"),
    and `test_command_resume_carries_the_candidates_level_into_state` proves
    it reaches state, and the HTTP test proves it reaches `sessions.level`.
    **None of those watch the value a downstream agent is actually called
    with** -- exactly the seam-shaped gap that let the upload bug survive
    nine sessions (DEV-STATE § Decisions 2026-08-04).

    Zero LLM tokens: both agents are stubbed to capture the level they are
    handed and return a minimal valid artifact. That is the point -- the
    property under test is what the NODES pass, not what the models say.
    """
    captured: dict[str, str] = {}

    class _World:
        @staticmethod
        def model_dump() -> dict:
            return {"company": {"name": "Stubbed Co"}, "supporting_facts": ["stub"]}

    def _fake_case_world(level, profile):
        captured["case_architect"] = level
        return _World()

    class _Q:
        @staticmethod
        def model_dump() -> dict:
            return {"idx": 0, "question": "Stub?", "primary_dimension": "decision_quality"}

    class _Plan:
        questions = [_Q()]

    async def _fake_plan(level, case_world, *, role="deep"):
        captured["planner"] = level
        return _Plan()

    # Story 3.5.4: `generate_case_world` no longer calls the generative
    # agent -- it calls `select_case_world`, which is synchronous. Patching
    # the binding this node actually calls, `app.graph.build._select_case_world`,
    # is what keeps this test watching the same property (what level does
    # the NODE hand downstream) rather than a name that no longer exists on
    # the module.
    monkeypatch.setattr("app.graph.build._select_case_world", _fake_case_world)
    monkeypatch.setattr("app.graph.build._plan_interview", _fake_plan)

    session_id = graph_sessions(SHORT_RESUME)
    graph = build_graph(checkpointer, resume_analyst_role="fast")
    config = _config(session_id)

    started = await graph.ainvoke(
        {"session_id": session_id, "resume_text": SHORT_RESUME}, config
    )
    original_level = started["__interrupt__"][0].value["assessed_level"]
    corrected_level = _a_different_level(original_level)

    await graph.ainvoke(Command(resume=corrected_level), config)

    # Positive control first: a test that captured nothing would pass both
    # assertions below vacuously, which is story 1.3a's bug in a new place.
    assert set(captured) == {"case_architect", "planner"}, (
        f"one of the two downstream agents was never called: captured {captured}"
    )
    assert captured["case_architect"] == corrected_level, (
        f"the Case Architect built a world for {captured['case_architect']!r}, but the "
        f"candidate corrected their level to {corrected_level!r} (assessed was "
        f"{original_level!r}) -- the correction was discarded"
    )
    assert captured["planner"] == corrected_level, (
        f"the Planner planned for {captured['planner']!r}, but the candidate corrected "
        f"their level to {corrected_level!r} -- the correction was discarded"
    )


async def test_resume_analyst_llm_call_fires_exactly_once_across_the_confirm_cycle(
    checkpointer: AsyncPostgresSaver,
    graph_sessions: Callable[[str | None], str],
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """THE test of story 1.4. See the module docstring.

    🔴 The Planner is STUBBED, and that is load-bearing to this test rather
    than a convenience. Story 3.2 extended the graph past `confirm_level`
    into `generate_case_world -> plan_interview`, so a resume used to
    legitimately make three LLM calls where story 1.4's graph made one.
    This test broke on that change and was committed broken in `08d8dba`,
    undetected because this file's live tests were not re-run after story
    3.2 -- the same "deselected is not passed" lesson as
    `test_conduct_loop.py`, one commit later.

    The Case Architect is deliberately NOT stubbed here, unlike the test
    above. Story 3.5.4 replaced its generative call with
    `select_case_world` (`app.graph.build._select_case_world`), which is
    synchronous, reads a checked-in JSON fixture, and makes no LLM call --
    so leaving it real costs nothing and this test still gets to exercise
    the actual node wiring end to end. Counting ALL `outcome=ok` records
    can no longer answer this test's question, and loosening the count to
    `== 2` would be worse than useless: it would pass just as happily if
    `level_candidate` re-ran. Stubbing the Planner restores the original
    property EXACTLY -- the Resume Analyst is then the only thing in the
    graph that can log an LLM call, so `== 1` means what it always meant.
    It also stops this test spending a `deep` Planner call it never needed.
    """

    class _Q:
        @staticmethod
        def model_dump() -> dict:
            return {"idx": 0, "question": "Stub?", "primary_dimension": "decision_quality"}

    class _Plan:
        questions = [_Q()]

    async def _fake_plan(level, case_world, *, role="deep"):
        return _Plan()

    monkeypatch.setattr("app.graph.build._plan_interview", _fake_plan)

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
