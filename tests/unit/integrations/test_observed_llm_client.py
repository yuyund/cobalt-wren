"""Observed LLM client tests."""

from __future__ import annotations

import json
import logging

import pytest

from langgraph_automation.graphs.runtime import GraphRuntime
from langgraph_automation.integrations.llm.base import LLMResult
from langgraph_automation.integrations.llm.observed_client import ObservedLLMClient
from langgraph_automation.integrations.observability.types import ObservabilityContext, SpanRef
from tests.support.failing_event_sink import FailingSpanFailedEventSink
from tests.support.llm_doubles import FailingLLMClient, RecordingLLMClient
from tests.support.recording_event_sink import RecordingEventSink


def test_observed_llm_client_records_successful_call() -> None:
    sink = RecordingEventSink()
    inner = RecordingLLMClient(
        result=LLMResult(
            content='Response with token=secret and path /tmp/out.txt',
            raw={'provider_response': 'hidden', 'authorization': 'Bearer secret'},
            provider='demo-provider',
            model='demo-model',
            input_tokens=3,
            output_tokens=2,
        ),
    )
    client = ObservedLLMClient(
        inner=inner,
        event_sink=sink,
        observability=ObservabilityContext(run_id=42, thread_id='thread-1', parent_span=SpanRef('span-parent'), node_name='planner'),
    )

    result = client.complete(
        [
            {'role': 'system', 'content': 'Authorization: Bearer abcdefghijklmnop'},
            {'role': 'user', 'content': 'summarize path /tmp/private.txt'},
        ],
        temperature=0.2,
    )

    assert result is inner.result
    assert len(inner.calls) == 1
    assert inner.calls[0].kwargs == {'temperature': 0.2}

    span = sink.spans['span-1']
    assert span.span_type == 'llm'
    assert span.name == 'llm:demo-model'
    assert span.node_name == 'planner'
    assert span.parent_id == 'span-parent'
    assert span.started_metadata['provider'] == 'demo-provider'
    assert span.started_metadata['model'] == 'demo-model'
    assert span.started_metadata['input_summary']['message_count'] == 2
    assert span.started_metadata['input_summary']['roles'] == ['system', 'user']
    assert 'abcdefghijklmnop' not in span.started_metadata['input_summary']['preview']
    assert 'REDACTED' in span.started_metadata['input_summary']['preview']

    output_summary = json.loads(span.output_summary)
    assert output_summary['length'] == len(inner.result.content)
    assert 'secret' not in output_summary['preview'].lower()
    assert '/tmp/' not in output_summary['preview']
    assert span.metrics == {'input_tokens': 3, 'output_tokens': 2, 'total_tokens': 5}
    assert span.metadata == {'provider': 'demo-provider', 'model': 'demo-model'}


def test_observed_llm_client_records_failures_without_swallowing_exceptions() -> None:
    sink = RecordingEventSink()
    inner = FailingLLMClient(ValueError('Authorization: Bearer secret'))
    client = ObservedLLMClient(
        inner=inner,
        event_sink=sink,
        observability=ObservabilityContext(run_id=7, thread_id='thread-2', parent_span=SpanRef('span-parent'), node_name='planner'),
    )

    with pytest.raises(ValueError):
        client.complete([{'role': 'user', 'content': 'trigger failure'}])

    assert len(inner.calls) == 1
    span = sink.spans['span-1']
    assert span.status == 'failed'
    assert 'Bearer secret' not in span.error_message
    assert span.metadata == {'provider': 'unknown', 'model': 'unknown'}


def test_observed_llm_client_preserves_primary_exception_when_span_failed_fails(caplog: pytest.LogCaptureFixture) -> None:
    sink = FailingSpanFailedEventSink(RuntimeError('Authorization: Bearer secret-token /tmp/leak.txt'))
    inner = FailingLLMClient(ValueError('primary llm failure'))
    client = ObservedLLMClient(
        inner=inner,
        event_sink=sink,
        observability=ObservabilityContext(run_id=8, thread_id='thread-2', parent_span=SpanRef('span-parent'), node_name='planner'),
    )

    caplog.set_level(logging.WARNING)
    with pytest.raises(ValueError, match='primary llm failure'):
        client.complete([{'role': 'user', 'content': 'trigger failure'}])

    assert 'Observability failure suppressed' in caplog.text
    assert 'secret-token' not in caplog.text
    assert '/tmp/leak.txt' not in caplog.text


def test_observed_llm_client_rebinds_context_without_mutating_original() -> None:
    sink = RecordingEventSink()
    inner = RecordingLLMClient()
    original = ObservedLLMClient(
        inner=inner,
        event_sink=sink,
        observability=ObservabilityContext(run_id=11, thread_id='thread-3', parent_span=SpanRef('span-original'), node_name='planner'),
    )

    rebound = original.with_observability_context(
        ObservabilityContext(run_id=11, thread_id='thread-3', parent_span=SpanRef('span-rebound'), node_name='summarizer'),
    )

    assert rebound is not original
    assert rebound.inner is original.inner
    assert rebound.event_sink is original.event_sink
    assert rebound.observability.parent_span == SpanRef('span-rebound')
    assert rebound.observability.node_name == 'summarizer'
    assert original.observability.parent_span == SpanRef('span-original')
    assert original.observability.node_name == 'planner'


def test_observed_llm_client_rebinds_through_graph_runtime() -> None:
    sink = RecordingEventSink()
    inner = RecordingLLMClient()
    observed = ObservedLLMClient(
        inner=inner,
        event_sink=sink,
        observability=ObservabilityContext(run_id=19, thread_id='thread-4'),
    )
    runtime = GraphRuntime(
        logger=logging.getLogger('test.observed.llm.runtime'),
        observability=ObservabilityContext(run_id=19, thread_id='thread-4'),
        event_sink=sink,
        llm_client=observed,
    )
    graph_span = sink.span_started(19, 'graph', 'graph', node_name='graph')

    rebound_runtime = runtime.with_parent_span(graph_span, node_name='planner')
    rebound_client = rebound_runtime.require_llm_client()
    result = rebound_client.complete([{'role': 'user', 'content': 'hello'}])

    assert result is inner.result
    assert rebound_client.observability.parent_span == graph_span
    assert rebound_client.observability.node_name == 'planner'
    assert runtime.require_llm_client().observability.parent_span is None
    llm_span = sink.spans['span-2']
    assert llm_span.parent_id == graph_span.span_id
    assert llm_span.node_name == 'planner'
