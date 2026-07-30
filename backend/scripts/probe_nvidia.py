"""Phase 0, story 0.2 — measure what the NVIDIA free endpoint actually does.

Answers four questions that the architecture currently assumes:

  1. Does streaming work through ChatNVIDIA?
  2. How reliable is structured output? Ten consecutive calls, pass rate recorded.
  3. Can `thinking` be disabled through ChatNVIDIA, and what does each level cost in latency?
  4. What values does `reasoning_effort` actually accept?

Question 3 is the one that could force an architecture change. The `thinking` parameter is
documented for the raw OpenAI client via `extra_body`. If ChatNVIDIA cannot pass it through,
the Interviewer cannot run with thinking disabled, and every candidate turn pays the
reasoning latency. This script tests both clients so the answer is observed, not assumed.

Run:  python scripts/probe_nvidia.py
Then paste the report into docs/DEV-STATE.md § Environment notes.
"""

from __future__ import annotations

import os
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

API_KEY = os.getenv("NVIDIA_API_KEY", "")
BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
MODEL = os.getenv("NVIDIA_MODEL", "z-ai/glm-5.2")

if not API_KEY or API_KEY.startswith("PASTE_"):
    sys.exit("NVIDIA_API_KEY is not set in backend/.env — paste your regenerated key first.")
if not API_KEY.startswith("nvapi-"):
    sys.exit(f"NVIDIA_API_KEY does not look like an NVIDIA key (expected 'nvapi-' prefix).")


# ─────────────────────────────────────────────────────────────────────────────
# Report accumulator
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Report:
    lines: list[str] = field(default_factory=list)

    def section(self, title: str) -> None:
        self.lines.append(f"\n### {title}")
        print(f"\n\033[1m{title}\033[0m")

    def note(self, text: str) -> None:
        self.lines.append(f"- {text}")
        print(f"  {text}")

    def dump(self) -> str:
        return "\n".join(self.lines)


report = Report()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Streaming through ChatNVIDIA
# ─────────────────────────────────────────────────────────────────────────────

def probe_streaming() -> None:
    report.section("1. Streaming (ChatNVIDIA)")
    from langchain_nvidia_ai_endpoints import ChatNVIDIA

    client = ChatNVIDIA(
        model=MODEL, api_key=API_KEY, temperature=1, top_p=1, max_tokens=256, seed=42
    )

    started = time.perf_counter()
    first_chunk_at: float | None = None
    chunks = 0
    text = ""

    try:
        for chunk in client.stream([{"role": "user", "content": "Name three fruits."}]):
            if first_chunk_at is None:
                first_chunk_at = time.perf_counter() - started
            chunks += 1
            text += chunk.content or ""
    except Exception as exc:
        report.note(f"FAILED — {type(exc).__name__}: {exc}")
        return

    total = time.perf_counter() - started
    report.note(f"chunks received: {chunks}")
    report.note(f"time to first chunk: {first_chunk_at:.2f}s")
    report.note(f"total: {total:.2f}s")
    report.note(f"streaming works: {'YES' if chunks > 1 else 'NO — single chunk only'}")
    report.note(f'sample output: "{text.strip()[:80]}"')


# ─────────────────────────────────────────────────────────────────────────────
# 2. Structured output reliability
# ─────────────────────────────────────────────────────────────────────────────

class CandidateLevel(BaseModel):
    """Deliberately shaped like the Resume Analyst's real output."""

    level: str = Field(description="One of: APM, PM, Senior PM, GPM")
    years_experience: int = Field(description="Total years of PM experience")
    rationale: str = Field(description="One sentence explaining the level")
    domains: list[str] = Field(description="Product domains worked in")


RESUME_SNIPPET = (
    "Priya Raghunathan. 7 years product management. Currently Senior PM at a B2B "
    "logistics marketplace, owning the carrier-matching product area (12 engineers, "
    "$4.7M ARR influenced). Previously PM at a fintech startup, launched a lending "
    "product 0-to-1 reaching 31,000 monthly active borrowers."
)

TRIALS = 10


def probe_structured_output() -> None:
    report.section(f"2. Structured output — {TRIALS} consecutive trials")
    from langchain_nvidia_ai_endpoints import ChatNVIDIA

    client = ChatNVIDIA(
        model=MODEL, api_key=API_KEY, temperature=1, top_p=1, max_tokens=2048
    ).with_structured_output(CandidateLevel)

    passes, failures, latencies = 0, [], []

    for i in range(1, TRIALS + 1):
        started = time.perf_counter()
        try:
            result = client.invoke(
                [{"role": "user", "content": f"Level this candidate:\n\n{RESUME_SNIPPET}"}]
            )
            elapsed = time.perf_counter() - started
            latencies.append(elapsed)
            if isinstance(result, CandidateLevel):
                passes += 1
                print(f"  trial {i:2}/{TRIALS}  ok    {elapsed:5.2f}s  level={result.level}")
            else:
                failures.append(f"trial {i}: wrong type {type(result).__name__}")
                print(f"  trial {i:2}/{TRIALS}  WRONG TYPE")
        except Exception as exc:
            failures.append(f"trial {i}: {type(exc).__name__}: {exc}")
            print(f"  trial {i:2}/{TRIALS}  FAIL  {type(exc).__name__}")

    report.note(f"**pass rate: {passes}/{TRIALS}**")
    if latencies:
        report.note(f"median latency: {statistics.median(latencies):.2f}s")
    for f in failures:
        report.note(f"failure — {f}")

    if passes == TRIALS:
        report.note("VERDICT: reliable. prompt-validate-retry stays defensive, not mandatory.")
    else:
        report.note(
            "VERDICT: NOT reliable. prompt-validate-retry becomes MANDATORY in every agent. "
            "Record this in DEV-STATE § Decisions before Phase 1 starts."
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. The `thinking` parameter — can ChatNVIDIA pass it through?
# ─────────────────────────────────────────────────────────────────────────────

PROMPT = "A product's DAU rose 20% but session length fell 15%. In two sentences, why?"


def _time_openai(extra_body: dict | None) -> tuple[float, str]:
    from openai import OpenAI

    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    started = time.perf_counter()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": PROMPT}],
        max_tokens=512,
        temperature=1,
        extra_body=extra_body or {},
    )
    return time.perf_counter() - started, (resp.choices[0].message.content or "")[:60]


def probe_thinking() -> None:
    report.section("3. `thinking` parameter — raw OpenAI client")

    configs = {
        "thinking disabled": {"thinking": {"type": "disabled"}},
        "thinking enabled": {"thinking": {"type": "enabled"}},
        "enabled + effort=max": {"thinking": {"type": "enabled"}, "reasoning_effort": "max"},
    }

    for label, extra in configs.items():
        try:
            elapsed, sample = _time_openai(extra)
            report.note(f"{label}: {elapsed:.2f}s")
        except Exception as exc:
            report.note(f"{label}: FAILED — {type(exc).__name__}: {exc}")

    report.section("3b. Can ChatNVIDIA pass `thinking` through?")
    from langchain_nvidia_ai_endpoints import ChatNVIDIA

    # Two plausible routes. We do not know which works; that is the point.
    routes = {
        "constructor kwarg": lambda: ChatNVIDIA(
            model=MODEL, api_key=API_KEY, max_tokens=512,
            thinking={"type": "disabled"},
        ),
        "extra_body kwarg": lambda: ChatNVIDIA(
            model=MODEL, api_key=API_KEY, max_tokens=512,
            extra_body={"thinking": {"type": "disabled"}},
        ),
    }

    worked: list[str] = []
    for label, build in routes.items():
        try:
            started = time.perf_counter()
            build().invoke([{"role": "user", "content": PROMPT}])
            elapsed = time.perf_counter() - started
            report.note(f"{label}: accepted, {elapsed:.2f}s")
            worked.append(label)
        except Exception as exc:
            report.note(f"{label}: rejected — {type(exc).__name__}: {str(exc)[:120]}")

    if worked:
        report.note(f"VERDICT: use `{worked[0]}` to disable thinking on the Interviewer.")
    else:
        report.note(
            "VERDICT: ChatNVIDIA cannot pass `thinking`. The Interviewer must either use the "
            "raw OpenAI client or accept reasoning latency on every turn. ARCHITECTURE CHANGE."
        )


# ─────────────────────────────────────────────────────────────────────────────
# 4. reasoning_effort enum
# ─────────────────────────────────────────────────────────────────────────────

CANDIDATES = ["none", "minimal", "low", "medium", "high", "max", "xhigh", "default"]


def probe_reasoning_effort() -> None:
    report.section("4. `reasoning_effort` accepted values")
    accepted, rejected = [], []

    for value in CANDIDATES:
        try:
            elapsed, _ = _time_openai(
                {"thinking": {"type": "enabled"}, "reasoning_effort": value}
            )
            accepted.append(f"{value} ({elapsed:.1f}s)")
            print(f"  {value:10} accepted  {elapsed:5.2f}s")
        except Exception as exc:
            rejected.append(value)
            print(f"  {value:10} rejected  {type(exc).__name__}")

    report.note(f"accepted: {', '.join(accepted) if accepted else 'none'}")
    report.note(f"rejected: {', '.join(rejected) if rejected else 'none'}")
    report.note(
        "The architecture assumes a 'high' level exists for the Evaluator. "
        f"'high' is {'AVAILABLE' if any(a.startswith('high') for a in accepted) else 'NOT AVAILABLE — pick the nearest accepted value'}."
    )


# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\nProbing {MODEL} at {BASE_URL}")
    print(f"Key: {API_KEY[:12]}…{API_KEY[-4:]}\n")

    for probe in (probe_streaming, probe_structured_output, probe_thinking,
                  probe_reasoning_effort):
        try:
            probe()
        except Exception as exc:
            report.note(f"PROBE CRASHED — {type(exc).__name__}: {exc}")

    print("\n" + "=" * 70)
    print("Paste the block below into docs/DEV-STATE.md § Environment notes")
    print("=" * 70)
    print(f"\n## NVIDIA probe — {time.strftime('%Y-%m-%d')}\n")
    print(report.dump())
    print()


if __name__ == "__main__":
    main()
