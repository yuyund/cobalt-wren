"""Planner node."""

from __future__ import annotations

from langgraph_automation.graphs.runtime import GraphRuntime
from langgraph_automation.graphs.states import AutomationState


def planner_node(state: AutomationState, runtime: GraphRuntime) -> AutomationState:
    input_payload = dict(state.get("input_payload", {}))
    metadata = dict(state.get("metadata", {}))
    plan = {
        "intent": "plan",
        "input_keys": sorted(input_payload.keys()),
        "node": "planner",
    }
    metadata["plan"] = plan
    messages = list(state.get("messages", []))
    messages.append({"role": "system", "content": "planner prepared execution plan"})
    return {
        "current_node": "planner",
        "input_payload": input_payload,
        "metadata": metadata,
        "messages": messages,
    }
