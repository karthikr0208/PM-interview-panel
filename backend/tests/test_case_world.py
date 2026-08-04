"""`case_world` is written exactly once, and a second write is REJECTED.

PHASE-2-SPEC.md §2.3 requires this to be falsifiable rather than asserted by
comment, on story 0.6's precedent: "an immutability rule nobody has watched
reject a write is a comment."

Until 2026-08-04 it was neither enforced nor tested. `0001_initial_schema.sql`
said so in its own words -- "Nothing enforces that in the database; it is a
graph-level invariant" -- and there was no state guard and no test either, so a
second insert would simply have succeeded and left two worlds for one session,
with whichever row a later `select` happened to return winning.
`0003_case_world_write_once.sql` adds the unique index these tests exercise.

Why it matters beyond tidiness: `case_world` is what stops the Interviewer
contradicting itself forty minutes in (ARCHITECTURE §2). These are generative
agents, so a second write would not merely duplicate the first, it would
disagree with it, and the audit copy would diverge from the working copy in
graph state.

No LLM calls anywhere in this file. It is `live` only because it needs the
database.
"""

from __future__ import annotations

import json
import uuid
from typing import Iterator

import psycopg
import pytest

pytestmark = pytest.mark.live


_WORLD = {
    "company": {
        "name": "Harbour Quill",
        "one_line": "Compliance tooling for mid-market lenders",
        "stage": "series_b",
        "employees": 180,
        "founded_year": 2017,
    },
    "supporting_facts": ["The enterprise tier is 61.4% of revenue but 12.1% of logos."],
}


@pytest.fixture
def session_id(conn: psycopg.Connection) -> Iterator[str]:
    """One throwaway `sessions` row, deleted in teardown.

    `case_worlds.session_id` is a foreign key, so the write-once check cannot
    be run against an invented uuid -- it would fail on the FK and look like a
    passing uniqueness test for entirely the wrong reason.
    """
    new_id = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute("insert into sessions (id) values (%s)", (new_id,))
    conn.commit()
    yield new_id
    with conn.cursor() as cur:
        # case_worlds cascades from sessions, so this clears both.
        cur.execute("delete from sessions where id = %s", (new_id,))
    conn.commit()


def _insert_world(conn: psycopg.Connection, session_id: str, world: dict) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "insert into case_worlds (session_id, world) values (%s, %s)",
            (session_id, json.dumps(world)),
        )


def test_the_first_case_world_write_succeeds(
    conn: psycopg.Connection, session_id: str
) -> None:
    """The positive control. Without it, a constraint that rejected EVERY
    write would pass the rejection test below and look like working
    immutability."""
    _insert_world(conn, session_id, _WORLD)
    conn.commit()

    with conn.cursor() as cur:
        cur.execute("select count(*) from case_worlds where session_id = %s", (session_id,))
        assert cur.fetchone()[0] == 1


def test_a_second_case_world_write_is_rejected(
    conn: psycopg.Connection, session_id: str
) -> None:
    """🔴 THE FALSIFICATION. The write-once rule is watched rejecting a write.

    A DIFFERENT world is used for the second insert, because that is the real
    hazard: a re-running `generate_case_world` node calls a generative agent
    again and gets back something that does not match what every downstream
    agent has already been told.
    """
    _insert_world(conn, session_id, _WORLD)
    conn.commit()

    second = {**_WORLD, "company": {**_WORLD["company"], "name": "Different Company"}}
    with pytest.raises(psycopg.errors.UniqueViolation):
        _insert_world(conn, session_id, second)
    conn.rollback()

    with conn.cursor() as cur:
        cur.execute(
            "select world -> 'company' ->> 'name' from case_worlds where session_id = %s",
            (session_id,),
        )
        rows = cur.fetchall()
    assert len(rows) == 1, f"expected exactly one world after a rejected write, got {rows}"
    assert rows[0][0] == "Harbour Quill", "the rejected write must not have overwritten the first"


def test_two_different_sessions_each_get_their_own_world(
    conn: psycopg.Connection, session_id: str
) -> None:
    """The constraint must be per-session, not global. A unique index on the
    wrong column would pass both tests above while making the product
    single-use."""
    other_id = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute("insert into sessions (id) values (%s)", (other_id,))
    conn.commit()
    try:
        _insert_world(conn, session_id, _WORLD)
        _insert_world(conn, other_id, _WORLD)
        conn.commit()

        with conn.cursor() as cur:
            cur.execute(
                "select count(*) from case_worlds where session_id in (%s, %s)",
                (session_id, other_id),
            )
            assert cur.fetchone()[0] == 2
    finally:
        with conn.cursor() as cur:
            cur.execute("delete from sessions where id = %s", (other_id,))
        conn.commit()
