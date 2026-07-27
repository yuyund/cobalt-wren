"""Native Artifact convenience API tests."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from cobalt_wren.api.engine import AutomationEngine, EnginePreparedWorkflow, create_engine
from cobalt_wren.api.errors import RuntimeAssemblyError
from cobalt_wren.api.workflow import (
    WorkflowBuildContext,
    WorkflowExecutionContext,
    WorkflowRequirements,
)
from cobalt_wren.integrations.observability.types import SpanRef
from cobalt_wren.native import NativeArtifact, NativeWorkflowContext, workflow
from tests.support.recording_event_sink import RecordedEvent, RecordingEventSink


def _prepared(
    native_workflow: object,
    kind: str,
) -> tuple[AutomationEngine, EnginePreparedWorkflow]:
    plugin = native_workflow.plugin(  # type: ignore[attr-defined]
        plugin_name=f"{kind}.plugin",
        workflow_kind=kind,
        requirements=WorkflowRequirements(artifact_store=True),
    )
    engine = create_engine(
        {"version": 1, "stores": {"artifact": {"backend": "memory"}}},
        plugins=(plugin,),
        discover_plugins=False,
    )
    return engine, engine.prepare_workflow(kind)


@pytest.mark.parametrize(
    ("content", "expected", "content_type"),
    [
        (b"raw", b"raw", "application/octet-stream"),
        ("hello", b"hello", "text/plain; charset=utf-8"),
        ({"b": 2, "a": 1}, b'{"a":1,"b":2}', "application/json"),
        ([1, "two", None], b'[1,"two",null]', "application/json"),
    ],
)
def test_native_artifact_write_serializes_and_returns_safe_descriptor(
    content: object, expected: bytes, content_type: str
) -> None:
    @workflow(name="Artifact writer")
    async def writer(ctx: NativeWorkflowContext, request: Mapping[str, object]):
        del request
        artifact = await ctx.artifact.write(
            name="report.json",
            content=content,
            kind="report",
            metadata={"classification": "internal"},
        )
        assert isinstance(artifact, NativeArtifact)
        assert not hasattr(artifact, "body")
        return {"storage_key": artifact.storage_key, "size": artifact.size}

    sink = RecordingEventSink()
    engine, prepared = _prepared(writer, "test.native.artifact.write")
    result = prepared.execute(
        {}, context=WorkflowExecutionContext(run_id=71, event_sink=sink)
    )
    stored = engine.read_artifact(str(result.output["storage_key"]))
    assert stored is not None
    assert stored.body == expected
    assert stored.artifact.content_type == content_type
    assert stored.artifact.size == len(expected)
    assert stored.artifact.digest.startswith("sha256:")
    assert sink.run_events[-1].kind == "artifact.created"
    assert expected.decode("utf-8", errors="ignore") not in str(sink.run_events[-1].payload)


def test_native_artifact_metadata_is_defensively_copied_and_redacted() -> None:
    source = {"nested": {"value": "before"}, "api_key": "secret-value"}
    captured: NativeArtifact | None = None

    @workflow(name="Metadata writer")
    async def writer(ctx: NativeWorkflowContext, request: Mapping[str, object]):
        nonlocal captured
        del request
        captured = await ctx.artifact.write(name="meta.json", content={}, metadata=source)
        return {}

    _, prepared = _prepared(writer, "test.native.artifact.metadata")
    prepared.execute({}, context=WorkflowExecutionContext(run_id=72))
    assert captured is not None
    source["nested"]["value"] = "after"  # type: ignore[index]
    nested = captured.metadata["nested"]
    assert isinstance(nested, Mapping)
    assert nested["value"] == "before"
    assert "secret-value" not in str(captured.metadata)
    with pytest.raises(TypeError):
        captured.metadata["new"] = "value"  # type: ignore[index]


def test_native_artifact_requires_run_store_and_safe_name() -> None:
    @workflow(name="Invalid artifact")
    async def writer(ctx: NativeWorkflowContext, request: Mapping[str, object]):
        del request
        await ctx.artifact.write(name="../escape.txt", content="bad")
        return {}

    _, prepared = _prepared(writer, "test.native.artifact.invalid")
    with pytest.raises(RuntimeAssemblyError) as missing_run:
        prepared.execute({}, context=WorkflowExecutionContext())
    assert missing_run.value.code == "WORKFLOW_EXECUTION_FAILED"
    assert isinstance(missing_run.value.__cause__, RuntimeError)
    assert "Run identity" in str(missing_run.value.__cause__)

    with pytest.raises(RuntimeAssemblyError) as unsafe_name:
        prepared.execute({}, context=WorkflowExecutionContext(run_id=73))
    assert unsafe_name.value.code == "WORKFLOW_EXECUTION_FAILED"
    assert isinstance(unsafe_name.value.__cause__, ValueError)
    assert "path separators" in str(unsafe_name.value.__cause__)


def test_native_artifact_json_failure_and_store_failure_are_primary() -> None:
    class BadStore:
        def put(self, request: object) -> object:
            del request
            raise OSError("store unavailable")

    @workflow(name="Serialization failure")
    async def bad_json(ctx: NativeWorkflowContext, request: Mapping[str, object]):
        del request
        await ctx.artifact.write(name="bad.json", content={"bad": object()})
        return {"unexpected": True}

    _, prepared = _prepared(bad_json, "test.native.artifact.bad-json")
    with pytest.raises(RuntimeAssemblyError) as bad_json_error:
        prepared.execute({}, context=WorkflowExecutionContext(run_id=74))
    assert bad_json_error.value.code == "WORKFLOW_EXECUTION_FAILED"
    assert isinstance(bad_json_error.value.__cause__, TypeError)
    assert "not JSON serializable" in str(bad_json_error.value.__cause__)

    context = NativeWorkflowContext(
        build=WorkflowBuildContext(
            workflow_kind="test.native.artifact.bad-store",
            artifact_store=BadStore(),
        ),
        execution=WorkflowExecutionContext(run_id=75),
    )
    with pytest.raises(OSError, match="store unavailable"):
        import asyncio

        asyncio.run(context.artifact.write(name="bad.txt", content="body"))


def test_native_artifact_event_failure_is_secondary_and_idempotent_retry_works() -> None:
    class FailingSink(RecordingEventSink):
        def artifact_created(
            self,
            run_id: int,
            storage_key: str,
            name: str,
            kind: str,
            span: SpanRef | None = None,
            metadata: Mapping[str, Any] | None = None,
            content_type: str = "",
            size: int | None = None,
        ) -> RecordedEvent:
            del run_id, storage_key, name, kind, span, metadata, content_type, size
            raise RuntimeError("sink unavailable")

    @workflow(name="Event failure")
    async def writer(ctx: NativeWorkflowContext, request: Mapping[str, object]):
        del request
        first = await ctx.artifact.write(name="same.json", content={"ok": True})
        second = await ctx.artifact.write(name="same.json", content={"ok": True})
        return {
            "same": first.storage_key == second.storage_key,
            "storage_key": first.storage_key,
        }

    engine, prepared = _prepared(writer, "test.native.artifact.event-failure")
    result = prepared.execute(
        {}, context=WorkflowExecutionContext(run_id=76, event_sink=FailingSink())
    )
    assert result.output["same"] is True
    stored = engine.read_artifact(str(result.output["storage_key"]))
    assert stored is not None
    assert stored.body == b'{"ok":true}'


def test_native_artifact_conflicting_duplicate_is_rejected() -> None:
    @workflow(name="Conflict")
    async def writer(ctx: NativeWorkflowContext, request: Mapping[str, object]):
        del request
        await ctx.artifact.write(name="same.json", content={"value": 1})
        await ctx.artifact.write(name="same.json", content={"value": 2})
        return {}

    _, prepared = _prepared(writer, "test.native.artifact.conflict")
    with pytest.raises(Exception) as excinfo:
        prepared.execute({}, context=WorkflowExecutionContext(run_id=77))
    assert type(excinfo.value).__name__ == "ArtifactConflictError"
