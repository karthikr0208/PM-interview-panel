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
from pydantic import ValidationError

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

    def with_structured_output(self, *args: Any, **kwargs: Any) -> "_LoggedStructured":
        """Returns a *logged* runnable, not the client's raw one.

        Returning `self._client.with_structured_output(...)` directly would
        hand back a runnable wired straight to the underlying client, so every
        call through it would skip this wrapper. Agents use structured output
        almost exclusively, which would have left nearly the whole application
        invisible to the rate-limit log while appearing to work.
        """
        return _LoggedStructured(
            role=self.role,
            model=self.model,
            runnable=self._client.with_structured_output(*args, **kwargs),
        )


class StructuredOutputError(RuntimeError):
    """Structured output failed on both the first attempt and the retry."""


_RETRY_INSTRUCTION = (
    "Your previous response could not be parsed into the required schema"
    " ({error}). Respond again with only a JSON object matching the schema"
    " exactly. No preamble, no explanation, no markdown fence."
)


def _append_retry_instruction(model_input: Any, error: str) -> Any:
    """Appends the failure to the prompt, whatever shape it arrived in.

    Agents pass either a plain string or a list of messages, so both are
    handled here rather than at every call site.
    """
    instruction = _RETRY_INSTRUCTION.format(error=error)
    if isinstance(model_input, str):
        return f"{model_input}\n\n{instruction}"
    if isinstance(model_input, list):
        return [*model_input, ("human", instruction)]
    return model_input


class _LoggedStructured:
    """Logging + validate-retry wrapper for what `with_structured_output` returns.

    **Retry is on by default, deliberately.** Measured 2026-07-30 through
    `ChatNVIDIA`: `nemotron-3-nano` 10/10, `nemotron-3-super` **7/10**, the
    three failures returning `None` rather than raising. Karthik's call on that
    gate was retry now and revisit the model assignment in Phase 2 against
    golden cases. Making retry the default here rather than something each
    agent opts into is what makes "mandatory in every agent" structural — an
    agent cannot forget it.

    Retries **schema failures only**: a `None` return or a `ValidationError`.
    Transport failures (429, 503, timeout) are a different concern with a
    different fix — exponential backoff per ARCHITECTURE.md §9 — and are
    re-raised untouched so they are not silently retried at the wrong layer.

    One retry, then fail, matching ARCHITECTURE.md's uniform failure behaviour.
    Logs `outcome=empty` for the silent `None` case so it is visible in the
    rate-limit log instead of vanishing.
    """

    def __init__(self, role: Role, model: str, runnable: Any) -> None:
        self.role = role
        self.model = model
        self._runnable = runnable

    def _outcome(self, result: Any) -> str:
        return "ok" if result is not None else "empty"

    def invoke(self, model_input: Any, *args: Any, **kwargs: Any) -> Any:
        result, error = self._attempt(model_input, *args, **kwargs)
        if result is not None:
            return result
        retried, retry_error = self._attempt(
            _append_retry_instruction(model_input, error), *args, **kwargs
        )
        if retried is not None:
            return retried
        raise StructuredOutputError(
            f"{self.model} failed schema validation twice: {retry_error or error}"
        )

    def _attempt(self, model_input: Any, *args: Any, **kwargs: Any) -> tuple[Any, str]:
        started = time.perf_counter()
        try:
            result = self._runnable.invoke(model_input, *args, **kwargs)
        except ValidationError as exc:
            _log_call(self.role, self.model, started, "invalid", type(exc).__name__)
            return None, str(exc)[:200]
        except Exception as exc:  # noqa: BLE001 — transport, not schema. Re-raised.
            _log_call(self.role, self.model, started, "error", type(exc).__name__)
            raise
        _log_call(self.role, self.model, started, self._outcome(result))
        return result, "" if result is not None else "the response was empty"

    async def ainvoke(self, model_input: Any, *args: Any, **kwargs: Any) -> Any:
        result, error = await self._aattempt(model_input, *args, **kwargs)
        if result is not None:
            return result
        retried, retry_error = await self._aattempt(
            _append_retry_instruction(model_input, error), *args, **kwargs
        )
        if retried is not None:
            return retried
        raise StructuredOutputError(
            f"{self.model} failed schema validation twice: {retry_error or error}"
        )

    async def _aattempt(self, model_input: Any, *args: Any, **kwargs: Any) -> tuple[Any, str]:
        started = time.perf_counter()
        try:
            result = await self._runnable.ainvoke(model_input, *args, **kwargs)
        except ValidationError as exc:
            _log_call(self.role, self.model, started, "invalid", type(exc).__name__)
            return None, str(exc)[:200]
        except Exception as exc:  # noqa: BLE001 — transport, not schema. Re-raised.
            _log_call(self.role, self.model, started, "error", type(exc).__name__)
            raise
        _log_call(self.role, self.model, started, self._outcome(result))
        return result, "" if result is not None else "the response was empty"


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
