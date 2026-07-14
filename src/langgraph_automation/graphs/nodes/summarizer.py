"""Summarizer node."""

from __future__ import annotations

from langgraph_automation.graphs.runtime import GraphRuntime
from langgraph_automation.graphs.states import AutomationState


def summarizer_node(state: AutomationState, runtime: GraphRuntime) -> AutomationState:
    input_payload = dict(state.get("input_payload", {}))
    metadata = dict(state.get("metadata", {}))
    plan = dict(metadata.get("plan", {}))
    output_payload = {
        "run_id": runtime.observability.run_id,
        "phase": metadata.get("phase", "run"),
        "summary": "minimal LangGraph execution completed",
        "input_payload": input_payload,
        "plan": plan,
    }
    metadata["summary"] = output_payload["summary"]
    messages = list(state.get("messages", []))
    messages.append({"role": "assistant", "content": output_payload["summary"]})
    return {
        "current_node": "summarizer",
        "input_payload": input_payload,
        "output_payload": output_payload,
        "metadata": metadata,
        "messages": messages,
    }
