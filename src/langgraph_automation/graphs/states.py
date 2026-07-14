"""LangGraph state definitions."""

from __future__ import annotations

from typing import Any, TypedDict


class AutomationState(TypedDict, total=False):
    """Minimal state carried through the LangGraph compiled graph."""

    input_payload: dict[str, Any]
    output_payload: dict[str, Any]
    current_node: str
    messages: list[dict[str, Any]]
    metadata: dict[str, Any]
    echo: dict[str, Any]
    llm: dict[str, Any]
