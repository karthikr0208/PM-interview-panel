"""0002_rls_policies.sql, proven through the real browser path.

"A policy exists" is not the assertion — PostgREST calls with real bearer
tokens from two real anonymous identities are. That is the only way to prove
the thing story 1.1 exists to prove: session A cannot read session B's rows,
through the same HTTP path a browser actually uses.

THE FACT THAT SHAPES THIS WHOLE FILE: Supabase anonymous sign-in issues the
`authenticated` role, not `anon` (verified live 2026-07-31, DEV-STATE §
Blockers). Every identity below authenticates as `authenticated`. A test that
only probed `anon` would pass while the real path stayed open.

Exactly TWO anonymous identities are minted, once per test session (module
scope), and shared by every test here. Supabase rate-limits anonymous
sign-ins per IP — a fresh pair per test, or per table, 429s. Both identities
are deleted via the admin API in teardown; anonymous auth.users rows are
never garbage-collected on their own, and test residue in auth.users is a
recorded failure mode for this project (DEV-STATE 2026-07-30).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import httpx
import psycopg
import pytest

from app.config import settings

pytestmark = pytest.mark.live

# (table, id_column) — sessions scopes on its own `id`/`user_id`; the other
# five scope via a join back to sessions, so filtering on session_id is what
# identifies "this identity's row" for the cross-session assertions.
TABLE_ID_COLUMNS = [
    ("sessions", "id"),
    ("resumes", "session_id"),
    ("case_worlds", "session_id"),
    ("transcript_turns", "session_id"),
    ("answer_evaluations", "session_id"),
    ("agent_events", "session_id"),
]

CHECKPOINT_TABLE_PREFIX = "checkpoint"


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
    # 404 is fine if something already removed it; anything else is a real
    # failure worth surfacing rather than swallowing in teardown.
    assert resp.status_code in (200, 404), (
        f"failed to delete auth user {user_id}: {resp.status_code} {resp.text}"
    )


def _select_as(token: str, table: str, column: str, value: str) -> list[dict]:
    """A real PostgREST call as a real identity — the browser's actual path,
    not a SQL simulation of it."""
    resp = httpx.get(
        f"{settings.supabase_url}/rest/v1/{table}",
        headers={"apikey": settings.supabase_anon_key, "Authorization": f"Bearer {token}"},
        params={column: f"eq.{value}", "select": "*"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _select_as_service(table: str, column: str, value: str) -> list[dict]:
    resp = httpx.get(
        f"{settings.supabase_url}/rest/v1/{table}",
        headers={
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
        },
        params={column: f"eq.{value}", "select": "*"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _db_connect() -> psycopg.Connection:
    return psycopg.connect(settings.supabase_db_url, connect_timeout=15)


def _delete_session_service(session_id: str) -> None:
    """Cascade-deletes a session and everything hung off it, via the
    service-role DB connection (bypasses RLS — the pooler role has
    rolbypassrls = true, per DEV-STATE 2026-07-30)."""
    conn = _db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute("delete from sessions where id = %s", (session_id,))
        conn.commit()
    finally:
        conn.close()


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


@pytest.fixture(scope="module")
def fixture_rows(identities: tuple[Identity, Identity]) -> Iterator[dict[str, dict[str, str]]]:
    """One row per app table, for each identity's own session. Inserted over
    the service-role DB connection — the backend's own write path, which
    bypasses RLS entirely — not over PostgREST as the identities, since the
    identities have no INSERT policy on anything but sessions.

    Cleanup is a single delete per session; `on delete cascade` (0001) takes
    the other five tables' rows with it.
    """
    a, b = identities
    conn = _db_connect()
    conn.autocommit = True
    data: dict[str, dict[str, str]] = {}
    try:
        with conn.cursor() as cur:
            for label, identity in (("a", a), ("b", b)):
                cur.execute(
                    "insert into sessions (user_id, status) values (%s, 'created') returning id",
                    (identity.user_id,),
                )
                (session_id,) = cur.fetchone()
                cur.execute(
                    "insert into resumes (session_id, storage_path) values (%s, %s)",
                    (session_id, f"{label}/resume.pdf"),
                )
                cur.execute(
                    "insert into case_worlds (session_id, world) values (%s, %s::jsonb)",
                    (session_id, '{"probe": true}'),
                )
                cur.execute(
                    "insert into transcript_turns (session_id, idx, role, kind, content) "
                    "values (%s, 0, 'interviewer', 'question', 'rls cross-session probe')",
                    (session_id,),
                )
                cur.execute(
                    "insert into answer_evaluations "
                    "(session_id, turn_idx, dimension, score, evidence_quote) "
                    "values (%s, 0, 'structuring', 3, 'rls cross-session probe')",
                    (session_id,),
                )
                cur.execute(
                    "insert into agent_events (session_id, agent, status) "
                    "values (%s, 'resume_analyst', 'done')",
                    (session_id,),
                )
                data[label] = {"session_id": str(session_id)}
        yield data
    finally:
        for label in ("a", "b"):
            if label in data:
                _delete_session_service(data[label]["session_id"])
        conn.close()


@pytest.mark.parametrize("table,id_col", TABLE_ID_COLUMNS)
def test_cross_session_denial_matrix(
    table: str,
    id_col: str,
    identities: tuple[Identity, Identity],
    fixture_rows: dict[str, dict[str, str]],
) -> None:
    """The assertion the whole story exists to prove, on every one of the six
    tables: each identity sees its own row and NEITHER sees the other's."""
    a, b = identities
    a_session = fixture_rows["a"]["session_id"]
    b_session = fixture_rows["b"]["session_id"]

    a_sees_own = _select_as(a.access_token, table, id_col, a_session)
    assert len(a_sees_own) == 1, f"{table}: identity A cannot see its own row"

    a_sees_b = _select_as(a.access_token, table, id_col, b_session)
    assert a_sees_b == [], f"{table}: identity A can see identity B's row(s): {a_sees_b}"

    b_sees_a = _select_as(b.access_token, table, id_col, a_session)
    assert b_sees_a == [], f"{table}: identity B can see identity A's row(s): {b_sees_a}"

    b_sees_own = _select_as(b.access_token, table, id_col, b_session)
    assert len(b_sees_own) == 1, f"{table}: identity B cannot see its own row"


@pytest.mark.parametrize("table,id_col", TABLE_ID_COLUMNS)
def test_service_role_bypasses_everything(
    table: str, id_col: str, fixture_rows: dict[str, dict[str, str]]
) -> None:
    """The backend's own path is unaffected by any of this — it authenticates
    with the service-role key, which bypasses RLS."""
    a_session = fixture_rows["a"]["session_id"]
    b_session = fixture_rows["b"]["session_id"]

    rows_a = _select_as_service(table, id_col, a_session)
    rows_b = _select_as_service(table, id_col, b_session)
    assert len(rows_a) == 1, f"{table}: service role cannot see identity A's row"
    assert len(rows_b) == 1, f"{table}: service role cannot see identity B's row"


def test_sessions_insert_policy_rejects_spoofed_owner(
    identities: tuple[Identity, Identity],
) -> None:
    """A browser authenticated as A must not be able to create a session
    claiming to belong to B. Proves the `with check` half of the INSERT
    policy, not just the `using` half the SELECT tests already cover."""
    a, b = identities
    resp = httpx.post(
        f"{settings.supabase_url}/rest/v1/sessions",
        headers={
            "apikey": settings.supabase_anon_key,
            "Authorization": f"Bearer {a.access_token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        json={"user_id": b.user_id, "status": "created"},
        timeout=30,
    )
    assert 400 <= resp.status_code < 500, (
        f"expected the spoofed insert to be rejected, got {resp.status_code}: {resp.text}"
    )


def test_sessions_insert_policy_allows_own_uid(identities: tuple[Identity, Identity]) -> None:
    """The other half of the same box: the policy must not be so restrictive
    that a candidate cannot create their own session either. A denial-only
    policy would pass the spoof test above while breaking the product."""
    a, _ = identities
    resp = httpx.post(
        f"{settings.supabase_url}/rest/v1/sessions",
        headers={
            "apikey": settings.supabase_anon_key,
            "Authorization": f"Bearer {a.access_token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        },
        json={"user_id": a.user_id, "status": "created"},
        timeout=30,
    )
    assert resp.status_code in (200, 201), (
        f"expected the candidate's own-uid insert to succeed, got {resp.status_code}: {resp.text}"
    )
    created = resp.json()
    row = created[0] if isinstance(created, list) else created
    # This test creates a real row outside fixture_rows' tracking — clean it
    # up immediately rather than leaving it for module teardown.
    _delete_session_service(row["id"])


def test_checkpoint_tables_have_zero_policies() -> None:
    """LangGraph's four checkpoint% tables must stay untouched by this
    migration. They hold entire interview states — resume text, full
    transcript, every evaluation — and nothing in a browser should ever read
    them (DEV-STATE 2026-07-30, the worst exposure found in the project)."""
    conn = _db_connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "select tablename, count(*) from pg_policies "
                "where schemaname = 'public' and tablename like %s "
                "group by tablename",
                (f"{CHECKPOINT_TABLE_PREFIX}%",),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    assert rows == [], f"checkpoint tables have policies, they must have none: {rows}"
