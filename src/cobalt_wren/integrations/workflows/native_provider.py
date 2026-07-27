"""Official provider for the built-in Native Authoring integration."""

from __future__ import annotations

from dataclasses import dataclass

from cobalt_wren.api.integrations import (
    IntegrationContext,
    IntegrationDefinition,
    WorkflowIntegrationProvider,
)
from cobalt_wren.integrations.workflows.definitions import NATIVE_INTEGRATION
from cobalt_wren.native import NativeExecutable, NativeWorkflow


@dataclass(frozen=True, slots=True)
class NativeIntegrationProvider(WorkflowIntegrationProvider):
    """Convert a Native authoring object into an opaque executable."""

    definition: IntegrationDefinition = NATIVE_INTEGRATION

    def wrap(self, target: object, *, context: IntegrationContext) -> object:
        if not isinstance(target, NativeWorkflow):
            raise TypeError("Native integration target must be a NativeWorkflow")
        build_context = context.config.get("build_context")
        from cobalt_wren.api.workflow import WorkflowBuildContext

        if not isinstance(build_context, WorkflowBuildContext):
            raise TypeError("Native integration requires a WorkflowBuildContext")
        return NativeExecutable(workflow=target, build_context=build_context)


NATIVE_PROVIDER = NativeIntegrationProvider()

__all__ = ["NATIVE_PROVIDER", "NativeIntegrationProvider"]
