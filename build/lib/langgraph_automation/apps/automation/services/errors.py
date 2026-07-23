"""Service-layer error types for automation orchestration."""

from __future__ import annotations

from langgraph_automation.core.errors import LanggraphAutomationError


class WorkflowConfigurationError(LanggraphAutomationError):
    """Raised when workflow configuration is invalid for runtime assembly."""
