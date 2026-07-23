"""Policy-aware wrapper for tool registries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langgraph_automation.integrations.tools.base import ToolCallable, ToolRegistry, ToolResult
from langgraph_automation.integrations.tools.policy import ToolPolicy, ToolPolicyContext, build_policy_denied_result


@dataclass(slots=True)
class PolicyAwareToolRegistry:
    """ToolRegistry decorator that enforces authorization policies."""

    inner: ToolRegistry
    policy: ToolPolicy
    context: ToolPolicyContext | None = None

    def __post_init__(self) -> None:
        if self.context is None:
            self.context = ToolPolicyContext()

    def register(self, name: str, tool: ToolCallable) -> None:
        self.inner.register(name, tool)

    def get(self, name: str) -> ToolCallable:
        return self.inner.get(name)

    def run(self, name: str, **kwargs: Any) -> ToolResult:
        context = self.context or ToolPolicyContext()
        decision = self.policy.authorize(name, kwargs, context)
        if not decision.allowed:
            return build_policy_denied_result(tool_name=name, decision=decision)
        return self.inner.run(name, **kwargs)
