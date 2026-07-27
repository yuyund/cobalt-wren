from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypedDict

import pytest

from cobalt_wren.api.engine import create_engine
from cobalt_wren.api.workflow import WorkflowExecutionContext
from cobalt_wren.native import NativeWorkflowContext, workflow
from cobalt_wren.native.local import lint_native_requirements, run_native_workflow
from cobalt_wren.native.schema import schema_for_type
from tests.support.recording_event_sink import RecordingEventSink


class Request(TypedDict):
    name: str
    count: int


class Result(TypedDict):
    message: str


@dataclass
class DataclassRequest:
    name: str
    optional: int = 1


def test_workflow_infers_typed_dict_schemas_and_accepts_positional_name() -> None:
    @workflow("Typed hello")
    async def hello(ctx: NativeWorkflowContext, request: Request) -> Result:
        del ctx
        return {"message": request["name"]}

    assert hello.input_schema == {
        "type": "object",
        "properties": {"name": {"type": "string"}, "count": {"type": "integer"}},
        "required": ["count", "name"],
    }
    assert hello.output_schema == {
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "required": ["message"],
    }
    contribution = hello.contribution(kind="test.native.typed")
    assert contribution.definition.input_schema == hello.input_schema


def test_dataclass_schema_marks_only_fields_without_defaults_required() -> None:
    assert schema_for_type(DataclassRequest) == {
        "type": "object",
        "properties": {"name": {"type": "string"}, "optional": {"type": "integer"}},
        "required": ["name"],
    }


def test_local_runner_executes_without_django_setup() -> None:
    @workflow("Local hello")
    async def hello(ctx: NativeWorkflowContext, request: Mapping[str, object]):
        value = await ctx.step("format", lambda name: str(name).upper(), request["name"])
        return {"message": value}

    result = run_native_workflow(hello, {"name": "Yudai"})
    assert result.output == {"message": "YUDAI"}
    assert result.metadata["step_count"] == 1
    assert result.metadata["last_step_name"] == "format"


def test_progress_and_metric_emit_safe_semantic_events() -> None:
    @workflow("Progress")
    async def progress(ctx: NativeWorkflowContext, request: Mapping[str, object]):
        del request
        await ctx.progress.update(current=2, total=4, message="Halfway")
        ctx.metric.record("documents.processed", 2, unit="document", metadata={"api_key": "secret"})
        return {}

    sink = RecordingEventSink()
    plugin = progress.plugin(plugin_name="test.native.progress", workflow_kind="test.native.progress")
    prepared = create_engine({"version": 1}, plugins=(plugin,), discover_plugins=False).prepare_workflow("test.native.progress")
    prepared.execute({}, context=WorkflowExecutionContext(run_id=88, event_sink=sink))

    progress_event, metric_event = sink.run_events[-2:]
    assert progress_event.kind == "native.progress"
    assert progress_event.payload["percent"] == 50.0
    assert metric_event.kind == "native.metric"
    assert "secret" not in str(metric_event.payload)


def test_progress_and_metric_validate_author_input() -> None:
    @workflow("Invalid telemetry")
    async def invalid(ctx: NativeWorkflowContext, request: Mapping[str, object]):
        del request
        with pytest.raises(ValueError, match="exceed"):
            await ctx.progress.update(current=2, total=1)
        with pytest.raises(ValueError, match="lowercase"):
            ctx.metric.record("Bad Metric", 1)
        return {}

    result = run_native_workflow(invalid, {})
    assert result.output == {}


def test_failed_step_preserves_primary_exception_and_adds_author_context() -> None:
    def fail() -> None:
        raise ValueError("bad input")

    @workflow("Failure")
    async def failing(ctx: NativeWorkflowContext, request: Mapping[str, object]):
        del request
        await ctx.step("validate-input", fail)
        return {}

    with pytest.raises(Exception) as excinfo:
        run_native_workflow(failing, {})
    cause = excinfo.value
    while cause.__cause__ is not None:
        cause = cause.__cause__
    assert isinstance(cause, ValueError)
    assert any("validate-input" in note for note in getattr(cause, "__notes__", ()))


def test_input_schema_validation_happens_before_workflow_execution() -> None:
    called = False

    @workflow("Validated input")
    async def validated(ctx: NativeWorkflowContext, request: Request) -> Result:
        nonlocal called
        del ctx
        called = True
        return {"message": request["name"]}

    with pytest.raises(Exception) as excinfo:
        run_native_workflow(validated, {"name": "Yudai", "count": "wrong"})
    cause = excinfo.value
    while cause.__cause__ is not None:
        cause = cause.__cause__
    assert type(cause).__name__ == "NativeSchemaValidationError"
    assert "$.count: expected integer" in str(cause)
    assert called is False


def test_output_schema_validation_rejects_invalid_result() -> None:
    @workflow("Validated output")
    async def invalid_output(ctx: NativeWorkflowContext, request: Request) -> Result:
        del ctx, request
        return {"message": 42}  # type: ignore[typeddict-item]

    with pytest.raises(Exception) as excinfo:
        run_native_workflow(invalid_output, {"name": "Yudai", "count": 1})
    cause = excinfo.value
    while cause.__cause__ is not None:
        cause = cause.__cause__
    assert "Native output validation failed" in str(cause)
    assert "$.message: expected string" in str(cause)


def test_workflow_decorator_declares_requirements() -> None:
    @workflow(
        "Required",
        provider_profiles=("default",),
        tools=("echo",),
        artifact_store=True,
        event_sinks=("audit",),
    )
    async def required(ctx: NativeWorkflowContext, request: Mapping[str, object]):
        del ctx, request
        return {}

    assert required.requirements.provider_profiles == ("default",)
    assert required.requirements.tools == ("echo",)
    assert required.requirements.artifact_store is True
    assert required.requirements.event_sinks == ("audit",)
    assert required.contribution(kind="test.required").definition.requirements == required.requirements


def test_progress_requires_monotonic_current_and_stable_total() -> None:
    @workflow("Progress contract")
    async def progress_contract(ctx: NativeWorkflowContext, request: Mapping[str, object]):
        del request
        await ctx.progress.update(current=1, total=3)
        with pytest.raises(ValueError, match="monotonic"):
            await ctx.progress.update(current=0, total=3)
        with pytest.raises(ValueError, match="stable"):
            await ctx.progress.update(current=2, total=4)
        return {}

    assert run_native_workflow(progress_contract, {}).output == {}


def test_metric_latest_updates_do_not_consume_distinct_metric_limit() -> None:
    @workflow("Metric contract")
    async def metric_contract(ctx: NativeWorkflowContext, request: Mapping[str, object]):
        del request
        for value in range(120):
            ctx.metric.record("documents.processed", value)
        return {}

    assert run_native_workflow(metric_contract, {}).output == {}


def test_requirement_lint_warns_for_direct_undeclared_helpers() -> None:
    @workflow("Lint")
    async def linted(ctx: NativeWorkflowContext, request: Mapping[str, object]):
        del request
        await ctx.llm.complete("summarize", (), profile="review")
        await ctx.tool.run("lookup", "search")
        await ctx.artifact.write(name="report.txt", content="done")
        return {}

    warnings = lint_native_requirements(linted)
    identities = {(item["requirement_type"], item["requirement_name"]) for item in warnings}
    assert identities == {
        ("provider_profile", "review"),
        ("tool", "search"),
        ("artifact_store", "artifact"),
    }


def test_requirement_lint_accepts_matching_explicit_declarations() -> None:
    @workflow(
        "Lint declared",
        provider_profiles=("review",),
        tools=("search",),
        artifact_store=True,
    )
    async def declared(ctx: NativeWorkflowContext, request: Mapping[str, object]):
        del request
        await ctx.llm.complete("summarize", (), profile="review")
        await ctx.tool.run("lookup", "search")
        await ctx.artifact.write(name="report.txt", content="done")
        return {}

    assert lint_native_requirements(declared) == ()


def test_requirement_lint_does_not_guess_dynamic_names() -> None:
    @workflow("Dynamic lint")
    async def dynamic(ctx: NativeWorkflowContext, request: Mapping[str, object]):
        profile = str(request["profile"])
        tool_name = str(request["tool"])
        await ctx.llm.complete("summarize", (), profile=profile)
        await ctx.tool.run("lookup", tool_name)
        return {}

    assert lint_native_requirements(dynamic) == ()
