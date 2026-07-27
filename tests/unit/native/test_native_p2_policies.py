"""Native Authoring P2 retry, timeout, and occurrence identity tests."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping

import pytest

from cobalt_wren.api.engine import create_engine
from cobalt_wren.api.errors import WorkflowTimeoutError
from cobalt_wren.api.workflow import WorkflowExecutionContext
from cobalt_wren.native import NativeWorkflowContext, RetryPolicy, workflow
from tests.support.recording_event_sink import RecordingEventSink


def _prepared(native_workflow, kind: str):
    plugin = native_workflow.plugin(
        plugin_name=f"{kind}.plugin",
        workflow_kind=kind,
    )
    return create_engine(
        {"version": 1},
        plugins=(plugin,),
        discover_plugins=False,
    ).prepare_workflow(kind)


def test_retry_records_each_attempt_and_preserves_stable_subject() -> None:
    attempts = 0

    async def unstable(value: str) -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ConnectionError("private transient detail")
        return value.upper()

    @workflow(name="Retry workflow")
    async def retry_workflow(
        ctx: NativeWorkflowContext,
        request: Mapping[str, object],
    ) -> Mapping[str, object]:
        result = await ctx.step(
            "fetch",
            unstable,
            str(request["value"]),
            retry=RetryPolicy(
                max_attempts=3,
                retry_on=(ConnectionError,),
            ),
        )
        return {"result": result}

    sink = RecordingEventSink()
    result = _prepared(retry_workflow, "test.native.retry").execute(
        {"value": "ok"},
        context=WorkflowExecutionContext(run_id=61, event_sink=sink),
    )

    assert result.output == {"result": "OK"}
    assert result.metadata["step_count"] == 1
    assert result.metadata["attempt_count"] == 3
    spans = list(sink.spans.values())
    assert [span.status for span in spans] == ["failed", "failed", "succeeded"]
    assert [span.started_metadata["attempt"] for span in spans] == [1, 2, 3]
    assert all(
        span.started_metadata["subject_external_id"] == "fetch" for span in spans
    )
    assert "private transient detail" not in str(spans)

    projections = sink.integration_projections
    assert [item["payload"]["status"] for item in projections] == [
        "running",
        "retrying",
        "running",
        "retrying",
        "running",
        "succeeded",
    ]
    assert {item["subject_external_id"] for item in projections} == {"fetch"}
    assert [item["payload"]["attempt"] for item in projections] == [1, 1, 2, 2, 3, 3]


def test_retry_does_not_catch_non_retryable_exception() -> None:
    attempts = 0

    def fail() -> None:
        nonlocal attempts
        attempts += 1
        raise ValueError("not retryable")

    @workflow(name="Non retryable")
    async def non_retryable(
        ctx: NativeWorkflowContext,
        request: Mapping[str, object],
    ) -> Mapping[str, object]:
        del request
        await ctx.step(
            "fail",
            fail,
            retry=RetryPolicy(max_attempts=3, retry_on=(ConnectionError,)),
        )
        return {}

    sink = RecordingEventSink()
    with pytest.raises(ValueError, match="not retryable"):
        _prepared(non_retryable, "test.native.non-retryable").executable.execute(
            {},
            context=WorkflowExecutionContext(run_id=62, event_sink=sink),
        )

    assert attempts == 1
    assert [item["payload"]["status"] for item in sink.integration_projections] == [
        "running",
        "failed",
    ]


def test_async_step_timeout_is_normalized_and_observed() -> None:
    async def slow() -> str:
        await asyncio.sleep(0.1)
        return "late"

    @workflow(name="Timeout")
    async def timeout_workflow(
        ctx: NativeWorkflowContext,
        request: Mapping[str, object],
    ) -> Mapping[str, object]:
        del request
        await ctx.step("slow", slow, timeout_seconds=0.01)
        return {}

    sink = RecordingEventSink()
    with pytest.raises(WorkflowTimeoutError, match="Native step execution timed out"):
        _prepared(timeout_workflow, "test.native.timeout").executable.execute(
            {},
            context=WorkflowExecutionContext(run_id=63, event_sink=sink),
        )

    span = next(iter(sink.spans.values()))
    assert span.status == "failed"
    assert span.error_message == "Native step execution failed."
    assert sink.integration_projections[-1]["payload"]["status"] == "failed"


def test_timeout_can_be_retried_explicitly() -> None:
    attempts = 0

    async def first_slow_then_fast() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            await asyncio.sleep(0.05)
        return "done"

    @workflow(name="Retry timeout")
    async def retry_timeout(
        ctx: NativeWorkflowContext,
        request: Mapping[str, object],
    ) -> Mapping[str, object]:
        del request
        value = await ctx.step(
            "remote-call",
            first_slow_then_fast,
            timeout_seconds=0.01,
            retry=RetryPolicy(
                max_attempts=2,
                retry_on=(WorkflowTimeoutError,),
            ),
        )
        return {"value": value}

    sink = RecordingEventSink()
    result = _prepared(retry_timeout, "test.native.retry-timeout").execute(
        {},
        context=WorkflowExecutionContext(run_id=64, event_sink=sink),
    )

    assert result.output == {"value": "done"}
    assert attempts == 2
    assert [item["payload"]["status"] for item in sink.integration_projections] == [
        "running",
        "retrying",
        "running",
        "succeeded",
    ]


def test_occurrence_keys_create_stable_bounded_loop_identities() -> None:
    @workflow(name="Loop")
    async def loop_workflow(
        ctx: NativeWorkflowContext,
        request: Mapping[str, object],
    ) -> Mapping[str, object]:
        values: list[str] = []
        for index, item in enumerate(request["items"]):
            values.append(
                await ctx.step(
                    "process-item",
                    lambda value: str(value).upper(),
                    item,
                    occurrence_key=str(index),
                )
            )
        return {"values": values}

    sink = RecordingEventSink()
    result = _prepared(loop_workflow, "test.native.loop").execute(
        {"items": ["a", "b", "c"]},
        context=WorkflowExecutionContext(run_id=65, event_sink=sink),
    )

    assert result.output == {"values": ["A", "B", "C"]}
    assert result.metadata["step_count"] == 3
    assert {item["subject_external_id"] for item in sink.integration_projections} == {
        "process-item:0",
        "process-item:1",
        "process-item:2",
    }


def test_duplicate_or_unsafe_occurrence_identity_is_rejected() -> None:
    @workflow(name="Duplicate")
    async def duplicate(
        ctx: NativeWorkflowContext,
        request: Mapping[str, object],
    ) -> Mapping[str, object]:
        del request
        await ctx.step("same", lambda: 1)
        await ctx.step("same", lambda: 2)
        return {}

    with pytest.raises(ValueError, match="already used"):
        _prepared(duplicate, "test.native.duplicate").executable.execute(
            {},
            context=WorkflowExecutionContext(),
        )

    @workflow(name="Unsafe key")
    async def unsafe_key(
        ctx: NativeWorkflowContext,
        request: Mapping[str, object],
    ) -> Mapping[str, object]:
        del request
        await ctx.step("item", lambda: 1, occurrence_key="raw customer name")
        return {}

    with pytest.raises(ValueError, match="occurrence_key"):
        _prepared(unsafe_key, "test.native.unsafe-key").executable.execute(
            {},
            context=WorkflowExecutionContext(),
        )


def test_retry_policy_validation() -> None:
    with pytest.raises(ValueError):
        RetryPolicy(max_attempts=0)
    with pytest.raises(ValueError):
        RetryPolicy(retry_on=())
    with pytest.raises(TypeError):
        RetryPolicy(retry_on=(str,))  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        RetryPolicy(initial_delay_seconds=-1)
    with pytest.raises(ValueError):
        RetryPolicy(backoff_multiplier=0.5)
