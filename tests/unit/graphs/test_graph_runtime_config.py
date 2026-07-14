"""Graph runtime config tests."""

from __future__ import annotations

import logging

from langgraph_automation.graphs.config import (
    GraphRuntimeConfig,
    GraphRuntimeGraphConfig,
    GraphRuntimeLLMConfig,
    GraphRuntimeToolConfig,
)
from langgraph_automation.graphs.runtime import GraphRuntime


def test_graph_runtime_config_types_are_graph_local() -> None:
    config = GraphRuntimeConfig(
        graph=GraphRuntimeGraphConfig(kind='llm_echo_summary'),
        llm=GraphRuntimeLLMConfig(enabled=True, model='test-model', temperature=0.5, max_tokens=128),
        tools=GraphRuntimeToolConfig(allowed_tools=('echo',)),
    )

    runtime = GraphRuntime(logger=logging.getLogger('test-graph-runtime-config'), workflow_config=config)

    assert runtime.workflow_config is config
    assert runtime.workflow_config.graph.kind == 'llm_echo_summary'
    assert runtime.workflow_config.llm.enabled is True
    assert runtime.workflow_config.llm.model == 'test-model'
    assert runtime.workflow_config.llm.temperature == 0.5
    assert runtime.workflow_config.llm.max_tokens == 128
    assert runtime.workflow_config.tools.allowed_tools == ('echo',)
    assert not hasattr(runtime.workflow_config.llm, 'api_key')
    assert not hasattr(runtime.workflow_config.llm, 'base_url')
