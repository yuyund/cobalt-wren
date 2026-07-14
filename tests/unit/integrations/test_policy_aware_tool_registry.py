"""Policy-aware tool registry tests."""

from __future__ import annotations

import pytest

from langgraph_automation.integrations.observability.types import ObservabilityContext
from langgraph_automation.integrations.tools.base import ToolResult
from langgraph_automation.integrations.tools.policy import AllowlistToolPolicy, POLICY_DENIED_EXIT_CODE, ToolPolicyContext
from langgraph_automation.integrations.tools.policy_registry import PolicyAwareToolRegistry
from langgraph_automation.integrations.tools.registry import InMemoryToolRegistry
from tests.support.recording_event_sink import RecordingEventSink
from tests.support.tool_doubles import FailingToolCallable, RecordingToolCallable


def test_policy_aware_tool_registry_allows_and_delegates() -> None:
    inner = InMemoryToolRegistry()
    calls: list[dict[str, object]] = []
    inner.register('allowed', RecordingToolCallable(result=ToolResult(output='ok', exit_code=0), calls=calls))
    registry = PolicyAwareToolRegistry(
        inner=inner,
        policy=AllowlistToolPolicy(allowed_tools=frozenset({'allowed'})),
        context=ToolPolicyContext(run_id=1, workflow_id=2, thread_id='thread-1'),
    )

    result = registry.run('allowed', path='/tmp/output.txt', limit=3)

    assert result.output == 'ok'
    assert calls == [{'path': '/tmp/output.txt', 'limit': 3}]


def test_policy_aware_tool_registry_denies_without_calling_inner() -> None:
    inner = InMemoryToolRegistry()
    inner.register('blocked', FailingToolCallable(RuntimeError('inner should not run')))
    registry = PolicyAwareToolRegistry(
        inner=inner,
        policy=AllowlistToolPolicy(allowed_tools=frozenset({'allowed'})),
        context=ToolPolicyContext(run_id=1, workflow_id=2, thread_id='thread-1'),
    )

    result = registry.run('blocked', api_key='secret-value', path='/tmp/secret.txt')

    assert result.exit_code == POLICY_DENIED_EXIT_CODE
    assert result.error_message
    assert result.metadata['policy_denied'] is True
    assert result.metadata['policy_error_code'] == 'tool_policy_denied'
    assert 'secret-value' not in str(result.metadata)


def test_policy_aware_tool_registry_propagates_policy_exceptions() -> None:
    class ExplodingPolicy:
        def authorize(self, name, kwargs, context):  # type: ignore[no-untyped-def]
            raise ValueError('policy failure')

    inner = InMemoryToolRegistry()
    inner.register('allowed', FailingToolCallable(RuntimeError('inner should not run')))
    registry = PolicyAwareToolRegistry(
        inner=inner,
        policy=ExplodingPolicy(),
        context=ToolPolicyContext(run_id=1, workflow_id=2, thread_id='thread-1'),
    )

    with pytest.raises(ValueError, match='policy failure'):
        registry.run('allowed', path='/tmp/output.txt')


def test_policy_aware_tool_registry_composes_with_observed_registry() -> None:
    from langgraph_automation.integrations.tools.observed_registry import ObservedToolRegistry

    sink = RecordingEventSink()
    inner = InMemoryToolRegistry()
    inner.register('allowed', RecordingToolCallable(result=ToolResult(output='ok', exit_code=0)))
    registry = ObservedToolRegistry(
        inner=PolicyAwareToolRegistry(
            inner=inner,
            policy=AllowlistToolPolicy(allowed_tools=frozenset({'other'})),
            context=ToolPolicyContext(run_id=1, workflow_id=2, thread_id='thread-1'),
        ),
        event_sink=sink,
        observability=ObservabilityContext(run_id=1, thread_id='thread-1'),
    )

    result = registry.run('allowed', path='/tmp/secret.txt')

    assert result.exit_code == POLICY_DENIED_EXIT_CODE
    assert sink.spans['span-1'].status == 'failed'
    assert sink.spans['span-1'].error_message
