"""Safe toy tool tests."""

from __future__ import annotations

from cobalt_wren.integrations.tools.safe_tools import ECHO_TOOL_NAME, EchoTool


def test_echo_tool_returns_bounded_redacted_result() -> None:
    tool = EchoTool()

    result = tool(text='Authorization: Bearer secret-token /tmp/secret.txt')

    assert result.exit_code == 0
    assert result.metadata['tool_name'] == ECHO_TOOL_NAME
    assert result.metadata['input_type'] == 'str'
    assert result.metadata['arg_keys'] == ['text']
    assert len(result.output_summary) <= 300
    assert 'secret-token' not in result.output_summary
    assert '/tmp/secret.txt' not in result.output_summary
    assert result.output == result.output_summary


def test_echo_tool_handles_non_string_input_without_leaking_raw_kwargs() -> None:
    tool = EchoTool()

    result = tool(text={'api_key': 'secret-value', 'nested': ['/tmp/secret.txt', 'ok']})

    assert result.exit_code == 0
    assert result.metadata['tool_name'] == ECHO_TOOL_NAME
    assert result.metadata['input_type'] == 'dict'
    assert result.metadata['arg_keys'] == ['text']
    assert len(result.output_summary) <= 300
    assert 'secret-value' not in result.output_summary
    assert '/tmp/secret.txt' not in result.output_summary
