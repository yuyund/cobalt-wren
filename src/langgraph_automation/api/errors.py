"""Public error facade for langgraph-automation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

__all__ = [
    'FrameworkError',
    'ConfigError',
    'ArtifactStoreError',
    'ArtifactValidationError',
    'ArtifactConflictError',
    'ArtifactIntegrityError',
    'ArtifactPersistenceError',
    'CheckpointStoreError',
    'CheckpointValidationError',
    'CheckpointConflictError',
    'CheckpointIntegrityError',
    'CheckpointPersistenceError',
    'PluginRegistrationError',
    'PluginResolutionError',
    'PluginValidationError',
    'RuntimeAssemblyError',
    'WorkflowPreparationError',
    'ExecutionError',
    'WorkflowCancelledError',
    'WorkflowTimeoutError',
    'WorkflowCheckpointCompatibilityError',
    'SafetyBoundaryError',
]


class FrameworkError(Exception):
    def __init__(
        self,
        safe_message: str,
        *,
        code: str,
        category: str,
        component: str | None = None,
        retryable: bool | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        if not isinstance(safe_message, str) or not safe_message:
            raise ValueError('safe_message must not be empty')
        if not isinstance(code, str) or not code:
            raise ValueError('code must not be empty')
        if not isinstance(category, str) or not category:
            raise ValueError('category must not be empty')

        super().__init__(safe_message)
        self.safe_message = safe_message
        self.code = code
        self.category = category
        self.component = component
        self.retryable = retryable
        self.metadata = dict(metadata or {})

    def to_safe_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            'category': self.category,
            'code': self.code,
            'safe_message': self.safe_message,
        }
        if self.component is not None:
            payload['component'] = self.component
        if self.retryable is not None:
            payload['retryable'] = self.retryable
        if self.metadata:
            payload['metadata'] = dict(self.metadata)
        return payload


class ConfigError(FrameworkError):
    def __init__(
        self,
        safe_message: str,
        *,
        code: str,
        component: str | None = None,
        retryable: bool | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            safe_message,
            code=code,
            category='config',
            component=component,
            retryable=retryable,
            metadata=metadata,
        )


class ArtifactStoreError(FrameworkError):
    def __init__(
        self,
        safe_message: str,
        *,
        code: str,
        component: str | None = None,
        retryable: bool | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            safe_message,
            code=code,
            category='artifact_store',
            component=component,
            retryable=retryable,
            metadata=metadata,
        )


class ArtifactValidationError(ArtifactStoreError):
    def __init__(
        self,
        safe_message: str,
        *,
        code: str,
        component: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            safe_message,
            code=code,
            component=component,
            metadata=metadata,
        )


class ArtifactConflictError(ArtifactStoreError):
    def __init__(
        self,
        safe_message: str,
        *,
        code: str,
        component: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            safe_message,
            code=code,
            component=component,
            metadata=metadata,
        )


class ArtifactIntegrityError(ArtifactStoreError):
    def __init__(
        self,
        safe_message: str,
        *,
        code: str,
        component: str | None = None,
        retryable: bool | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            safe_message,
            code=code,
            component=component,
            retryable=retryable,
            metadata=metadata,
        )


class ArtifactPersistenceError(ArtifactStoreError):
    def __init__(
        self,
        safe_message: str,
        *,
        code: str,
        component: str | None = None,
        retryable: bool | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            safe_message,
            code=code,
            component=component,
            retryable=retryable,
            metadata=metadata,
        )


class CheckpointStoreError(FrameworkError):
    def __init__(
        self,
        safe_message: str,
        *,
        code: str,
        component: str | None = None,
        retryable: bool | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            safe_message,
            code=code,
            category='checkpoint_store',
            component=component,
            retryable=retryable,
            metadata=metadata,
        )


class CheckpointValidationError(CheckpointStoreError):
    def __init__(
        self,
        safe_message: str,
        *,
        code: str,
        component: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            safe_message,
            code=code,
            component=component,
            metadata=metadata,
        )


class CheckpointConflictError(CheckpointStoreError):
    def __init__(
        self,
        safe_message: str,
        *,
        code: str,
        component: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            safe_message,
            code=code,
            component=component,
            metadata=metadata,
        )


class CheckpointIntegrityError(CheckpointStoreError):
    def __init__(
        self,
        safe_message: str,
        *,
        code: str,
        component: str | None = None,
        retryable: bool | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            safe_message,
            code=code,
            component=component,
            retryable=retryable,
            metadata=metadata,
        )


class CheckpointPersistenceError(CheckpointStoreError):
    def __init__(
        self,
        safe_message: str,
        *,
        code: str,
        component: str | None = None,
        retryable: bool | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            safe_message,
            code=code,
            component=component,
            retryable=retryable,
            metadata=metadata,
        )


class PluginRegistrationError(FrameworkError):
    def __init__(
        self,
        safe_message: str,
        *,
        code: str,
        component: str | None = None,
        retryable: bool | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            safe_message,
            code=code,
            category='plugin_registration',
            component=component,
            retryable=retryable,
            metadata=metadata,
        )


class PluginResolutionError(FrameworkError):
    def __init__(
        self,
        safe_message: str,
        *,
        code: str,
        component: str | None = None,
        retryable: bool | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            safe_message,
            code=code,
            category='plugin_resolution',
            component=component,
            retryable=retryable,
            metadata=metadata,
        )


class PluginValidationError(FrameworkError):
    def __init__(
        self,
        safe_message: str,
        *,
        code: str,
        component: str | None = None,
        retryable: bool | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            safe_message,
            code=code,
            category='plugin_validation',
            component=component,
            retryable=retryable,
            metadata=metadata,
        )


class RuntimeAssemblyError(FrameworkError):
    def __init__(
        self,
        safe_message: str,
        *,
        code: str,
        component: str | None = None,
        retryable: bool | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            safe_message,
            code=code,
            category='runtime_assembly',
            component=component,
            retryable=retryable,
            metadata=metadata,
        )


class WorkflowPreparationError(RuntimeAssemblyError):
    def __init__(
        self,
        safe_message: str,
        *,
        code: str,
        component: str | None = None,
        retryable: bool | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        FrameworkError.__init__(
            self,
            safe_message,
            code=code,
            category="workflow_preparation",
            component=component,
            retryable=retryable,
            metadata=metadata,
        )


class ExecutionError(FrameworkError):
    def __init__(
        self,
        safe_message: str,
        *,
        code: str,
        component: str | None = None,
        retryable: bool | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            safe_message,
            code=code,
            category="execution",
            component=component,
            retryable=retryable,
            metadata=metadata,
        )


class WorkflowCancelledError(ExecutionError):
    def __init__(self, safe_message: str = "Workflow execution was cancelled.") -> None:
        super().__init__(safe_message, code="WORKFLOW_CANCELLED", component="execution_control", retryable=False)


class WorkflowTimeoutError(ExecutionError):
    def __init__(self, safe_message: str = "Workflow execution timed out.") -> None:
        super().__init__(safe_message, code="WORKFLOW_TIMED_OUT", component="execution_control", retryable=True)


class WorkflowCheckpointCompatibilityError(ExecutionError):
    def __init__(self, safe_message: str = "Workflow checkpoint version is incompatible.") -> None:
        super().__init__(safe_message, code="WORKFLOW_CHECKPOINT_INCOMPATIBLE", component="workflow_checkpoint", retryable=False)


class SafetyBoundaryError(FrameworkError):
    def __init__(
        self,
        safe_message: str,
        *,
        code: str,
        component: str | None = None,
        retryable: bool | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            safe_message,
            code=code,
            category='safety',
            component=component,
            retryable=retryable,
            metadata=metadata,
        )
