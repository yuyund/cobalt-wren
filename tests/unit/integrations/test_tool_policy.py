"""Tool policy foundation tests."""

from __future__ import annotations

from langgraph_automation.integrations.tools.base import ToolResult
from langgraph_automation.integrations.tools.policy import (
    AllowlistToolPolicy,
    POLICY_DENIED_ERROR_CODE,
    POLICY_DENIED_EXIT_CODE,
    ToolPolicyContext,
    ToolPolicyDecision,
    build_policy_denied_result,
)


def test_tool_policy_context_does_not_carry_allowlist_configuration() -> None:
    assert 'allowed_tools' not in ToolPolicyContext.__dataclass_fields__


def test_allowlist_tool_policy_allows_known_tools() -> None:
    policy = AllowlistToolPolicy(allowed_tools=frozenset({'allowed'}))

    decision = policy.authorize('allowed', {'token': 'secret'}, ToolPolicyContext(run_id=1, workflow_id=2, thread_id='thread-1'))

    assert decision.allowed is True
    assert decision.code == 'tool_allowed'
    assert decision.reason == 'Tool is allowed by policy.'
    assert decision.metadata['tool_name'] == 'allowed'


def test_allowlist_tool_policy_denies_unknown_tools_without_exposing_kwargs() -> None:
    policy = AllowlistToolPolicy(allowed_tools=frozenset({'allowed'}))

    decision = policy.authorize('blocked', {'api_key': 'secret-value', 'path': '/tmp/secret.txt'}, ToolPolicyContext(run_id=1, workflow_id=2, thread_id='thread-1'))

    assert decision.allowed is False
    assert decision.code == 'tool_not_allowed'
    assert decision.reason
    assert decision.metadata['tool_name'] == 'blocked'
    assert 'api_key' not in str(decision.metadata)
    assert 'secret-value' not in str(decision.metadata)


def test_build_policy_denied_result_redacts_metadata_and_sets_denial_fields() -> None:
    decision = ToolPolicyDecision(
        allowed=False,
        code='tool_not_allowed',
        reason='denied for api_key=secret token=secret-token /tmp/secret.txt',
        metadata={
            'api_key': 'secret-value',
            'token': 'secret-token',
            'safe': 'value',
        },
    )

    result = build_policy_denied_result(tool_name='blocked', decision=decision)

    assert isinstance(result, ToolResult)
    assert result.exit_code == POLICY_DENIED_EXIT_CODE
    assert result.error_message
    assert result.output_summary
    assert result.metadata['tool_name'] == 'blocked'
    assert result.metadata['policy_denied'] is True
    assert result.metadata['policy_error_code'] == POLICY_DENIED_ERROR_CODE
    assert result.metadata['policy_code'] == 'tool_not_allowed'
    assert 'secret-value' not in str(result.metadata)
    assert 'secret-token' not in str(result.metadata)
    assert 'api_key' not in str(result.metadata)
    assert 'token' not in str(result.metadata)
    assert 'secret-value' not in result.error_message
    assert 'secret-token' not in result.error_message
    assert '/tmp/secret.txt' not in result.error_message
    assert '***REDACTED***' in result.metadata['policy_metadata']['keys']
    assert 'blocked' in result.output_summary
    assert 'denied' in result.error_message
