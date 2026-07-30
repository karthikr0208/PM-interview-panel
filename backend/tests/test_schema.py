"""0001_initial_schema.sql, verified against the live database.

Every test here is marked `live` and hits the real Supabase project over the
session pooler. Deselect with `-m "not live"`. The migration is idempotent
and already applied — these tests assert what it produced, not what the SQL
claims to do.

Every test either only reads, or writes inside a transaction it rolls back
before returning. The database is shared; a leftover row would make a later
run of this same file lie.
"""

from __future__ import annotations

from typing import Iterator

import psycopg
import pytest

from app.config import settings

pytestmark = pytest.mark.live

EXPECTED_TABLES = {
    "sessions",
    "resumes",
    "case_worlds",
    "transcript_turns",
    "answer_evaluations",
    "agent_events",
}


@pytest.fixture
def conn() -> Iterator[psycopg.Connection]:
    """One connection per test, transactional. `finally: rollback` is a
    safety net on top of each test's own rollback — a test that raises
    before reaching its rollback line must not leave data behind either.
    """
    connection = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
    try:
        yield connection
    finally:
        connection.rollback()
        connection.close()


def test_all_six_tables_exist(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("select tablename from pg_tables where schemaname = 'public'")
        tables = {row[0] for row in cur.fetchall()}
    assert tables == EXPECTED_TABLES, f"public schema has {tables}, expected {EXPECTED_TABLES}"


def test_rls_enabled_on_every_table(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("select tablename, rowsecurity from pg_tables where schemaname = 'public'")
        rows = dict(cur.fetchall())
    assert set(rows) == EXPECTED_TABLES
    for table, enabled in rows.items():
        assert enabled is True, f"RLS is not enabled on {table}"


def test_rls_denies_anon_and_authenticated_with_no_policies(conn: psycopg.Connection) -> None:
    """`rowsecurity = true` alone does not prove the data is hidden — this
    test proves it empirically.

    `anon` and `authenticated` hold table-level SELECT grants (Supabase adds
    these by default), so the table is reachable by both roles. It is RLS
    enabled with zero policies that denies every row. Asserting "RLS is
    enabled" alone (the test above) would not catch a policy accidentally
    opening the table back up later; this test would.
    """
    with conn.cursor() as cur:
        cur.execute("insert into sessions (status) values ('created') returning id")
        (session_id,) = cur.fetchone()
        cur.execute(
            "insert into transcript_turns (session_id, idx, role, kind, content) "
            "values (%s, 0, 'interviewer', 'question', 'schema test turn')",
            (session_id,),
        )

        cur.execute("select count(*) from transcript_turns where session_id = %s", (session_id,))
        assert cur.fetchone()[0] == 1, "row not visible to the connecting role"

        cur.execute("set local role anon")
        cur.execute("select count(*) from transcript_turns where session_id = %s", (session_id,))
        assert cur.fetchone()[0] == 0, "anon can read a row RLS with no policies should hide"

        cur.execute("set local role authenticated")
        cur.execute("select count(*) from transcript_turns where session_id = %s", (session_id,))
        assert cur.fetchone()[0] == 0, "authenticated can read a row RLS with no policies should hide"

        cur.execute("reset role")

    conn.rollback()


def test_constraints_reject_bad_data(conn: psycopg.Connection) -> None:
    """The three data-integrity constraints, exercised in one transaction via
    savepoints — a failed insert aborts the current (sub)transaction, so each
    check gets its own savepoint to roll back to without poisoning the rest.
    """
    with conn.cursor() as cur:
        cur.execute("insert into sessions (status) values ('created') returning id")
        (session_id,) = cur.fetchone()

        # evidence_quote check: enforces the PRD guarantee that no score
        # ships without evidence, at the database rather than in prompt
        # text. An agent that stops quoting fails loudly here instead of
        # producing a confident scorecard with nothing behind it.
        cur.execute("savepoint sp")
        with pytest.raises(psycopg.errors.CheckViolation):
            cur.execute(
                "insert into answer_evaluations "
                "(session_id, turn_idx, dimension, score, evidence_quote) "
                "values (%s, 0, 'structuring', 3, '')",
                (session_id,),
            )
        cur.execute("rollback to savepoint sp")

        # score check: must be 1-4.
        cur.execute("savepoint sp")
        with pytest.raises(psycopg.errors.CheckViolation):
            cur.execute(
                "insert into answer_evaluations "
                "(session_id, turn_idx, dimension, score, evidence_quote) "
                "values (%s, 0, 'structuring', 7, 'candidate said the quiet part')",
                (session_id,),
            )
        cur.execute("rollback to savepoint sp")

        # unique (session_id, idx): what makes a replayed turn a conflict
        # rather than a silent duplicate when LangGraph re-runs a node.
        cur.execute(
            "insert into transcript_turns (session_id, idx, role, kind, content) "
            "values (%s, 0, 'interviewer', 'question', 'first')",
            (session_id,),
        )
        cur.execute("savepoint sp")
        with pytest.raises(psycopg.errors.UniqueViolation):
            cur.execute(
                "insert into transcript_turns (session_id, idx, role, kind, content) "
                "values (%s, 0, 'interviewer', 'question', 'duplicate')",
                (session_id,),
            )
        cur.execute("rollback to savepoint sp")

    conn.rollback()


def test_realtime_publication_matches_the_three_column_ui(conn: psycopg.Connection) -> None:
    """A table missing from this publication leaves the UI's middle column
    permanently empty, which reads as an agent bug rather than a missing
    publication membership.
    """
    with conn.cursor() as cur:
        cur.execute(
            "select tablename from pg_publication_tables "
            "where pubname = 'supabase_realtime' and schemaname = 'public'"
        )
        tables = {row[0] for row in cur.fetchall()}
    assert tables == {"transcript_turns", "answer_evaluations", "agent_events"}


def test_resumes_bucket_exists_and_is_private(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("select public from storage.buckets where id = 'resumes'")
        row = cur.fetchone()
    assert row is not None, "resumes bucket does not exist"
    assert row[0] is False, "resumes bucket is public; resumes are personal data"


def test_session_delete_cascades_to_transcript_turns(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute("insert into sessions (status) values ('created') returning id")
        (session_id,) = cur.fetchone()
        cur.execute(
            "insert into transcript_turns (session_id, idx, role, kind, content) "
            "values (%s, 0, 'interviewer', 'question', 'schema test turn')",
            (session_id,),
        )

        cur.execute("delete from sessions where id = %s", (session_id,))
        cur.execute("select count(*) from transcript_turns where session_id = %s", (session_id,))
        assert cur.fetchone()[0] == 0, "transcript_turns row survived its session's deletion"

    conn.rollback()
