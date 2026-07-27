"""Service-layer error types for automation orchestration."""

from __future__ import annotations

from cobalt_wren.core.errors import CobaltWrenError


class WorkflowConfigurationError(CobaltWrenError):
    """Raised when workflow configuration is invalid for runtime assembly."""
