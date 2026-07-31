"""Structured output, tested fairly.

The first attempt at this used max_tokens=512 (truncating JSON mid-string) and left
reasoning enabled (so chain-of-thought landed in `content` ahead of the JSON). Both
produced false failures. This version gives room, disables reasoning where supported,
and extracts JSON the way production code would.

Reports three separate things, because they have different fixes:
  strict   — response_format json_schema accepted and returned clean JSON
  lenient  — JSON recoverable after stripping fences/prose (needs an extractor)
  fail     — no usable JSON

Run:  python scripts/probe_structured.py
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import dotenv_values

env = dotenv_values(Path(__file__).resolve().parent.parent / ".env")
KEY, BASE = env["NVIDIA_API_KEY"], env["NVIDIA_BASE_URL"]
TIMEOUT = 120
TRIALS = 3

CANDIDATES = [
    "nvidia/nemotron-3-nano-30b-a3b",
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/llama-3.3-nemotron-super-49b-v1.5",
    "openai/gpt-oss-20b",
]

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

FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.S)


def extract(text: str) -> dict | None:
    """What a production fallback parser would do."""
    for candidate in (text, *(m.group(1) for m in FENCE.finditer(text))):
        candidate = candidate.strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    return None


def call(model: str, use_schema: bool) -> tuple[str | None, float, str]:
    body = {
        "model": model,
        "messages": [
            {"role": "system",
             "content": "You output only JSON. No prose, no code fences, no reasoning."},
            {"role": "user",
             "content": f"Level this PM candidate as JSON with keys level, "
                        f"years_experience, rationale:\n\n{RESUME}"}],
        "max_tokens": 3000,
        "temperature": 0,
    }
    # `thinking` is GLM-specific — the Nemotron 3 family rejects it with a 400.
    # Reasoning control is per-family, not a portable OpenAI parameter.
    if model.startswith("z-ai/"):
        body["thinking"] = {"type": "disabled"}
    if use_schema:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": "candidate_level", "schema": SCHEMA, "strict": True}}

    req = urllib.request.Request(
        f"{BASE}/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
        method="POST")
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.load(resp)
        msg = data["choices"][0]["message"]
        return (msg.get("content") or ""), time.perf_counter() - started, ""
    except urllib.error.HTTPError as exc:
        return None, time.perf_counter() - started, \
            f"HTTP {exc.code} {exc.read()[:80].decode(errors='replace')}"
    except Exception as exc:  # noqa: BLE001
        return None, time.perf_counter() - started, type(exc).__name__


def score(model: str, use_schema: bool) -> None:
    strict = lenient = failed = 0
    latencies: list[float] = []
    note = ""

    for _ in range(TRIALS):
        content, elapsed, err = call(model, use_schema)
        latencies.append(elapsed)
        if content is None:
            failed += 1
            note = err
            continue
        try:
            parsed = json.loads(content.strip())
            if all(k in parsed for k in SCHEMA["required"]):
                strict += 1
                continue
        except json.JSONDecodeError:
            pass
        parsed = extract(content)
        if parsed and all(k in parsed for k in SCHEMA["required"]):
            lenient += 1
        else:
            failed += 1
            if not note:
                note = repr((content or "")[:70])

    mode = "json_schema" if use_schema else "prompt-only"
    avg = sum(latencies) / len(latencies)
    print(f"  {model:42} {mode:12} {avg:6.1f}s  "
          f"strict {strict}/{TRIALS}  lenient {lenient}/{TRIALS}  fail {failed}/{TRIALS}"
          f"{'  ' + note if note else ''}")


if __name__ == "__main__":
    print(f"{TRIALS} trials per model per mode, max_tokens 3000, thinking disabled\n")
    for model in CANDIDATES:
        score(model, use_schema=True)
        score(model, use_schema=False)
        print()
