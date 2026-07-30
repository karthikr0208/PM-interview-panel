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

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config import settings


async def main() -> None:
    print(f"Connecting to {settings.supabase_db_url.split('@')[-1]} (session pooler)...")
    async with AsyncPostgresSaver.from_conn_string(settings.supabase_db_url) as checkpointer:
        await checkpointer.setup()
    print("checkpointer.setup() complete — checkpoints / checkpoint_writes / "
          "checkpoint_blobs tables exist (or already did; this is idempotent).")


if __name__ == "__main__":
    asyncio.run(main())
