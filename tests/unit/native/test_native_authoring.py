"""Native Authoring public API and executor tests."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from cobalt_wren.api.engine import create_engine
from cobalt_wren.api.workflow import (
    WorkflowExecutionContext,
    WorkflowExecutionControl,
)
from cobalt_wren.native import NativeWorkflowContext, workflow
from tests.support.recording_event_sink import RecordingEventSink


@workflow(name="Conditional review", tags=("test",))
async def conditional_review(
    ctx: NativeWorkflowContext,
    request: Mapping[str, object],
) -> Mapping[str, object]:
    normalized = await ctx.step("normalize", _normalize, str(request["text"]))
    if bool(request.get("upper")):
        result = await ctx.step("uppercase", _uppercase, normalized)
    else:
        result = await ctx.step("lowercase", _lowercase, normalized)
    return {"result": result}


def _normalize(value: str) -> str:
    return value.strip()


async def _uppercase(value: str) -> str:
    return value.upper()


async def _lowercase(value: str) -> str:
    return value.lower()


def test_native_workflow_converts_to_public_plugin_and_executes_sync_and_async_steps() -> None:
    plugin = conditional_review.plugin(
        plugin_name="native-test-plugin",
        workflow_kind="test.native.conditional",
    )
    engine = create_engine(
        {"version": 1},
        plugins=(plugin,),
        discover_plugins=False,
    )
    sink = RecordingEventSink()

    result = engine.prepare_workflow("test.native.conditional").execute(
        {"text": " Hello ", "upper": True},
        context=WorkflowExecutionContext(
            run_id=7,
            thread_id="native-unit",
            event_sink=sink,
        ),
    )

    assert result.output == {"result": "HELLO"}
    assert result.metadata["integration_id"] == "native"
    assert result.metadata["step_count"] == 2
    assert result.metadata["last_step_name"] == "uppercase"
    assert [span.name for span in sink.spans.values()] == ["normalize", "uppercase"]
    assert all(span.status == "succeeded" for span in sink.spans.values())
    projections = sink.integration_projections
    assert len(projections) == 4
    assert {item["schema_id"] for item in projections} == {"native.step.v1"}
    assert {item["projection_kind"] for item in projections} == {"snapshot"}
    assert [item["payload"]["status"] for item in projections] == [
        "running",
        "succeeded",
        "running",
        "succeeded",
    ]
    assert {item["subject_external_id"] for item in projections} == {
        "normalize",
        "uppercase",
    }


def test_native_records_only_the_executed_conditional_path() -> None:
    plugin = conditional_review.plugin(
        plugin_name="native-conditional-plugin",
        workflow_kind="test.native.path",
    )
    sink = RecordingEventSink()
    result = create_engine(
        {"version": 1},
        plugins=(plugin,),
        discover_plugins=False,
    ).prepare_workflow("test.native.path").execute(
        {"text": " Hello ", "upper": False},
        context=WorkflowExecutionContext(run_id=8, event_sink=sink),
    )

    assert result.output == {"result": "hello"}
    assert [span.name for span in sink.spans.values()] == ["normalize", "lowercase"]
    assert "uppercase" not in {
        item["subject_external_id"] for item in sink.integration_projections
    }


def test_native_failure_preserves_primary_exception_and_records_failed_step() -> None:
    @workflow(name="Failure")
    async def failure(
        ctx: NativeWorkflowContext,
        request: Mapping[str, object],
    ) -> Mapping[str, object]:
        del request
        await ctx.step("explode", _explode)
        return {}

    sink = RecordingEventSink()
    executable = create_engine(
        {"version": 1},
        plugins=(
            failure.plugin(
                plugin_name="native-failure-plugin",
                workflow_kind="test.native.failure",
            ),
        ),
        discover_plugins=False,
    ).prepare_workflow("test.native.failure")

    with pytest.raises(RuntimeError, match="private failure detail"):
        executable.executable.execute(
            {},
            context=WorkflowExecutionContext(run_id=9, event_sink=sink),
        )

    span = next(iter(sink.spans.values()))
    assert span.status == "failed"
    assert "private failure detail" not in span.error_message
    terminal = sink.integration_projections[-1]
    assert terminal["payload"]["status"] == "failed"
    assert "private failure detail" not in str(terminal["payload"])


def _explode() -> None:
    raise RuntimeError("private failure detail")


def test_native_checks_cancellation_before_the_next_step() -> None:
    cancelled = False

    @workflow(name="Cancellation")
    async def cancellation(
        ctx: NativeWorkflowContext,
        request: Mapping[str, object],
    ) -> Mapping[str, object]:
        nonlocal cancelled
        del request
        await ctx.step("first", lambda: "done")
        cancelled = True
        await ctx.step("never-started", lambda: "unexpected")
        return {}

    sink = RecordingEventSink()
    prepared = create_engine(
        {"version": 1},
        plugins=(
            cancellation.plugin(
                plugin_name="native-cancel-plugin",
                workflow_kind="test.native.cancel",
            ),
        ),
        discover_plugins=False,
    ).prepare_workflow("test.native.cancel")

    with pytest.raises(Exception) as excinfo:
        prepared.executable.execute(
            {},
            context=WorkflowExecutionContext(
                run_id=10,
                event_sink=sink,
                control=WorkflowExecutionControl(
                    cancellation_requested=lambda: cancelled
                ),
            ),
        )

    assert type(excinfo.value).__name__ == "WorkflowCancelledError"
    assert [span.name for span in sink.spans.values()] == ["first"]
