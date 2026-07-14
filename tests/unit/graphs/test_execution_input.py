"""Tests for the transient graph execution input boundary."""

from __future__ import annotations

import logging

import pytest

from langgraph_automation.core.errors import MissingRuntimeDependencyError
from langgraph_automation.graphs.inputs import GraphExecutionInput
from langgraph_automation.graphs.runtime import GraphRuntime


def test_graph_execution_input_extracts_primary_text_from_text_and_prompt() -> None:
    execution_input = GraphExecutionInput.from_mapping({'text': '  hello  ', 'prompt': 'fallback'})

    assert execution_input.text == 'hello'
    assert execution_input.prompt == 'fallback'
    assert execution_input.primary_text == 'hello'


def test_graph_execution_input_uses_prompt_when_text_missing() -> None:
    execution_input = GraphExecutionInput.from_mapping({'prompt': '  summarize this  '})

    assert execution_input.text == ''
    assert execution_input.prompt == 'summarize this'
    assert execution_input.primary_text == 'summarize this'


def test_graph_runtime_requires_execution_input() -> None:
    runtime = GraphRuntime(logger=logging.getLogger('test.execution-input'))

    with pytest.raises(MissingRuntimeDependencyError, match='Execution input'):
        runtime.require_execution_input()
