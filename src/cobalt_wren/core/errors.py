"""Common application error types."""

from __future__ import annotations


class CobaltWrenError(Exception):
    """Base class for project-specific failures."""


class ValidationError(CobaltWrenError):
    """Input validation failed."""


class DependencyError(CobaltWrenError):
    """A required dependency is missing or misconfigured."""


class MissingRuntimeDependencyError(DependencyError):
    """Raised when a graph node requires a runtime dependency that is not configured."""


class GraphExecutionError(CobaltWrenError):
    """LangGraph execution failed."""
