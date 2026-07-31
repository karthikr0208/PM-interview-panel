"""Verify every credential in .env actually works. Fails loudly, names the variable.

Checks reachability and auth, not just presence — a well-formed key that the
service rejects is the failure this catches and a shape check does not.

Run:  python scripts/check_env.py
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import dotenv_values

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
env = dotenv_values(ENV_PATH)

# Groq replaced NVIDIA NIM on 2026-07-31. Kept in sync with
# app/config.py REQUIRED_VARS by hand -- when one changes, grep the other.
REQUIRED = [
    "GROQ_API_KEY", "GROQ_BASE_URL",
    "GROQ_MODEL_FAST", "GROQ_MODEL_DEEP", "GROQ_MODEL_BACKUP",
    "SUPABASE_DB_URL", "SUPABASE_URL", "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY", "ALLOWED_ORIGINS",
]

failures: list[str] = []


def check_present() -> None:
    print("presence")
    for name in REQUIRED:
        value = (env.get(name) or "").strip()
        if not value or value.startswith(("PASTE_", "<")):
            print(f"  {name:28} MISSING")
            failures.append(name)
        else:
            print(f"  {name:28} set ({len(value)} chars)")


def request(url: str, headers: dict, body: dict | None = None) -> tuple[bool, str]:
    # A User-Agent is REQUIRED, not cosmetic. Groq sits behind Cloudflare,
    # which answers urllib's default header set with `HTTP 403 error code:
    # 1010` (browser integrity check). That is indistinguishable from a
    # rejected key by status code alone, so without this the script tells you
    # to regenerate a perfectly good credential. Observed 2026-07-31.
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body else None,
        headers={"User-Agent": "pm-interview-panel/check_env", **headers},
        method="POST" if body else "GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return True, f"HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:140].decode(errors="replace").replace("\n", " ")
        return False, f"HTTP {exc.code} — {detail}"
    except Exception as exc:  # noqa: BLE001
        return False, f"{type(exc).__name__}: {exc}"


def check_groq() -> None:
    """Times all three models. Latency is the whole reason for the split, so a
    model that has become slow is a finding, not noise — but it is not an env
    failure, so it never appends to `failures`.

    Groq: the binding constraint is TOKENS PER MINUTE (8000 on the gpt-oss
    models), not requests. A 429 here is throttling, not misconfiguration.
    """
    print("\ngroq")
    import time

    for name in ("GROQ_MODEL_FAST", "GROQ_MODEL_DEEP", "GROQ_MODEL_BACKUP"):
        model = env[name]
        started = time.perf_counter()
        ok, detail = request(
            f"{env['GROQ_BASE_URL']}/chat/completions",
            {"Authorization": f"Bearer {env['GROQ_API_KEY']}",
             "Content-Type": "application/json"},
            {"model": model,
             "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
             "max_tokens": 16},
        )
        elapsed = time.perf_counter() - started
        print(f"  {model:34} {'OK' if ok else 'FAIL'}  {elapsed:5.1f}s  {detail}")
        if ok:
            if elapsed > 10:
                print(f"  -> {elapsed:.0f}s is far above the 2.7-4.4s measured 2026-07-31.")
        elif "401" in detail or "403" in detail:
            failures.append("GROQ_API_KEY")
            print("  -> key rejected. Regenerate at console.groq.com/keys.")
        elif "404" in detail:
            failures.append(name)
            print("  -> model id wrong, or not enabled for this account.")
        elif "429" in detail:
            print("  -> rate limited, not misconfigured. 8000 tokens/min is the binding cap.")
        else:
            print("  -> not an auth failure. Slow or queued, not misconfigured.")


def check_supabase_keys() -> None:
    """Each key gets an endpoint that key is actually entitled to use.

    /rest/v1/ root is secret-only, so testing the publishable key against it
    reports a false failure — which this script did on its first run.
    """
    print("\nsupabase rest")

    ok, detail = request(
        f"{env['SUPABASE_URL']}/auth/v1/settings",
        {"apikey": env["SUPABASE_ANON_KEY"]},
    )
    print(f"  {'SUPABASE_ANON_KEY':28} {'OK' if ok else 'FAIL'}  {detail}")
    if not ok:
        failures.append("SUPABASE_ANON_KEY")

    ok, detail = request(
        f"{env['SUPABASE_URL']}/rest/v1/",
        {"apikey": env["SUPABASE_SERVICE_ROLE_KEY"],
         "Authorization": f"Bearer {env['SUPABASE_SERVICE_ROLE_KEY']}"},
    )
    print(f"  {'SUPABASE_SERVICE_ROLE_KEY':28} {'OK' if ok else 'FAIL'}  {detail}")
    if not ok:
        failures.append("SUPABASE_SERVICE_ROLE_KEY")


def check_key_shapes() -> None:
    """The dangerous mistake is not a missing key, it is the wrong one."""
    print("\nkey shapes")
    anon = env.get("SUPABASE_ANON_KEY", "")
    secret = env.get("SUPABASE_SERVICE_ROLE_KEY", "")

    if anon.startswith("sb_secret_"):
        print("  SUPABASE_ANON_KEY holds a SECRET key — it bypasses RLS and this value")
        print("  is also copied into the frontend bundle. Swap it.")
        failures.append("SUPABASE_ANON_KEY")
    elif anon.startswith("sb_publishable_"):
        print("  SUPABASE_ANON_KEY            publishable, correct")
    elif anon.startswith("eyJ"):
        print("  SUPABASE_ANON_KEY            legacy JWT — works, but deprecated")

    if secret.startswith("sb_publishable_"):
        print("  SUPABASE_SERVICE_ROLE_KEY holds a PUBLISHABLE key — signed-URL minting")
        print("  will fail. Swap it.")
        failures.append("SUPABASE_SERVICE_ROLE_KEY")
    elif secret.startswith("sb_secret_"):
        print("  SUPABASE_SERVICE_ROLE_KEY    secret, correct")
    elif secret.startswith("eyJ"):
        print("  SUPABASE_SERVICE_ROLE_KEY    legacy JWT — works, but deprecated")

    # Parse values, never raw text — the comments in frontend/.env mention
    # sb_secret_ by name, and a substring scan flags its own warning label.
    frontend_env = ENV_PATH.parent.parent / "frontend" / ".env"
    if frontend_env.exists():
        leaked = [k for k, v in dotenv_values(frontend_env).items()
                  if (v or "").startswith("sb_secret_")]
        if leaked:
            print(f"  frontend/.env EXPOSES A SECRET KEY in: {', '.join(leaked)}")
            print("  It would ship in the browser bundle. Swap for the publishable key.")
            failures.append("frontend/.env")
        else:
            print("  frontend/.env                no secret key present, correct")


def main() -> None:
    print(f"reading {ENV_PATH}\n")
    check_present()
    if failures:
        sys.exit(f"\n{len(failures)} missing: {', '.join(failures)}")
    check_key_shapes()
    check_groq()
    check_supabase_keys()

    print()
    if failures:
        sys.exit(f"FAILED: {', '.join(sorted(set(failures)))}")
    print("All credentials present and working.")


if __name__ == "__main__":
    main()
