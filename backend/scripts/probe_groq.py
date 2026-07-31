"""Probe the Groq endpoint: catalog, strict-schema support, and real rate limits.

Replaces the five archived NVIDIA-era probes (see archive/README.md). Answers the
three questions that actually decide a model assignment on this project:

  1. What models does this account see? (catalog, live, not documentation)
  2. Which of them accept a STRICT json_schema? This is the binding constraint —
     only openai/gpt-oss-* did on 2026-07-31; llama, qwen and compound all
     return 400 "This model does not support response format".
  3. What are the real rate limits? Read from x-ratelimit-* response headers,
     because the binding cap is TOKENS PER MINUTE, not requests.

Run:  backend/.venv/Scripts/python.exe backend/scripts/probe_groq.py
      backend/.venv/Scripts/python.exe backend/scripts/probe_groq.py --schema

--schema sends one real structured request per chat model. That costs requests
against a 1000/day budget, so it is opt-in rather than the default.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import httpx
from dotenv import dotenv_values
from pydantic import BaseModel

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
env = dotenv_values(ENV_PATH)

KEY = env["GROQ_API_KEY"]
BASE = env["GROQ_BASE_URL"]

# A User-Agent is required, not cosmetic: Groq sits behind Cloudflare, which
# answers a default urllib/httpx header set with `403 error code: 1010`
# (browser integrity check). That is indistinguishable from a rejected key by
# status alone. Cost this project a false "regenerate your key" once already.
HEADERS = {
    "Authorization": f"Bearer {KEY}",
    "User-Agent": "pm-interview-panel/probe_groq",
    "Content-Type": "application/json",
}

# Not chat models; they cannot answer any of the questions above.
SKIP = ("whisper", "tts", "guard", "embed", "distil", "orpheus")


class _Probe(BaseModel):
    """FLAT deliberately, and this is a correction worth keeping.

    The first version nested a sub-model, which made Pydantic emit `$defs` and
    a `$ref`. Groq's raw `response_format` rejects that with `invalid JSON
    schema for response_format: '/$defs/...'` even on the gpt-oss models that
    demonstrably DO support strict schemas. That produced a false negative
    against the very models this project runs on.

    The app never hits that path: `langchain-openai`'s `with_structured_output`
    resolves refs before sending, which is why the Resume Analyst's nested
    `ResumeAnalysis` works in production while this probe's did not. **Anything
    calling `response_format` directly with a nested Pydantic model must inline
    its `$defs` first.**
    """

    verdict: str
    quotes: list[str]
    note: str | None


def catalog() -> list[str]:
    resp = httpx.get(f"{BASE}/models", headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return sorted(m["id"] for m in resp.json()["data"])


def rate_limits(model: str) -> dict[str, str]:
    """Reads the limits off a real (tiny) completion. There is no headers-only
    endpoint, so this costs one request."""
    resp = httpx.post(
        f"{BASE}/chat/completions",
        headers=HEADERS,
        json={"model": model, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 5},
        timeout=60,
    )
    return {k: v for k, v in resp.headers.items() if "ratelimit" in k.lower()}


def _strict_schema() -> dict:
    """Pydantic's JSON Schema is not accepted by strict mode as-is.

    Two adjustments, both learned by watching this probe fail against models
    that provably work in the app:
      - `additionalProperties: false` is REQUIRED and Pydantic never emits it
      - `$defs`/`$ref` are rejected outright, which is why `_Probe` is flat

    `langchain-openai`'s `with_structured_output` does both for us, which is the
    whole reason the app's nested `ResumeAnalysis` works. Anything bypassing it
    and calling `response_format` directly has to do this itself.
    """
    schema = _Probe.model_json_schema()
    schema["additionalProperties"] = False
    return schema


def supports_strict_schema(model: str) -> tuple[bool, str]:
    started = time.perf_counter()
    resp = httpx.post(
        f"{BASE}/chat/completions",
        headers=HEADERS,
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": "Return the required JSON object."},
                {"role": "user", "content": "Quote two short phrases from: the quick brown fox."},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "Probe", "schema": _strict_schema(), "strict": True},
            },
            "max_tokens": 512,
        },
        timeout=120,
    )
    elapsed = time.perf_counter() - started
    if resp.status_code == 200:
        return True, f"{elapsed:5.1f}s"
    detail = resp.json().get("error", {}).get("message", "")[:60]
    return False, f"HTTP {resp.status_code} {detail}"


def main() -> int:
    models = catalog()
    print(f"=== CATALOG ({len(models)} models) ===")
    for m in models:
        print(f"  {m}")

    chat = [m for m in models if not any(s in m.lower() for s in SKIP)]

    print("\n=== RATE LIMITS (from x-ratelimit-* headers, not documentation) ===")
    print("    requests are per DAY: 2 consumed showing 2m52.8s to replenish")
    print("    means 86.4s each, and 86400/86.4 = 1000/day.")
    for m in chat:
        limits = rate_limits(m)
        req = limits.get("x-ratelimit-limit-requests", "?")
        tok = limits.get("x-ratelimit-limit-tokens", "?")
        print(f"  {m:34s} {req:>6} req   {tok:>6} tokens/min")
        time.sleep(1)

    if "--schema" not in sys.argv:
        print("\n(strict-schema check skipped; pass --schema to spend one request per model)")
        return 0

    print("\n=== STRICT JSON SCHEMA SUPPORT ===")
    print("    THE constraint that pins fast/deep. A model that fails here")
    print("    cannot run any structured agent in this product.")
    for m in chat:
        ok, detail = supports_strict_schema(m)
        print(f"  {m:34s} {'YES' if ok else 'no ':4s} {detail}")
        time.sleep(2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
