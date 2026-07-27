"""Observed tool registry tests."""

from __future__ import annotations

import logging

import json

import pytest

from cobalt_wren.integrations.observability.types import ObservabilityContext, SpanRef
from cobalt_wren.integrations.tools.base import ToolResult
from cobalt_wren.integrations.tools.observed_registry import ObservedToolRegistry
from cobalt_wren.integrations.tools.registry import InMemoryToolRegistry
from tests.support.failing_event_sink import FailingSpanFailedEventSink
from tests.support.recording_event_sink import RecordingEventSink
from tests.support.tool_doubles import FailingToolCallable, RecordingToolCallable


def test_observed_tool_registry_records_successful_tool_calls() -> None:
    sink = RecordingEventSink()
    inner = InMemoryToolRegistry()
    calls: list[dict[str, object]] = []
    inner.register(
        'report',
        RecordingToolCallable(
            result=ToolResult(
                output='stdout with path /tmp/secret.txt and token=abcd',
                output_summary='',
                exit_code=0,
                metadata={'path': '/tmp/secret.txt', 'authorization': 'Bearer secret'},
            ),
            calls=calls,
        ),
    )
    registry = ObservedToolRegistry(
        inner=inner,
        event_sink=sink,
        observability=ObservabilityContext(run_id=21, thread_id='thread-1', parent_span=SpanRef('span-parent'), node_name='executor'),
    )

    result = registry.run('report', path='/tmp/secret.txt', limit=3, api_key='Bearer 1234567890')

    assert result.output == 'stdout with path /tmp/secret.txt and token=abcd'
    assert calls == [{'path': '/tmp/secret.txt', 'limit': 3, 'api_key': 'Bearer 1234567890'}]

    span = sink.spans['span-1']
    assert span.span_type == 'tool'
    assert span.name == 'tool:report'
    assert span.node_name == 'executor'
    assert span.parent_id == 'span-parent'
    assert span.started_metadata['tool_name'] == 'report'
    assert span.started_metadata['input_summary']['tool_name'] == 'report'
    assert span.started_metadata['input_summary']['arg_keys'] == ['api_key', 'limit', 'path']
    assert 'secret.txt' not in str(span.started_metadata['input_summary'])
    assert 'Bearer' not in str(span.started_metadata['input_summary'])

    output_summary = json.loads(span.output_summary)
    assert output_summary['exit_code'] == 0
    assert output_summary['length'] > 0
    assert '/tmp/secret.txt' not in output_summary['preview']
    assert 'token' not in output_summary['preview'].lower() or 'REDACTED' in output_summary['preview']
    assert span.metrics == {'exit_code': 0}
    assert span.metadata['tool_name'] == 'report'
    assert '/tmp/secret.txt' not in str(span.metadata)
    assert 'authorization' not in str(span.metadata).lower()


def test_observed_tool_registry_marks_failed_tool_results_without_raising() -> None:
    sink = RecordingEventSink()
    inner = InMemoryToolRegistry()
    inner.register(
        'broken',
        RecordingToolCallable(
            result=ToolResult(
                output='stdout',
                output_summary='failed output /tmp/secret.txt',
                exit_code=1,
                metadata={'path': '/tmp/secret.txt'},
                error_message='Authorization: Bearer secret',
            ),
        ),
    )
    registry = ObservedToolRegistry(
        inner=inner,
        event_sink=sink,
        observability=ObservabilityContext(run_id=22, thread_id='thread-2', parent_span=SpanRef('span-parent'), node_name='executor'),
    )

    result = registry.run('broken', path='/tmp/secret.txt')

    assert result.exit_code == 1
    span = sink.spans['span-1']
    assert span.status == 'failed'
    assert 'Bearer secret' not in span.error_message
    assert span.metrics == {'exit_code': 1}
    assert span.output_summary == ''


def test_observed_tool_registry_preserves_primary_exception_when_span_failed_fails(caplog: pytest.LogCaptureFixture) -> None:
    sink = FailingSpanFailedEventSink(RuntimeError('Authorization: Bearer secret-token /tmp/leak.txt'))
    inner = InMemoryToolRegistry()
    inner.register('explode', FailingToolCallable(ValueError('primary tool failure')))
    registry = ObservedToolRegistry(
        inner=inner,
        event_sink=sink,
        observability=ObservabilityContext(run_id=23, thread_id='thread-3', parent_span=SpanRef('span-parent'), node_name='executor'),
    )

    caplog.set_level(logging.WARNING)
    with pytest.raises(ValueError, match='primary tool failure'):
        registry.run('explode', token='abc')

    assert 'Observability failure suppressed' in caplog.text
    assert 'secret-token' not in caplog.text
    assert '/tmp/leak.txt' not in caplog.text


def test_observed_tool_registry_preserves_failed_tool_result_when_span_failed_fails(caplog: pytest.LogCaptureFixture) -> None:
    sink = FailingSpanFailedEventSink(RuntimeError('Authorization: Bearer secret-token /tmp/leak.txt'))
    inner = InMemoryToolRegistry()
    inner.register(
        'broken',
        RecordingToolCallable(
            result=ToolResult(
                output='stdout',
                output_summary='failed output /tmp/secret.txt',
                exit_code=1,
                metadata={'path': '/tmp/secret.txt'},
                error_message='Authorization: Bearer secret',
            ),
        ),
    )
    registry = ObservedToolRegistry(
        inner=inner,
        event_sink=sink,
        observability=ObservabilityContext(run_id=24, thread_id='thread-4', parent_span=SpanRef('span-parent'), node_name='executor'),
    )

    caplog.set_level(logging.WARNING)
    result = registry.run('broken', path='/tmp/secret.txt')

    assert result.exit_code == 1
    assert result.error_message == 'Authorization: Bearer secret'
    assert 'Observability failure suppressed' in caplog.text
    assert 'secret-token' not in caplog.text
    assert '/tmp/leak.txt' not in caplog.text


def test_observed_tool_registry_rebinds_context_without_mutating_original() -> None:
    sink = RecordingEventSink()
    inner = InMemoryToolRegistry()
    inner.register('echo', RecordingToolCallable(result=ToolResult(output='ok', exit_code=0)))
    original = ObservedToolRegistry(
        inner=inner,
        event_sink=sink,
        observability=ObservabilityContext(run_id=25, thread_id='thread-4', parent_span=SpanRef('span-original'), node_name='executor'),
    )

    rebound = original.with_observability_context(
        ObservabilityContext(run_id=25, thread_id='thread-4', parent_span=SpanRef('span-rebound'), node_name='planner'),
    )

    assert rebound is not original
    assert rebound.inner is original.inner
    assert rebound.event_sink is original.event_sink
    assert rebound.observability.parent_span == SpanRef('span-rebound')
    assert rebound.observability.node_name == 'planner'
    assert original.observability.parent_span == SpanRef('span-original')
    assert original.observability.node_name == 'executor'


def test_observed_tool_registry_rebinds_to_parent_span_context() -> None:
    sink = RecordingEventSink()
    inner = InMemoryToolRegistry()
    inner.register("echo", RecordingToolCallable(result=ToolResult(output="ok", exit_code=0)))
    observed = ObservedToolRegistry(
        inner=inner,
        event_sink=sink,
        observability=ObservabilityContext(run_id=26, thread_id="thread-5"),
    )
    graph_span = sink.span_started(26, "graph", "graph", node_name="graph")
    rebound_registry = observed.with_observability_context(
        observed.observability.with_parent_span(graph_span, "executor")
    )

    result = rebound_registry.run("echo", path="/tmp/secret.txt")

    assert result.output == "ok"
    assert rebound_registry.observability.parent_span == graph_span
    assert rebound_registry.observability.node_name == "executor"
    assert observed.observability.parent_span is None
    tool_span = sink.spans["span-2"]
    assert tool_span.parent_id == graph_span.span_id
    assert tool_span.node_name == "executor"
