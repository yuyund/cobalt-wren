"""Checkpoint-safe state for the llm_echo_summary reference workflow."""

from __future__ import annotations

from typing import Any, TypedDict


class LlmEchoSummaryState(TypedDict, total=False):
    """Checkpoint-safe state carried through the reference diagnostic workflow."""

    input_summary: dict[str, Any]
    output_payload: dict[str, Any]
    current_node: str
    metadata: dict[str, Any]
    echo: dict[str, Any]
    llm: dict[str, Any]
