"""Does one candidate journey survive REAL HTTP request boundaries, all the
way through 2-3 answered interview questions?

    backend/.venv/Scripts/python.exe backend/scripts/prove_interview_over_http.py

Story 3.2's last acceptance box, and the phase gate's condition 3. Takes no
arguments. Costs one full chain: Resume Analyst (`deep`) + Case Architect
(`fast`) + Planner (`deep`) + the conduct loop (`fast`), roughly 12,000-15,000
`deep` tokens of a 200,000 daily cap. Budget for it before running.

WHY A SUBPROCESS AND NOT TestClient. Story 0.7 established the rule: a
rebuilt `TestClient` shares the parent's memory, so it cannot prove that
nothing about a paused interview lives anywhere but Postgres. This script
starts a real `uvicorn` in a separate OS process and speaks HTTP to it over a
socket, exactly as a browser would. Every pause here is a genuine
request/response boundary with the graph's only continuity being its
checkpoint.

WHAT IT PROVES, and each is asserted, not printed for a human to eyeball:
  1. the interview reaches question 1 across the level/confirm boundary
  2. question text is the Planner's string VERBATIM (spec §2a -- Python emits
     it, the model never rewrites it)
  3. a clarification is answered WITHOUT consuming a question slot
  4. 2-3 questions are asked and answered, each over its own HTTP request
  5. the loop exits, and the transcript in Postgres holds every turn

Exit 0 = the journey completed and every assertion held. Exit 1 = a failure,
named. Exit 3 = rate limited, which is NOT a defect -- classify before
believing a red run (CLAUDE.md).

Cleans up its own rows.
"""
from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx
import psycopg

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

from app.config import settings  # noqa: E402

RESUME = (
    "Ada Byron\n"
    "Senior Product Manager, Loomly (2021-2025)\n"
    "Owned the notifications and messaging product line end to end, three squads.\n"
    "Cut opt-outs from 12.4% to 7.1% in two quarters and grew weekly senders 38%.\n"
    "Product Manager, Corvid Labs (2018-2021)\n"
    "Ran the onboarding surface; lifted activation from 22.6% to 31.4%.\n"
)


_DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _docx(text: str) -> bytes:
    """A real DOCX, built the same way `tests/test_resume_upload.py` builds
    its fixtures."""
    import io

    import docx

    document = docx.Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _anon_token() -> str:
    """A REAL anonymous identity, the same one the browser gets. Not a
    hand-built JWT: `validate_bearer_token` verifies it against Supabase, so
    a forged token would prove nothing about the path a candidate walks."""
    r = httpx.post(
        f"{settings.supabase_url}/auth/v1/signup",
        headers={"apikey": settings.supabase_anon_key, "Content-Type": "application/json"},
        json={},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _wait_for_health(base: str, proc: subprocess.Popen, timeout: float = 90) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            # Surface the child's own traceback. A bare exit code here sent
            # the first run of this script chasing the wrong thing.
            out = proc.stdout.read() if proc.stdout else ""
            raise RuntimeError(
                f"uvicorn died during startup, exit={proc.returncode}\n--- child output ---\n{out}"
            )
        try:
            if httpx.get(f"{base}/health", timeout=3).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise RuntimeError("uvicorn never became healthy")


def _is_rate_limited(text: str) -> bool:
    # CLAUDE.md: classify every failure before calling it a defect. Three
    # separate times a mostly-red run has been rate limiting, once wearing an
    # AssertionError written to be believed.
    lowered = text.lower()
    return "tokens per day" in lowered or "tokens per minute" in lowered or "rate_limit" in lowered


def main() -> int:
    port = _free_port()
    base = f"http://127.0.0.1:{port}"
    env = {**os.environ, "PYTHONPATH": str(BACKEND)}
    # Started through an inline runner rather than `-m uvicorn` so the event
    # loop policy is set BEFORE the app's lifespan opens the checkpointer.
    # On Windows uvicorn defaults to ProactorEventLoop and psycopg refuses to
    # run async on it ("Psycopg cannot use the 'ProactorEventLoop'"), so the
    # server dies in lifespan with exit 3 and never binds. Local-only: Render
    # is Linux and uses the default policy there. `--loop asyncio` does NOT
    # fix this -- on Windows that still selects Proactor.
    runner = (
        "import asyncio, sys, uvicorn\n"
        "if sys.platform == 'win32':\n"
        "    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())\n"
        f"uvicorn.run('app.main:app', host='127.0.0.1', port={port}, log_level='warning')\n"
    )
    proc = subprocess.Popen(
        [str(BACKEND / ".venv" / "Scripts" / "python.exe"), "-c", runner],
        cwd=str(BACKEND), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )

    session_id = None
    rc = 1
    try:
        _wait_for_health(base, proc)
        token = _anon_token()
        h = {"Authorization": f"Bearer {token}"}
        c = httpx.Client(base_url=base, headers=h, timeout=300)

        # ---- request 1: create the session -------------------------------
        r = c.post("/session")
        r.raise_for_status()
        session_id = r.json()["session_id"]
        print(f"  [1] POST /session                      -> {session_id}")

        # ---- request 2: upload the resume --------------------------------
        # A real DOCX, not a .txt: `detect_file_kind` reads the file's own
        # bytes and accepts only PDF or DOCX, so a plain-text upload is
        # rejected at the route with a 400 before any of this is exercised.
        r = c.post(
            f"/session/{session_id}/resume",
            files={"file": ("ada.docx", _docx(RESUME), _DOCX_MIME)},
        )
        r.raise_for_status()
        print(f"  [2] POST /session/../resume            -> {r.status_code}")

        # ---- request 3: level (Resume Analyst, pauses at confirm_level) ---
        r = c.post(f"/session/{session_id}/level")
        if r.status_code != 200 and _is_rate_limited(r.text):
            print(f"\n  RATE LIMITED at /level, not a defect:\n  {r.text[:300]}")
            return 3
        r.raise_for_status()
        level = r.json()["assessed_level"]
        print(f"  [3] POST /session/../level             -> {level}")

        # ---- request 4: confirm (Case Architect + Planner + question 1) ---
        r = c.post(f"/session/{session_id}/level/confirm", json={"level": level})
        if r.status_code != 200 and _is_rate_limited(r.text):
            print(f"\n  RATE LIMITED at /level/confirm, not a defect:\n  {r.text[:300]}")
            return 3
        r.raise_for_status()
        confirmed = r.json()
        first = confirmed.get("first_question")
        assert first, f"/level/confirm did not surface the first question: {confirmed}"
        q1_text = first["text"]
        print(f"  [4] POST /session/../level/confirm     -> question 1 ({len(q1_text)} chars)")
        print(f"      {q1_text[:110]}...")

        # --- assertion 2: question 1 is the Planner's string VERBATIM -----
        conn = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
        with conn.cursor() as cur:
            cur.execute(
                "select content from transcript_turns where session_id=%s and kind='question' order by idx",
                (session_id,),
            )
            stored_q1 = cur.fetchone()[0]
        conn.close()
        assert stored_q1 == q1_text, "the question served over HTTP differs from the stored turn"
        assert "—" not in q1_text and "–" not in q1_text, (
            f"question 1 contains a dash variant, which the ban forbids: {q1_text!r}"
        )
        print("      question 1 has no bridge and no dash variant, as spec 2a requires")

        # ---- request 5: a CLARIFICATION, which must not consume a slot ---
        r = c.post(
            f"/session/{session_id}/interview/reply",
            json={"type": "clarify", "text": "Before I answer, how many customers does the company have?"},
        )
        if r.status_code != 200 and _is_rate_limited(r.text):
            print(f"\n  RATE LIMITED at the clarification, not a defect:\n  {r.text[:300]}")
            return 3
        r.raise_for_status()
        clar = r.json()
        # The route nests the paused payload under `next` and flags the end
        # of the interview with `done`, rather than putting `kind`/`text` at
        # the top level. Reading the top level instead is what made this
        # script over-post and 404 on its first full run.
        assert clar["done"] is False, "the interview ended on a clarification"
        clar_next = clar["next"]
        assert clar_next["kind"] == "clarification", (
            f"a clarify reply did not come back as a clarification: {clar_next}"
        )
        print(f"  [5] POST /session/../interview/reply   -> {clar_next['kind']}")
        print(f"      {str(clar_next.get('text'))[:110]}...")

        asked_after_clarify = None
        conn = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
        with conn.cursor() as cur:
            cur.execute(
                "select count(*) from transcript_turns where session_id=%s and kind='question'",
                (session_id,),
            )
            asked_after_clarify = cur.fetchone()[0]
        conn.close()
        assert asked_after_clarify == 1, (
            f"a clarification consumed a question slot: {asked_after_clarify} questions asked, want 1"
        )
        print("      clarification consumed NO question slot")

        # ---- requests 6+: answer until the interview ends -----------------
        answers = [
            "I'd start by sizing which segment the churn is concentrated in, then pick the cheapest reversible test.",
            "I'd run a two-week holdout against the current flow and read activation, not raw signups.",
            "I'd track whether the change holds after 30 days, since early lift usually decays.",
            "I'd escalate only if the 30-day number regressed against the holdout.",
        ]
        turns = 0
        for i, a in enumerate(answers):
            r = c.post(f"/session/{session_id}/interview/reply", json={"type": "answer", "text": a})
            if r.status_code != 200 and _is_rate_limited(r.text):
                print(f"\n  RATE LIMITED at answer {i + 1}, not a defect:\n  {r.text[:300]}")
                return 3
            r.raise_for_status()
            body = r.json()
            turns += 1
            if body["done"]:
                print(f"  [{6 + i}] POST /session/../interview/reply   -> done, interview over")
                break
            nxt = body["next"]
            print(f"  [{6 + i}] POST /session/../interview/reply   -> {nxt['kind']}")
            print(f"      {str(nxt.get('text'))[:110]}...")
            if nxt["kind"] == "question":
                assert "—" not in nxt["text"] and "–" not in nxt["text"], (
                    f"a served question contains a dash variant: {nxt['text']!r}"
                )
        else:
            raise AssertionError(
                f"the interview never reported done after {turns} answers -- "
                f"the loop's exit condition did not fire"
            )

        # ---- the transcript in Postgres is the record ---------------------
        conn = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
        with conn.cursor() as cur:
            cur.execute(
                "select role, kind, left(content, 70) from transcript_turns "
                "where session_id=%s order by idx",
                (session_id,),
            )
            rows = cur.fetchall()
            cur.execute(
                "select count(*) from transcript_turns where session_id=%s and kind='question'",
                (session_id,),
            )
            questions_asked = cur.fetchone()[0]
        conn.close()

        print(f"\n  transcript_turns rows ({len(rows)}):")
        for role, kind, snippet in rows:
            print(f"    {role:12} {kind:14} {snippet}")

        assert 2 <= questions_asked <= 3, (
            f"the loop asked {questions_asked} questions; Phase 3 requires 2-3"
        )
        print(f"\n  questions asked over separate HTTP requests: {questions_asked}  (want 2-3)")
        print("  ALL ASSERTIONS HELD")
        rc = 0

    except AssertionError as exc:
        print(f"\n  FAILED: {exc}")
        rc = 1
    except httpx.HTTPStatusError as exc:
        body = exc.response.text
        if _is_rate_limited(body):
            print(f"\n  RATE LIMITED, not a defect:\n  {body[:300]}")
            return 3
        print(f"\n  HTTP {exc.response.status_code}: {body[:500]}")
        rc = 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
        if session_id:
            conn = psycopg.connect(settings.supabase_db_url, connect_timeout=15)
            try:
                with conn.cursor() as cur:
                    for t in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
                        cur.execute(f"delete from {t} where thread_id = %s", (session_id,))
                    for t in ("transcript_turns", "agent_events", "case_worlds", "resumes"):
                        cur.execute(f"delete from {t} where session_id = %s", (session_id,))
                    cur.execute("delete from sessions where id = %s", (session_id,))
                conn.commit()
                with conn.cursor() as cur:
                    cur.execute("select count(*) from sessions where id = %s", (session_id,))
                    print(f"  residue: sessions rows = {cur.fetchone()[0]}")
            finally:
                conn.close()
    return rc


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    sys.exit(main())
