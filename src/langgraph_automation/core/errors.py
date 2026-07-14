"""Common application error types."""

from __future__ import annotations


class LanggraphAutomationError(Exception):
    """Base class for project-specific failures."""


class ValidationError(LanggraphAutomationError):
    """Input validation failed."""


class DependencyError(LanggraphAutomationError):
    """A required dependency is missing or misconfigured."""


class MissingRuntimeDependencyError(DependencyError):
    """Raised when a graph node requires a runtime dependency that is not configured."""


class GraphExecutionError(LanggraphAutomationError):
    """LangGraph execution failed."""
