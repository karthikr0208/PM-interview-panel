"""Applies backend/migrations/*.sql in filename order, over the session pooler.

Every migration is written to be idempotent, so this is safe to re-run and is
the only supported way to change the schema. Do not hand-edit tables in the
Supabase dashboard: story 0.8 deploys to Render, and a schema that exists only
as dashboard clicks cannot be recreated.

Distinct from scripts/init_db.py, which runs LangGraph's checkpointer.setup()
for its own tables. Neither runs on application startup.

Run:  python backend/scripts/migrate.py [--dry-run]
"""

from __future__ import annotations

import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402 — needs the path insert above

MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations"


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    files = sorted(MIGRATIONS.glob("*.sql"))
    if not files:
        sys.exit(f"no .sql files in {MIGRATIONS}")

    print(f"{len(files)} migration(s) in {MIGRATIONS}")
    for path in files:
        print(f"  {path.name}")
    if dry_run:
        print("\n--dry-run: nothing applied")
        return

    # autocommit=False: each migration is one transaction, so a failure
    # halfway leaves no partially-created schema behind.
    with psycopg.connect(settings.supabase_db_url, connect_timeout=15) as conn:
        for path in files:
            print(f"\napplying {path.name} ...", end=" ", flush=True)
            try:
                with conn.cursor() as cur:
                    cur.execute(path.read_text(encoding="utf-8"))
                conn.commit()
            except Exception as exc:  # noqa: BLE001 — reported, then re-raised
                conn.rollback()
                print("FAILED, rolled back")
                raise SystemExit(f"{path.name}: {type(exc).__name__}: {exc}") from exc
            print("ok")

    print("\nAll migrations applied.")


if __name__ == "__main__":
    main()
