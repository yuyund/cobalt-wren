"""Public error facade import coverage."""

from __future__ import annotations


def test_public_errors_api_exports() -> None:
    from langgraph_automation.api.errors import (
        ArtifactConflictError,
        ArtifactIntegrityError,
        ArtifactPersistenceError,
        ArtifactStoreError,
        ArtifactValidationError,
        CheckpointConflictError,
        CheckpointIntegrityError,
        CheckpointPersistenceError,
        CheckpointStoreError,
        CheckpointValidationError,
        ConfigError,
        FrameworkError,
        PluginRegistrationError,
        PluginResolutionError,
        PluginValidationError,
        RuntimeAssemblyError,
        SafetyBoundaryError,
    )

    assert FrameworkError is not None
    assert ArtifactStoreError is not None
    assert ArtifactValidationError is not None
    assert ArtifactConflictError is not None
    assert ArtifactIntegrityError is not None
    assert ArtifactPersistenceError is not None
    assert CheckpointStoreError is not None
    assert CheckpointValidationError is not None
    assert CheckpointConflictError is not None
    assert CheckpointIntegrityError is not None
    assert CheckpointPersistenceError is not None
    assert ConfigError is not None
    assert PluginRegistrationError is not None
    assert PluginResolutionError is not None
    assert PluginValidationError is not None
    assert RuntimeAssemblyError is not None
    assert SafetyBoundaryError is not None


def test_public_errors_api_all() -> None:
    import langgraph_automation.api.errors as errors_api

    assert set(errors_api.__all__) == {
        'FrameworkError',
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
        'ConfigError',
        'PluginRegistrationError',
        'PluginResolutionError',
        'PluginValidationError',
        'RuntimeAssemblyError',
        'WorkflowPreparationError',
        'ExecutionError',
        'SafetyBoundaryError',
    }
