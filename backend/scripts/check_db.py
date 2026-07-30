"""Prove SUPABASE_DB_URL actually authenticates, and diagnose it when it doesn't.

Three failure modes look similar from a stack trace but need different fixes:

  - wrong host prefix   -> "Tenant or user not found"    -> swap aws-0- for aws-1-
  - wrong password      -> "password authentication failed"
  - transaction pooler  -> connects, then DuplicatePreparedStatement later

Never prints the password. Run:  python scripts/check_db.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values

env = dotenv_values(Path(__file__).resolve().parent.parent / ".env")
url = (env.get("SUPABASE_DB_URL") or "").strip()

if not url or "<PASSWORD>" in url:
    sys.exit("SUPABASE_DB_URL is missing or still contains <PASSWORD>.")

parts = urlsplit(url)
host, port = parts.hostname or "", parts.port or 0
redacted = re.sub(r"://([^:]+):[^@]+@", r"://\1:****@", url)
print(f"URL:  {redacted}")

# Static checks first — cheaper than a network round trip, and catch the
# two mistakes that are silent until much later.
problems: list[str] = []
if port == 6543:
    problems.append("Port 6543 is the TRANSACTION pooler. It connects fine, then breaks "
                    "LangGraph's checkpointer with DuplicatePreparedStatement. Use 5432.")
if "pooler.supabase.com" not in host:
    problems.append(f"Host '{host}' is not a pooler. The direct connection is IPv6-only "
                    "and unreachable from Render's free tier.")
if problems:
    for p in problems:
        print(f"\n  PROBLEM: {p}")
    sys.exit(1)

print(f"Host: {host}  port {port}  (session pooler, correct)\n")

import psycopg  # noqa: E402  — imported after the cheap checks

try:
    with psycopg.connect(url, connect_timeout=15) as conn:
        with conn.cursor() as cur:
            cur.execute("select current_database(), current_user, version()")
            db, user, version = cur.fetchone()
            cur.execute("select count(*) from information_schema.tables "
                        "where table_schema = 'public'")
            (table_count,) = cur.fetchone()

    print("CONNECTED")
    print(f"  database:     {db}")
    print(f"  user:         {user}")
    print(f"  postgres:     {version.split(',')[0]}")
    print(f"  public tables: {table_count}  "
          f"{'(empty, as expected before story 0.4)' if table_count == 0 else ''}")
    print("\nThe Sydney project is now safe to delete.")

except psycopg.OperationalError as exc:
    msg = str(exc)
    print(f"FAILED\n  {msg.strip()}\n")
    if "Tenant or user not found" in msg:
        print("  DIAGNOSIS: wrong pooler host for this project.\n"
              "  FIX: swap aws-0- for aws-1- in SUPABASE_DB_URL. The password is fine.")
    elif "password authentication failed" in msg:
        print("  DIAGNOSIS: host is right, password is wrong.\n"
              "  FIX: reset it in Project Settings -> Database. Letters and digits only —\n"
              "       @ : / # in a password break URL parsing before it is ever sent.")
    elif "timeout" in msg.lower() or "could not translate" in msg.lower():
        print("  DIAGNOSIS: cannot reach the host at all.\n"
              "  FIX: check the region in the hostname, and that the project is not paused.")
    else:
        print("  DIAGNOSIS: unrecognised. Paste the error above into the chat.")
    sys.exit(1)
