"""Execution nodes for the llm_echo_summary reference diagnostic workflow."""

from __future__ import annotations

from typing import Any

from langgraph_automation.graphs.runtime import GraphRuntime
from langgraph_automation.integrations.tools.policy import POLICY_DENIED_EXIT_CODE

from .state import LlmEchoSummaryState

ECHO_TOOL_NAME = 'echo'


def _input_text(runtime: GraphRuntime) -> str:
    execution_input = runtime.require_execution_input()
    return execution_input.primary_text


def _echo_status(exit_code: int) -> str:
    if exit_code == 0:
        return 'succeeded'
    if exit_code == POLICY_DENIED_EXIT_CODE:
        return 'denied'
    return 'failed'


def echo_tool_node(state: LlmEchoSummaryState, runtime: GraphRuntime) -> LlmEchoSummaryState:
    tool_registry = runtime.require_tool_registry()
    input_text = _input_text(runtime)
    result = tool_registry.run(ECHO_TOOL_NAME, text=input_text)
    status = _echo_status(result.exit_code)
    echo = {
        'status': status,
        'output_summary': result.output_summary,
    }
    metadata = dict(state.get('metadata', {}))
    metadata['echo'] = echo
    output_payload = dict(state.get('output_payload', {}))
    output_payload['echo'] = echo
    return {
        'current_node': 'echo',
        'metadata': metadata,
        'output_payload': output_payload,
        'echo': echo,
    }


def llm_summary_node(state: LlmEchoSummaryState, runtime: GraphRuntime) -> LlmEchoSummaryState:
    llm_client = runtime.require_llm_client()
    input_text = _input_text(runtime)
    echo = dict(state.get('echo', {}))
    echo_summary = echo.get('output_summary', '')
    messages: list[dict[str, Any]] = [
        {
            'role': 'system',
            'content': 'Summarize the user input concisely. Do not expose secrets or raw credentials if present.',
        },
        {
            'role': 'user',
            'content': input_text,
        },
    ]
    if echo_summary:
        messages.insert(
            1,
            {
                'role': 'system',
                'content': f'EchoTool summary: {echo_summary}',
            },
        )
    llm_result = llm_client.complete(messages)
    summary = llm_result.content
    output_payload = {
        'summary': summary,
        'echo': echo,
        'llm': {
            'provider': llm_result.provider,
            'model': llm_result.model,
            'input_tokens': llm_result.input_tokens,
            'output_tokens': llm_result.output_tokens,
        },
    }
    metadata = dict(state.get('metadata', {}))
    metadata['llm'] = output_payload['llm']
    return {
        'current_node': 'llm_summary',
        'metadata': metadata,
        'output_payload': output_payload,
        'llm': output_payload['llm'],
    }
