"""Public API facade import coverage."""

from __future__ import annotations


def test_llm_api_exports() -> None:
    from langgraph_automation.api.llm import LLMClient, LLMRequest, LLMResult

    assert LLMClient is not None
    assert LLMRequest is not None
    assert LLMResult is not None


def test_llm_api_all() -> None:
    import langgraph_automation.api.llm as llm_api

    assert set(llm_api.__all__) == {'LLMClient', 'LLMRequest', 'LLMResult'}


def test_tool_api_exports() -> None:
    from langgraph_automation.api.tools import ToolPolicy, ToolPolicyContext, ToolPolicyDecision, ToolRegistry, ToolResult

    assert ToolRegistry is not None
    assert ToolResult is not None
    assert ToolPolicy is not None
    assert ToolPolicyContext is not None
    assert ToolPolicyDecision is not None


def test_tool_api_all() -> None:
    import langgraph_automation.api.tools as tools_api

    assert set(tools_api.__all__) == {'ToolRegistry', 'ToolResult', 'ToolPolicy', 'ToolPolicyContext', 'ToolPolicyDecision'}


def test_store_api_exports() -> None:
    from langgraph_automation.api.stores import ArtifactStore, CheckpointStore

    assert ArtifactStore is not None
    assert CheckpointStore is not None


def test_store_api_all() -> None:
    import langgraph_automation.api.stores as stores_api

    assert set(stores_api.__all__) == {'ArtifactStore', 'CheckpointStore'}


def test_event_api_exports() -> None:
    from langgraph_automation.api.events import EventSink

    assert EventSink is not None


def test_event_api_all() -> None:
    import langgraph_automation.api.events as events_api

    assert set(events_api.__all__) == {'EventSink'}
