"""ChatNVIDIA client factory with per-call timestamped logging.

Logging is written now, not retrofitted later: the free tier ceiling is 40
requests/minute and rate-limit logging has to exist before the first call is
made, per PHASE-0-SPEC.md story 0.2.

No `thinking` parameter is passed anywhere in this file. `thinking` is
GLM-specific; Nemotron 3 returns HTTP 400 Validation: Unsupported
parameter(s): 'thinking' for it. Model choice (fast / deep / backup) is the
latency-vs-quality lever instead of a request parameter. See DEV-STATE.md
2026-07-29.
"""

from __future__ import annotations

import logging
import time
from typing import Any, AsyncIterator, Iterator, Literal

from langchain_nvidia_ai_endpoints import ChatNVIDIA

from app.config import settings

logger = logging.getLogger("app.llm")

Role = Literal["fast", "deep", "backup"]

_MODEL_BY_ROLE: dict[Role, str] = {
    "fast": settings.nvidia_model_fast,
    "deep": settings.nvidia_model_deep,
    "backup": settings.nvidia_model_backup,
}


def _log_call(role: Role, model: str, started: float, outcome: str, error: str = "") -> None:
    elapsed_ms = (time.perf_counter() - started) * 1000
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if error:
        logger.info(
            "llm_call ts=%s role=%s model=%s elapsed_ms=%.0f outcome=%s error=%s",
            timestamp, role, model, elapsed_ms, outcome, error,
        )
    else:
        logger.info(
            "llm_call ts=%s role=%s model=%s elapsed_ms=%.0f outcome=%s",
            timestamp, role, model, elapsed_ms, outcome,
        )


class LoggingChatNVIDIA:
    """Wraps a `ChatNVIDIA` client so every `invoke` / `ainvoke` is logged with
    a timestamp, model id, elapsed ms, and outcome — before anything is built
    on top of it, not after a rate-limit incident makes it necessary.

    Wraps rather than subclasses: `ChatNVIDIA` is a pydantic model with its
    own field validation, and invoke/ainvoke/stream/astream are the only entry
    points a graph node needs. Wrapping keeps every call site's logging in one
    place regardless of which entry point a node uses.
    """

    def __init__(self, role: Role, client: ChatNVIDIA) -> None:
        self.role = role
        self.model = _MODEL_BY_ROLE[role]
        self._client = client

    def invoke(self, *args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        try:
            result = self._client.invoke(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 — logged, then re-raised unchanged
            _log_call(self.role, self.model, started, "error", type(exc).__name__)
            raise
        _log_call(self.role, self.model, started, "ok")
        return result

    async def ainvoke(self, *args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        try:
            result = await self._client.ainvoke(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 — logged, then re-raised unchanged
            _log_call(self.role, self.model, started, "error", type(exc).__name__)
            raise
        _log_call(self.role, self.model, started, "ok")
        return result

    def stream(self, *args: Any, **kwargs: Any) -> Iterator[Any]:
        started = time.perf_counter()
        try:
            for chunk in self._client.stream(*args, **kwargs):
                yield chunk
        except Exception as exc:  # noqa: BLE001
            _log_call(self.role, self.model, started, "error", type(exc).__name__)
            raise
        else:
            _log_call(self.role, self.model, started, "ok")

    async def astream(self, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        started = time.perf_counter()
        try:
            async for chunk in self._client.astream(*args, **kwargs):
                yield chunk
        except Exception as exc:  # noqa: BLE001
            _log_call(self.role, self.model, started, "error", type(exc).__name__)
            raise
        else:
            _log_call(self.role, self.model, started, "ok")

    def with_structured_output(self, *args: Any, **kwargs: Any) -> Any:
        """Delegates to the underlying client. The structured-output pass-rate
        measurement (story 0.2's remaining item — 10 consecutive calls through
        `ChatNVIDIA`, not raw HTTP) is application logic and belongs in
        `tests/test_llm.py`, not in this scaffold."""
        return self._client.with_structured_output(*args, **kwargs)


def get_llm(role: Role) -> LoggingChatNVIDIA:
    """Factory: 'fast' | 'deep' | 'backup' -> a logged ChatNVIDIA client.

    fast   = nemotron-3-nano-30b-a3b   — latency-critical turns (Interviewer)
    deep   = nemotron-3-super-120b-a12b — quality-critical turns (everything else)
    backup = gpt-oss-20b                — fallback if the primary 429s or 503s
    """
    client = ChatNVIDIA(
        model=_MODEL_BY_ROLE[role],
        api_key=settings.nvidia_api_key,
        base_url=settings.nvidia_base_url,
    )
    return LoggingChatNVIDIA(role=role, client=client)
