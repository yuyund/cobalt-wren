from __future__ import annotations

import importlib
from pathlib import Path

import pytest


PUBLIC_EXPORTS = {
    "cobalt_wren.api.llm": {"LLMClient", "LLMRequest", "LLMResult"},
    "cobalt_wren.api.tools": {
        "ToolRegistry", "ToolResult", "ToolPolicy", "ToolPolicyContext", "ToolPolicyDecision"
    },
    "cobalt_wren.api.stores": {
        "ArtifactStore", "ArtifactWriteRequest", "StoredArtifact", "ArtifactReadResult",
        "CheckpointStore", "CheckpointWriteRequest", "StoredCheckpoint", "CheckpointReadResult",
    },
    "cobalt_wren.api.events": {"EventSink"},
    "cobalt_wren.api.errors": {
        "FrameworkError", "ConfigError", "ArtifactStoreError",
        "ArtifactValidationError", "ArtifactConflictError", "ArtifactIntegrityError",
        "ArtifactPersistenceError", "CheckpointStoreError",
        "CheckpointValidationError", "CheckpointConflictError",
        "CheckpointIntegrityError", "CheckpointPersistenceError",
        "PluginRegistrationError", "PluginResolutionError", "PluginValidationError",
        "RuntimeAssemblyError", "WorkflowPreparationError", "ExecutionError",
        "WorkflowCancelledError", "WorkflowTimeoutError",
        "WorkflowCheckpointCompatibilityError", "SafetyBoundaryError",
    },
    "cobalt_wren.api.integrations": {
        "IntegrationSupport", "IntegrationMaturity", "IntegrationAvailabilityStatus",
        "ActionSafety", "ProjectionOwnerKind", "IntegrationCapability",
        "IntegrationDefinition", "IntegrationAvailability", "IntegrationContext",
        "ExecutionUnitProjection", "LifecycleProjection", "IntegrationProjection",
        "IntegrationActionDescriptor", "IntegrationActionRequest",
        "IntegrationProjectionBatch", "WorkflowIntegrationProvider",
    },
    "cobalt_wren.api.plugins": {
        "DEFAULT_PLUGIN_ENTRY_POINT_GROUP", "PLUGIN_API_VERSION", "discover_plugins",
        "Plugin", "PluginMetadata", "PluginContributions", "ToolContribution",
        "ProviderContribution", "StoreContribution", "EventSinkContribution",
    },
    "cobalt_wren.api.workflow": {
        "WorkflowBuildContext", "WorkflowExecutionContext", "WorkflowExecutionControl",
        "WorkflowResumeRequest", "WorkflowExecutionResult", "WorkflowExecutable",
        "WorkflowResumable", "WorkflowMetadata", "WorkflowRequirements",
        "WorkflowDefinition", "WorkflowContribution",
    },
    "cobalt_wren.api.engine": {"EnginePreparedWorkflow", "AutomationEngine", "create_engine"},
    "cobalt_wren.native": {
        "NativeArtifact", "NativeWorkflowContext", "NativeWorkflow", "NativeExecutable",
        "RetryPolicy", "workflow",
    },
}


@pytest.mark.parametrize(("module_name", "expected"), PUBLIC_EXPORTS.items())
def test_public_facade_exports_are_explicit(module_name: str, expected: set[str]) -> None:
    module = importlib.import_module(module_name)
    assert set(module.__all__) == expected
    assert all(hasattr(module, name) for name in expected)


def test_package_root_does_not_accidentally_reexport_facades() -> None:
    package = importlib.import_module("cobalt_wren")
    assert not hasattr(package, "create_engine")
    assert not hasattr(package, "workflow")
    assert not hasattr(package, "Plugin")


def test_consumer_docs_do_not_recommend_internal_imports() -> None:
    root = Path(__file__).parents[3]
    consumer_text = "\n".join(
        (root / path).read_text(encoding="utf-8")
        for path in (
            "README.md",
            "docs/workflows/authoring/WORKFLOW_AUTHOR_GUIDE.md",
            "src/cobalt_wren/scaffold/workflow_package.py",
        )
    )
    forbidden = (
        "from cobalt_wren.apps.",
        "from cobalt_wren.runtime.",
        "from cobalt_wren.config.",
        "from cobalt_wren.plugins.registry",
        "from cobalt_wren.workflows.prepare",
    )
    assert not any(value in consumer_text for value in forbidden)


def test_stable_schema_ids_follow_versioned_policy() -> None:
    schema_ids = {
        "native.step.v1",
        "langgraph.task.v1",
        "langgraph.interrupt.v1",
        "langgraph.checkpoint_ref.v1",
        "llamaindex.step.v1",
        "llamaindex.event.v1",
    }
    assert all(value.rsplit(".v", 1)[-1].isdigit() for value in schema_ids)


def test_machine_error_codes_are_stable() -> None:
    from cobalt_wren.api.errors import (
        WorkflowCancelledError,
        WorkflowCheckpointCompatibilityError,
        WorkflowTimeoutError,
    )

    assert WorkflowCancelledError("cancelled").code == "WORKFLOW_CANCELLED"
    assert WorkflowTimeoutError("timed out").code == "WORKFLOW_TIMED_OUT"
    assert (
        WorkflowCheckpointCompatibilityError("incompatible").code
        == "WORKFLOW_CHECKPOINT_INCOMPATIBLE"
    )
