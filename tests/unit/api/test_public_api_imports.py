"""Public API facade import coverage."""

from __future__ import annotations


def test_llm_api_exports() -> None:
    from langgraph_automation.api.llm import LLMClient, LLMRequest, LLMResult

    assert LLMClient is not None
    assert LLMRequest is not None
    assert LLMResult is not None


def test_tool_api_exports() -> None:
    from langgraph_automation.api.tools import ToolPolicy, ToolPolicyContext, ToolPolicyDecision, ToolRegistry, ToolResult

    assert ToolRegistry is not None
    assert ToolResult is not None
    assert ToolPolicy is not None
    assert ToolPolicyContext is not None
    assert ToolPolicyDecision is not None


def test_store_api_exports() -> None:
    from langgraph_automation.api.stores import ArtifactStore, CheckpointStore

    assert ArtifactStore is not None
    assert CheckpointStore is not None


def test_event_api_exports() -> None:
    from langgraph_automation.api.events import EventSink

    assert EventSink is not None
