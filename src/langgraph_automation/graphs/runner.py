"""LangGraph execution entrypoint used by services."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol, runtime_checkable
import json

from langgraph_automation.core.result_safety import safe_run_error_message
from langgraph_automation.core.summary import summarize_mapping
from langgraph_automation.graphs.builders import build_graph
from langgraph_automation.graphs.runtime import GraphRuntime
from langgraph_automation.integrations.observability import events as obs_events
from langgraph_automation.integrations.observability.failure_policy import suppress_observability_failure


@dataclass(slots=True)
class ExecutionResult:
    """Normalized result returned by graph execution attempts.

    The runner returns execution candidates here. Services are responsible for
    final persistence safety normalization before writing Run.output_payload or
    Run.error_message.
    """

    status: str
    output_payload: dict[str, object] = field(default_factory=dict)
    error_message: str = ''
    last_node_name: str = ''
    message: str = ''
    details: dict[str, object] = field(default_factory=dict)


GraphRunResult = ExecutionResult


@runtime_checkable
class GraphRunner(Protocol):
    def run_graph_once(self, *, run_id: int, runtime: GraphRuntime, input_payload: Mapping[str, object] | None = None) -> ExecutionResult: ...
    def resume_graph_once(self, *, run_id: int, runtime: GraphRuntime, input_payload: Mapping[str, object] | None = None) -> ExecutionResult: ...


class LangGraphRunner:
    """Execute the compiled LangGraph graph once."""

    def _invoke_graph(self, *, run_id: int, runtime: GraphRuntime, phase: str, input_payload: Mapping[str, object] | None) -> ExecutionResult:
        sink = runtime.event_sink
        normalized_input = dict(input_payload or {})
        graph_span = None
        observed_runtime = runtime

        try:
            if sink is not None:
                sink.run_started(run_id, message='run started', payload={'phase': phase})
                graph_span = sink.span_started(
                    run_id,
                    span_type=obs_events.SPAN_GRAPH,
                    name=f'{phase}-graph',
                    node_name='graph',
                    parent=runtime.observability.parent_span,
                    metadata={'phase': phase},
                )
                observed_runtime = runtime.with_parent_span(graph_span, node_name='graph')

            graph = build_graph(observed_runtime)
            initial_state = {
                'input_payload': normalized_input,
                'output_payload': {},
                'current_node': 'graph',
                'messages': [],
                'metadata': {
                    'phase': phase,
                    'run_id': run_id,
                    'thread_id': runtime.observability.thread_id,
                },
            }
            final_state = graph.invoke(initial_state)
        except Exception as primary_exc:
            failure_message = safe_run_error_message(primary_exc)
            if sink is not None and graph_span is not None:
                suppress_observability_failure(
                    lambda: sink.span_failed(
                        graph_span,
                        error_message=failure_message,
                        metadata={'phase': phase},
                    ),
                    context={
                        'component': 'GraphRunner',
                        'operation': 'span_failed',
                        'phase': phase,
                    },
                )
                suppress_observability_failure(
                    lambda: sink.run_failed(
                        run_id,
                        error_message=failure_message,
                        payload={'phase': phase, 'run_id': run_id},
                    ),
                    context={
                        'component': 'GraphRunner',
                        'operation': 'run_failed',
                        'phase': phase,
                    },
                )
            return ExecutionResult(
                status='failed',
                error_message=str(primary_exc),
                last_node_name=observed_runtime.observability.node_name,
                message=f'{phase} failed',
                details={'phase': phase},
            )

        if sink is not None and graph_span is not None:
            sink.span_completed(
                graph_span,
                output_summary=json.dumps(summarize_mapping(final_state.get('output_payload', {})), ensure_ascii=False, sort_keys=True, default=str),
                metrics={'ok': True},
                metadata={'phase': phase},
            )
            sink.run_completed(run_id, message='run completed', payload={'phase': phase, 'run_id': run_id})

        return ExecutionResult(
            status='succeeded',
            output_payload=dict(final_state.get('output_payload', {})),
            last_node_name=str(final_state.get('current_node', '')),
            message=f'{phase} completed',
            details={
                'phase': phase,
                'graph_span_id': None if graph_span is None else graph_span.span_id,
            },
        )

    def run_graph_once(self, *, run_id: int, runtime: GraphRuntime, input_payload: Mapping[str, object] | None = None) -> ExecutionResult:
        return self._invoke_graph(run_id=run_id, runtime=runtime, phase='run', input_payload=input_payload)

    def resume_graph_once(self, *, run_id: int, runtime: GraphRuntime, input_payload: Mapping[str, object] | None = None) -> ExecutionResult:
        raise NotImplementedError('resume_graph_once is not implemented until checkpoint resume semantics are defined; use run_graph_once or retry_run instead')


def build_graph_runner() -> GraphRunner:
    """Return the production graph runner."""

    return LangGraphRunner()
