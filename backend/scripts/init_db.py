"""Run LangGraph's `checkpointer.setup()` — creates the `checkpoints`,
`checkpoint_writes`, and `checkpoint_blobs` tables in Supabase.

Run exactly ONCE, by hand:  python backend/scripts/init_db.py

NEVER called from application startup (`app/main.py`). `.setup()` is a schema
migration, not a runtime dependency check — running it on every boot means
every Render cold start would race a schema migration against live traffic.
It is idempotent (safe to run a second time by accident), but "safe to rerun"
is not the same as "belongs in the request path".

Connects over the SESSION POOLER, port 5432 — see CLAUDE.md. The transaction
pooler (6543) will connect but breaks LangGraph's own prepared statements the
same way it breaks the app's.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# Runnable from the repo root, which is how CLAUDE.md documents it. Without
# this the import resolves only when cwd is backend/.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402 — needs the path insert above


# Windows only, and local development only. Python 3.8+ defaults to
# ProactorEventLoop on Windows, which psycopg's async mode refuses:
#   InterfaceError: Psycopg cannot use the 'ProactorEventLoop' to run in async mode
# Render runs Linux, where the selector loop is already the default, so this
# is invisible in production. Anything using AsyncPostgresSaver locally on
# Windows needs it — see DEV-STATE § Environment notes.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# LangGraph creates its tables WITHOUT row level security, in `public`, which
# Supabase exposes through the Data API — and anon/authenticated hold default
# grants there. Measured 2026-07-30 before this fix: `set role anon; select
# count(*) from checkpoints` SUCCEEDED, and anon also held INSERT, UPDATE,
# DELETE and TRUNCATE.
#
# Checkpoints hold the entire interview state: resume text, full transcript,
# every evaluation. So this was both a total read exposure and a route to
# destroying in-progress interviews.
#
# Secured here rather than in a migration because ordering would otherwise be
# a trap: migrate.py can run before these tables exist, silently no-op, and
# leave them unprotected forever. They are created and secured in one step.
#
# Pattern-matched rather than hardcoded so a table added by a future LangGraph
# version is covered too, instead of being quietly missed.
SECURE_CHECKPOINT_TABLES = """
do $$
declare t text;
begin
  for t in
    select tablename from pg_tables
    where schemaname = 'public' and tablename like 'checkpoint%' and not rowsecurity
  loop
    execute format('alter table public.%I enable row level security', t);
  end loop;
end $$;
"""

# Reports resulting state rather than what the DO block claims to have done.
# A report derived from the actual catalog cannot drift from reality.
VERIFY_RLS = """
select tablename, rowsecurity from pg_tables
where schemaname = 'public' and tablename like 'checkpoint%'
order by tablename
"""


async def main() -> None:
    print(f"Connecting to {settings.supabase_db_url.split('@')[-1]} (session pooler)...")
    async with AsyncPostgresSaver.from_conn_string(settings.supabase_db_url) as checkpointer:
        await checkpointer.setup()
        # No policies, matching the app tables: RLS with zero policies denies
        # every role that does not bypass it. The backend's role bypasses, so
        # LangGraph is unaffected; browsers get nothing.
        async with checkpointer.conn.cursor() as cur:
            await cur.execute(SECURE_CHECKPOINT_TABLES)
            await cur.execute(VERIFY_RLS)
            # AsyncPostgresSaver sets a dict_row factory on its connection, so
            # rows are mappings, not tuples. Unpacking them as tuples yields
            # the column NAMES, which are truthy and make the check below pass
            # against a table that has no RLS at all.
            rls = [(r["tablename"], r["rowsecurity"]) for r in await cur.fetchall()]

    # ASCII only: the Windows console default codepage mangles non-ASCII here.
    print("checkpointer.setup() complete. checkpoint tables exist "
          "(or already did; this is idempotent).")
    for name, enabled in rls:
        print(f"  {name:24} rls={enabled}")

    unprotected = [name for name, enabled in rls if not enabled]
    if unprotected or not rls:
        raise SystemExit(f"FAILED: no RLS on {unprotected or 'any checkpoint table (none found)'}")


if __name__ == "__main__":
    asyncio.run(main())
