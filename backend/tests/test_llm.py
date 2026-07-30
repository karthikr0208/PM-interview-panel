"""Story 0.2: what the real NVIDIA endpoint actually does.

Every test here is marked `live` and hits the real endpoint. Deselect with
`-m "not live"`. Mocking these would defeat the entire purpose of Phase 0,
which is finding out what the endpoint does rather than what the docs claim.

Runtime is minutes, not seconds: `deep` structured calls measured a ~20s
median on 2026-07-30. That cost is the point of the test.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Literal

import pytest
from pydantic import BaseModel, Field

from app.llm import StructuredOutputError, get_llm

pytestmark = pytest.mark.live

# 10 consecutive calls, per PHASE-0-SPEC.md story 0.2.
N_TRIALS = 10

# Regression detectors, not aspirations. Observed across four N=10 runs on
# 2026-07-30: fast 9-10/10, deep 7-9/10. Asserting 10/10 on deep would fail a
# correct build most of the time.
#
# Floors sit below the observed minimum on purpose. Contention on this free
# tier is time-varying and large — deep's median moved between 9.2s and 20.4s
# within one hour — so a floor set at the observed minimum would turn a bad
# hour into a red build. Anything at or below these floors is a real signal.
RAW_PASS_FLOOR = {"fast": 8, "deep": 5}


class Levelling(BaseModel):
    """Shaped like the real Resume Analyst output, not a toy schema. A schema
    the model finds trivial would not exercise the failure this test exists
    to catch."""

    assessed_level: Literal["APM", "PM", "Senior PM", "GPM"]
    rationale: str = Field(description="One sentence citing evidence from the resume.")
    confidence: float = Field(ge=0.0, le=1.0)


RESUME = (
    "Led pricing for a B2B analytics suite. Owned roadmap for 3 squads (14 engineers). "
    "Shipped usage-based billing; ARR moved from $4.7M to $7.2M over 6 quarters. "
    "Ran quarterly planning across design, data science, and sales enablement. "
    "Previously APM on the onboarding team for 2 years."
)
PROMPT = f"Level this product manager candidate.\n\nResume:\n{RESUME}"


def test_completion_returns_text() -> None:
    result = get_llm("fast").invoke("Reply with the single word: ok")
    assert result.content.strip(), "completion returned empty content"


def test_streaming_yields_multiple_chunks() -> None:
    """More than one chunk, not merely a non-empty result. A non-streaming
    endpoint still returns content in a single chunk and would pass a
    weaker assertion."""
    chunks = list(
        get_llm("fast").stream(
            "Name three risks in launching usage-based pricing. One line each."
        )
    )
    assert len(chunks) > 1, f"expected incremental chunks, got {len(chunks)}"
    assert "".join(getattr(c, "content", "") or "" for c in chunks).strip()


@pytest.mark.parametrize("role", ["fast", "deep"])
def test_structured_output_raw_pass_rate(role: str, record_property) -> None:
    """Measures the pass rate WITHOUT retry and records it.

    This is the number story 0.2 asks for. It is deliberately measured on the
    unwrapped runnable: with retry on, this test would report the shipped
    contract instead of the underlying reliability, and a model silently
    degrading from 10/10 to 6/10 would stay hidden behind the retry.
    """
    llm = get_llm(role)
    raw = llm._client.with_structured_output(Levelling)

    passed, latencies, failures = 0, [], []
    for i in range(N_TRIALS):
        started = time.perf_counter()
        try:
            result = raw.invoke(PROMPT)
        except Exception as exc:  # noqa: BLE001 — a transport failure is a data point
            failures.append(f"#{i + 1} {type(exc).__name__}")
            continue
        if isinstance(result, Levelling):
            passed += 1
            latencies.append(time.perf_counter() - started)
        else:
            failures.append(f"#{i + 1} returned {type(result).__name__}")

    latencies.sort()
    median = latencies[len(latencies) // 2] if latencies else float("nan")
    record_property("pass_rate", f"{passed}/{N_TRIALS}")
    record_property("median_seconds", round(median, 1))
    print(
        f"\n  {role} ({llm.model}) raw structured output: {passed}/{N_TRIALS}"
        f"  median {median:.1f}s  failures={failures or 'none'}"
    )

    floor = RAW_PASS_FLOOR[role]
    assert passed >= floor, (
        f"{role} scored {passed}/{N_TRIALS}, below the {floor} floor measured "
        f"2026-07-30. Failures: {failures}"
    )


def test_retry_wrapper_converges() -> None:
    """The shipped contract: get_llm(...).with_structured_output() retries a
    schema failure once and returns a valid instance.

    Run on `deep` because that is the model that actually fails — on `fast`
    the retry path would almost never execute and the test would pass without
    exercising anything.
    """
    structured = get_llm("deep").with_structured_output(Levelling)
    try:
        result = structured.invoke(PROMPT)
    except StructuredOutputError:
        pytest.fail("structured output failed twice in a row; retry did not converge")
    assert isinstance(result, Levelling)
    assert 0.0 <= result.confidence <= 1.0


def test_every_call_is_logged_with_a_timestamp(caplog) -> None:
    """The free tier ceiling is 40 requests/minute. An unlogged call is one
    that cannot be accounted for when that ceiling is hit."""
    with caplog.at_level(logging.INFO, logger="app.llm"):
        get_llm("fast").invoke("Reply with the single word: ok")

    lines = [r.getMessage() for r in caplog.records if r.name == "app.llm"]
    assert lines, "no llm_call log record was emitted"
    assert re.search(
        r"llm_call ts=\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z "
        r"role=\w+ model=\S+ elapsed_ms=\d+ outcome=\w+",
        lines[-1],
    ), f"log line is missing a field: {lines[-1]}"


def test_structured_calls_are_logged_too(caplog) -> None:
    """Regression guard for a real bug: `with_structured_output` originally
    returned the client's raw runnable, so every structured call bypassed the
    logging wrapper. Agents use structured output almost exclusively, so
    nearly the whole application was invisible while appearing to work."""
    structured = get_llm("fast").with_structured_output(Levelling)
    with caplog.at_level(logging.INFO, logger="app.llm"):
        structured.invoke(PROMPT)

    assert [r for r in caplog.records if "llm_call" in r.getMessage()], (
        "a structured call emitted no llm_call log line"
    )
