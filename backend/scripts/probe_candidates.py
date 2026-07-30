"""Pick the production model on evidence: latency first, then structured output.

Latency is the gate. GLM 5.2 is capable but sits behind a ~230s queue on the free
tier, which makes it unusable for a conversational product regardless of how good
it is. Structured output is the second gate — every agent in this system depends
on it.

Run:  python scripts/probe_candidates.py
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import dotenv_values

env = dotenv_values(Path(__file__).resolve().parent.parent / ".env")
KEY, BASE = env["NVIDIA_API_KEY"], env["NVIDIA_BASE_URL"]

LATENCY_TIMEOUT = 45
SCHEMA_TIMEOUT = 90

CANDIDATES = [
    "nvidia/nemotron-3-nano-30b-a3b",
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/nemotron-3-ultra-550b-a55b",
    "nvidia/llama-3.3-nemotron-super-49b-v1.5",
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "deepseek-ai/deepseek-v4-flash",
    "mistralai/mistral-medium-3.5-128b",
    "google/gemma-4-31b-it",
    "moonshotai/kimi-k2.6",
]

# Deliberately shaped like the Resume Analyst's real output.
SCHEMA = {
    "type": "object",
    "properties": {
        "level": {"type": "string", "enum": ["APM", "PM", "Senior PM", "GPM"]},
        "years_experience": {"type": "integer"},
        "rationale": {"type": "string"},
    },
    "required": ["level", "years_experience", "rationale"],
    "additionalProperties": False,
}

RESUME = ("Priya Raghunathan. 7 years PM. Senior PM at a B2B logistics marketplace, "
          "owns carrier-matching, 12 engineers, $4.7M ARR influenced.")


def call(body: dict, timeout: int) -> tuple[bool, float, str]:
    req = urllib.request.Request(
        f"{BASE}/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        method="POST")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
        return True, time.perf_counter() - started, \
            data["choices"][0]["message"].get("content") or ""
    except urllib.error.HTTPError as exc:
        return False, time.perf_counter() - started, \
            f"HTTP {exc.code} {exc.read()[:70].decode(errors='replace')}"
    except Exception as exc:  # noqa: BLE001
        return False, time.perf_counter() - started, f"{type(exc).__name__}"


def main() -> None:
    print(f"latency gate (timeout {LATENCY_TIMEOUT}s)\n")
    fast: list[tuple[str, float]] = []

    for model in CANDIDATES:
        ok, elapsed, detail = call(
            {"model": model,
             "messages": [{"role": "user", "content": "Reply with one word: ok"}],
             "max_tokens": 8}, LATENCY_TIMEOUT)
        if ok and elapsed < 15:
            print(f"  {model:44} {elapsed:6.1f}s  PASS")
            fast.append((model, elapsed))
        elif ok:
            print(f"  {model:44} {elapsed:6.1f}s  too slow")
        else:
            print(f"  {model:44} {elapsed:6.1f}s  {detail}")

    if not fast:
        print("\nNo model passed the latency gate.")
        return

    print(f"\nstructured output gate (timeout {SCHEMA_TIMEOUT}s)\n")
    for model, latency in fast:
        ok, elapsed, content = call(
            {"model": model,
             "messages": [
                 {"role": "system", "content": "Return only JSON matching the schema."},
                 {"role": "user", "content": f"Level this candidate:\n{RESUME}"}],
             "max_tokens": 512,
             "response_format": {"type": "json_schema",
                                 "json_schema": {"name": "level", "schema": SCHEMA,
                                                 "strict": True}}},
            SCHEMA_TIMEOUT)
        if not ok:
            print(f"  {model:44} json_schema unsupported — {content}")
            continue
        try:
            parsed = json.loads(content)
            missing = [k for k in SCHEMA["required"] if k not in parsed]
            verdict = "VALID" if not missing else f"missing {missing}"
            print(f"  {model:44} {elapsed:6.1f}s  {verdict}  {parsed.get('level')!r}")
        except json.JSONDecodeError:
            print(f"  {model:44} {elapsed:6.1f}s  NOT JSON — {content[:60]!r}")

    print("\nchat latency (fastest first):")
    for model, latency in sorted(fast, key=lambda x: x[1]):
        print(f"  {latency:6.1f}s  {model}")


if __name__ == "__main__":
    main()
