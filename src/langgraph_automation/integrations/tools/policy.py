"""Tool authorization policy primitives."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, runtime_checkable

from langgraph_automation.core.redaction import redact_mapping, redact_text
from langgraph_automation.core.summary import summarize_mapping, truncate_text
from langgraph_automation.integrations.tools.base import ToolResult

POLICY_DENIED_EXIT_CODE = 126
POLICY_DENIED_ERROR_CODE = "tool_policy_denied"


@dataclass(frozen=True)
class ToolPolicyContext:
    """Pure policy input provided by runtime assembly."""

    run_id: int | None = None
    workflow_id: int | None = None
    thread_id: str = ""


@dataclass(frozen=True)
class ToolPolicyDecision:
    """Normalized authorization decision."""

    allowed: bool
    code: str = ""
    reason: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)


@runtime_checkable
class ToolPolicy(Protocol):
    """Protocol for tool authorization policies."""

    def authorize(self, name: str, kwargs: Mapping[str, Any], context: ToolPolicyContext) -> ToolPolicyDecision: ...


@dataclass(frozen=True)
class AllowlistToolPolicy:
    """Allow only explicitly configured tool names."""

    allowed_tools: frozenset[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "allowed_tools", frozenset(self.allowed_tools))

    def authorize(self, name: str, kwargs: Mapping[str, Any], context: ToolPolicyContext) -> ToolPolicyDecision:
        del kwargs, context
        if name in self.allowed_tools:
            return ToolPolicyDecision(
                allowed=True,
                code="tool_allowed",
                reason="Tool is allowed by policy.",
                metadata={"tool_name": name},
            )
        return ToolPolicyDecision(
            allowed=False,
            code="tool_not_allowed",
            reason=truncate_text(redact_text(f"Tool '{name}' is not allowed by policy."), max_chars=300),
            metadata={"tool_name": name},
        )


def _safe_policy_metadata(decision: ToolPolicyDecision) -> dict[str, Any]:
    redacted = redact_mapping(dict(decision.metadata))
    return summarize_mapping(redacted)


def _safe_reason(reason: str) -> str:
    bounded = truncate_text(redact_text(reason or "Tool is not allowed by policy."), max_chars=300).strip()
    return bounded or "Tool is not allowed by policy."


def build_policy_denied_result(*, tool_name: str, decision: ToolPolicyDecision) -> ToolResult:
    """Build a failed ToolResult for policy denials."""

    safe_reason = _safe_reason(decision.reason)
    safe_policy_metadata = _safe_policy_metadata(decision)
    output_summary = {
        "policy_error_code": POLICY_DENIED_ERROR_CODE,
        "tool_name": tool_name,
        "reason": safe_reason,
        "policy_metadata": safe_policy_metadata,
    }
    return ToolResult(
        output=None,
        output_summary=truncate_text(
            json.dumps(output_summary, ensure_ascii=False, sort_keys=True, default=str),
            max_chars=500,
        ),
        exit_code=POLICY_DENIED_EXIT_CODE,
        metadata={
            "tool_name": tool_name,
            "policy_denied": True,
            "policy_error_code": POLICY_DENIED_ERROR_CODE,
            "policy_code": decision.code or POLICY_DENIED_ERROR_CODE,
            "policy_metadata": safe_policy_metadata,
        },
        error_message=safe_reason,
    )
