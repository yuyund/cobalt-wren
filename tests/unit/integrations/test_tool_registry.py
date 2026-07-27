"""Tool registry tests."""

from __future__ import annotations

import pytest

from cobalt_wren.integrations.tools.base import ToolResult
from cobalt_wren.integrations.tools.registry import InMemoryToolRegistry


def test_in_memory_tool_registry_registers_and_runs_tools() -> None:
    registry = InMemoryToolRegistry()
    calls: list[dict[str, object]] = []

    def echo_tool(**kwargs: object) -> ToolResult:
        calls.append(dict(kwargs))
        return ToolResult(output=kwargs, output_summary='ok', metadata={'name': 'echo'})

    registry.register('echo', echo_tool)

    result = registry.run('echo', message='hello', count=2)

    assert calls == [{'message': 'hello', 'count': 2}]
    assert isinstance(result, ToolResult)
    assert result.output == {'message': 'hello', 'count': 2}
    assert result.output_summary == 'ok'
    assert result.metadata == {'name': 'echo'}


def test_in_memory_tool_registry_wraps_non_tool_result_values() -> None:
    registry = InMemoryToolRegistry()

    def plain_tool(**kwargs: object) -> str:
        return f"value:{kwargs['limit']}"

    registry.register('plain', plain_tool)

    result = registry.run('plain', limit=3)

    assert result.output == 'value:3'
    assert result.output_summary == 'value:3'
    assert result.exit_code == 0
    assert result.metadata == {'tool_name': 'plain'}


def test_in_memory_tool_registry_missing_tool_raises_key_error() -> None:
    registry = InMemoryToolRegistry()

    with pytest.raises(KeyError):
        registry.run('missing')


def test_in_memory_tool_registry_does_not_swallow_exceptions() -> None:
    registry = InMemoryToolRegistry()

    def boom(**kwargs: object) -> ToolResult:
        raise RuntimeError('boom')

    registry.register('boom', boom)

    with pytest.raises(RuntimeError):
        registry.run('boom', token='abc')
