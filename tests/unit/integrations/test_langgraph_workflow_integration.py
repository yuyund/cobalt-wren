"""Official LangGraph workflow integration tests."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from cobalt_wren.api.integrations import IntegrationContext
from cobalt_wren.api.workflow import WorkflowExecutionContext, WorkflowResumeRequest
from cobalt_wren.integrations.langgraph import integrate_langgraph
from cobalt_wren.integrations.observability.types import SpanRef
from tests.support.recording_event_sink import RecordingEventSink
from cobalt_wren.integrations.workflows.definitions import LANGGRAPH_INTEGRATION
from cobalt_wren.integrations.workflows.langgraph_provider import LANGGRAPH_PROVIDER


class _State(TypedDict, total=False):
    value: int
    output: dict[str, object]


class _Sink:
    def __init__(self) -> None:
        self.started: list[dict[str, object]] = []
        self.completed: list[dict[str, object]] = []
        self.failed: list[dict[str, object]] = []

    def span_started(self, run_id: int, span_type: str, name: str, node_name: str | None = None, parent: SpanRef | None = None, metadata: Mapping[str, Any] | None = None) -> SpanRef:
        self.started.append({"run_id": run_id, "span_type": span_type, "name": name, "node_name": node_name, "parent": parent, "metadata": dict(metadata or {})})
        return SpanRef(span_id=str(len(self.started)))

    def span_completed(self, span: SpanRef, output_summary: str | None = None, metrics: Mapping[str, Any] | None = None, metadata: Mapping[str, Any] | None = None) -> None:
        self.completed.append({"span": span, "output_summary": output_summary, "metrics": dict(metrics or {}), "metadata": dict(metadata or {})})

    def span_failed(self, span: SpanRef, error_message: str, metrics: Mapping[str, Any] | None = None, metadata: Mapping[str, Any] | None = None) -> None:
        self.failed.append({"span": span, "error_message": error_message, "metrics": dict(metrics or {}), "metadata": dict(metadata or {})})


def _graph():
    def increment(state: _State) -> _State:
        return {"value": state.get("value", 0) + 1}

    def finalize(state: _State) -> _State:
        return {"output": {"answer": state["value"]}}

    graph = StateGraph(_State)
    graph.add_node("increment", increment)
    graph.add_node("finalize", finalize)
    graph.add_edge(START, "increment")
    graph.add_edge("increment", "finalize")
    graph.add_edge("finalize", END)
    return graph.compile(name="integration-test")


def test_langgraph_definition_is_central_and_experimental() -> None:
    assert LANGGRAPH_PROVIDER.definition is LANGGRAPH_INTEGRATION
    assert LANGGRAPH_INTEGRATION.integration_id == "langgraph"
    assert LANGGRAPH_INTEGRATION.capability("node_observability") is not None
    assert LANGGRAPH_INTEGRATION.capability("resume") is not None


def test_langgraph_provider_wraps_and_projects_nodes() -> None:
    sink = _Sink()
    executable = LANGGRAPH_PROVIDER.wrap(
        _graph(),
        context=IntegrationContext(
            workflow_kind="acme.langgraph",
            config={"output_key": "output"},
        ),
    )

    result = executable.execute(
        {"value": 1},
        context=WorkflowExecutionContext(
            run_id=7,
            thread_id="thread-7",
            event_sink=sink,
            parent_span=SpanRef("root"),
        ),
    )

    assert result.output == {"answer": 2}
    assert result.metadata["integration_id"] == "langgraph"
    assert result.metadata["completed_nodes"] == ["increment", "finalize"]
    assert [item["name"] for item in sink.started] == ["increment", "finalize"]
    assert len(sink.completed) == 2
    assert sink.failed == []
    assert sink.started[0]["parent"] == SpanRef("root")
    assert sink.started[0]["metadata"]["integration_id"] == "langgraph"


def test_integrate_langgraph_is_thin_convenience_helper() -> None:
    executable = integrate_langgraph(
        _graph(),
        workflow_kind="acme.langgraph",
        output_key="output",
    )

    result = executable.execute(
        {"value": 4},
        context=WorkflowExecutionContext(thread_id="thread"),
    )

    assert result.output == {"answer": 5}


def test_langgraph_provider_rejects_non_stream_target() -> None:
    try:
        LANGGRAPH_PROVIDER.wrap(
            object(),
            context=IntegrationContext(workflow_kind="invalid"),
        )
    except TypeError as exc:
        assert "stream" in str(exc)
    else:
        raise AssertionError("target without stream must be rejected")


def test_langgraph_interrupt_and_resume_are_normalized() -> None:
    class ApprovalState(TypedDict, total=False):
        decision: object

    def approval(state: ApprovalState) -> ApprovalState:
        del state
        return {"decision": interrupt({"kind": "approval", "allowed": ["approve"]})}

    graph = StateGraph(ApprovalState)
    graph.add_node("approval", approval)
    graph.add_edge(START, "approval")
    graph.add_edge("approval", END)
    executable = integrate_langgraph(
        graph.compile(checkpointer=InMemorySaver()),
        workflow_kind="acme.approval",
    )
    context = WorkflowExecutionContext(thread_id="approval-thread")

    paused = executable.execute({}, context=context)

    assert paused.status == "paused"
    assert paused.metadata["interrupt_count"] == 1
    assert paused.output["allowed_actions"] == ["resume"]
    assert len(paused.output["interrupts"]) == 1

    resumed = executable.resume(
        WorkflowResumeRequest(value={"decision": "approve"}),
        context=context,
    )

    assert resumed.status == "completed"
    assert resumed.output == {"decision": {"decision": "approve"}}
    assert resumed.metadata["resumed"] is True


def test_langgraph_node_failure_closes_started_span() -> None:
    class FailureState(TypedDict, total=False):
        value: int

    def fail(state: FailureState) -> FailureState:
        del state
        raise ValueError("unsafe detail should be normalized")

    graph = StateGraph(FailureState)
    graph.add_node("fail", fail)
    graph.add_edge(START, "fail")
    graph.add_edge("fail", END)
    sink = _Sink()
    executable = integrate_langgraph(
        graph.compile(),
        workflow_kind="acme.failure",
    )

    try:
        executable.execute(
            {},
            context=WorkflowExecutionContext(run_id=9, event_sink=sink),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("node failure must propagate")

    assert [item["name"] for item in sink.started] == ["fail"]
    assert len(sink.failed) == 1
    assert sink.completed == []


def test_langgraph_provider_emits_versioned_task_projections() -> None:
    sink = RecordingEventSink()
    executable = integrate_langgraph(
        _graph(),
        workflow_kind="acme.projection",
        output_key="output",
    )

    result = executable.execute(
        {"value": 2},
        context=WorkflowExecutionContext(run_id=11, thread_id="projection", event_sink=sink),
    )

    assert result.output == {"answer": 3}
    task_records = [item for item in sink.integration_projections if item["schema_id"] == "langgraph.task.v1"]
    assert len(task_records) == 4
    assert {item["payload"]["status"] for item in task_records} == {"running", "succeeded"}
    assert all(item["owner_kind"] == "execution_unit" for item in task_records)
