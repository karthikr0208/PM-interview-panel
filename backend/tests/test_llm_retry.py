"""Deterministic tests for the validate-retry path. No network.

`test_llm.py::test_retry_wrapper_converges` proves retry works against the
real endpoint, but only probabilistically — it passes without exercising the
retry at all whenever the first attempt happens to succeed. These tests force
each branch with a fake runnable, so the logic is actually covered.

Retry became mandatory rather than defensive after `nemotron-3-super` scored
7/10 on structured output (DEV-STATE 2026-07-30), which makes this logic
load-bearing for every agent from Phase 1 onward.
"""

from __future__ import annotations

import logging

import pytest
from pydantic import BaseModel

from app.llm import StructuredOutputError, _append_retry_instruction, _LoggedStructured


class Answer(BaseModel):
    value: int


class FakeRunnable:
    """Returns a queued sequence of results, recording what it was called with.

    A queued exception is raised rather than returned, so transport failures
    can be exercised alongside schema failures.
    """

    def __init__(self, *results: object) -> None:
        self._results = list(results)
        self.inputs: list[object] = []

    def invoke(self, model_input: object, *_: object, **__: object) -> object:
        self.inputs.append(model_input)
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def wrap(runnable: FakeRunnable) -> _LoggedStructured:
    return _LoggedStructured(role="deep", model="fake-model", runnable=runnable)


def test_none_then_valid_returns_the_valid_result() -> None:
    runnable = FakeRunnable(None, Answer(value=7))
    assert wrap(runnable).invoke("prompt") == Answer(value=7)
    assert len(runnable.inputs) == 2, "expected exactly one retry"


def test_none_twice_raises_rather_than_returning_none() -> None:
    """Returning None on double failure would push an unparseable value into
    graph state, where it surfaces as a confusing error several nodes later."""
    runnable = FakeRunnable(None, None)
    with pytest.raises(StructuredOutputError, match="fake-model"):
        wrap(runnable).invoke("prompt")


def test_first_attempt_success_does_not_retry() -> None:
    """Retry costs a second call against a 40 requests/minute ceiling."""
    runnable = FakeRunnable(Answer(value=1))
    wrap(runnable).invoke("prompt")
    assert len(runnable.inputs) == 1


def test_retry_appends_the_failure_to_a_string_prompt() -> None:
    runnable = FakeRunnable(None, Answer(value=2))
    wrap(runnable).invoke("original prompt")
    retried = runnable.inputs[1]
    assert retried.startswith("original prompt")
    assert "could not be parsed" in retried


def test_retry_appends_a_message_to_a_message_list() -> None:
    """Agents pass message lists as often as strings; appending a string to a
    list would corrupt the input rather than extend it."""
    runnable = FakeRunnable(None, Answer(value=3))
    wrap(runnable).invoke([("system", "you are an evaluator"), ("human", "score this")])
    retried = runnable.inputs[1]
    assert isinstance(retried, list)
    assert len(retried) == 3
    assert retried[-1][0] == "human"


def test_transport_errors_are_reraised_not_retried() -> None:
    """A 429 or timeout needs backoff, not an immediate second call — retrying
    at this layer would double the load exactly when the endpoint is refusing
    it. Transport handling belongs in ARCHITECTURE.md §9."""
    runnable = FakeRunnable(TimeoutError("read timed out"), Answer(value=4))
    with pytest.raises(TimeoutError):
        wrap(runnable).invoke("prompt")
    assert len(runnable.inputs) == 1, "a transport failure must not be retried here"


class FakeSchemaRejection(Exception):
    """Stands in for `openai.BadRequestError` on a 400 `json_validate_failed`.

    Deliberately not the real SDK type: the wrapper must classify this by the
    error body's code, not by catching an openai-specific class, or the same
    failure from a different client library would go unretried again.
    """

    def __init__(self) -> None:
        super().__init__(
            "Error code: 400 - {'error': {'message': 'Generated JSON does not match the "
            "expected schema.', 'type': 'invalid_request_error', "
            "'code': 'json_validate_failed'}}"
        )
        self.code = "json_validate_failed"


def test_groq_schema_rejection_is_retried_not_reraised() -> None:
    """Regression, 2026-08-04. Groq validates structured output server-side,
    so a model that emits well-formed JSON of the WRONG SHAPE never reaches
    pydantic -- the SDK raises `BadRequestError` instead. That is a schema
    failure wearing a transport exception's clothes, and it was falling
    through to the re-raise branch, so the retry this wrapper exists to
    provide never ran. Observed on the Planner's first golden smoke:
    gpt-oss-20b folded `grounded_in` into the preceding `probe_angles`
    array, and the retry then succeeded."""
    runnable = FakeRunnable(FakeSchemaRejection(), Answer(value=8))
    assert wrap(runnable).invoke("prompt") == Answer(value=8)
    assert len(runnable.inputs) == 2, "a schema rejection must be retried"


def test_schema_rejection_twice_raises_structured_output_error() -> None:
    runnable = FakeRunnable(FakeSchemaRejection(), FakeSchemaRejection())
    with pytest.raises(StructuredOutputError, match="fake-model"):
        wrap(runnable).invoke("prompt")


def test_schema_rejection_detection_does_not_swallow_a_429() -> None:
    """The boundary that matters: broadening the retry must not start
    retrying rate limits, which is the failure the transport branch exists
    to prevent. A 429 mentions neither the code nor the phrase."""
    runnable = FakeRunnable(
        RuntimeError("Error code: 429 - rate_limit_exceeded: tokens per day (TPD)"),
        Answer(value=9),
    )
    with pytest.raises(RuntimeError):
        wrap(runnable).invoke("prompt")
    assert len(runnable.inputs) == 1, "a 429 must not be retried at this layer"


def test_both_attempts_are_logged(caplog) -> None:
    """Both calls count against the rate budget, so both must appear."""
    runnable = FakeRunnable(None, Answer(value=5))
    with caplog.at_level(logging.INFO, logger="app.llm"):
        wrap(runnable).invoke("prompt")

    calls = [r.getMessage() for r in caplog.records if "llm_call" in r.getMessage()]
    assert len(calls) == 2, f"expected 2 logged calls, got {len(calls)}"
    assert "outcome=empty" in calls[0], "the None attempt should log outcome=empty"
    assert "outcome=ok" in calls[1]


def test_append_helper_leaves_unknown_input_shapes_alone() -> None:
    sentinel = object()
    assert _append_retry_instruction(sentinel, "err") is sentinel
