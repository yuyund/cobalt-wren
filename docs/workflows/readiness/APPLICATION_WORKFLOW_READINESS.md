# Application Workflow Readiness

This document defines the readiness gate for introducing application workflows.

Goal:

- make it safe to load application workflows after the foundation blocks are in place
- keep application workflows on the `Plugin` / `WorkflowContribution` path
- keep public facade usage narrow and intentional
- keep control-plane, Django, registry, and runtime assembly dependencies out of workflow author code

## Public / internal policy

Public facades:

- `cobalt_wren.api.errors`
- `cobalt_wren.api.plugins`
- `cobalt_wren.api.workflow`
- `cobalt_wren.api.llm`
- `cobalt_wren.api.tools`
- `cobalt_wren.api.stores`
- `cobalt_wren.api.events`

Internal / provisional:

- `cobalt_wren.config.*`
- `cobalt_wren.runtime.*`
- `cobalt_wren.plugins.registry`
- `cobalt_wren.workflows.adapter`
- `cobalt_wren.workflows.requirements`
- `cobalt_wren.workflows.catalog`

Internal foundation:

- legacy `cobalt_wren.graphs.*` package: removed; no compatibility import is provided

Control plane:

- `cobalt_wren.apps.automation.*`

Application workflow code should use public facades by default and should not depend on control-plane modules directly.

## Readiness criteria

Ready:

- workflow is represented as a `Plugin`
- workflow contributions are carried through `PluginContributions.workflows`
- workflow contribution is expressed with `WorkflowContribution`
- workflow definition is expressed with `WorkflowDefinition`
- workflow requirements are declared with `WorkflowRequirements`
- workflow code does not build runtime dependencies directly
- workflow code does not call `RuntimeAssembler` directly
- workflow code does not call `PluginRegistry.register()` directly
- workflow code does not import Django models or settings
- workflow code does not import `apps.automation` services
- workflow code does not persist raw input, raw prompt, or raw provider response
- workflow code does not place secret values into metadata, logs, or errors
- workflow code can pass the architecture boundary tests
- workflow code can be reasoned about through the public workflow facade

Not ready:

- workflow code imports `apps.automation` directly
- workflow code imports Django models or settings directly
- workflow code calls `RuntimeAssembler` directly
- workflow code performs registry registration by itself
- workflow code keeps raw provider response in state, output, or metadata
- workflow code stores secret values in metadata
- workflow code depends on `api.runtime`
- workflow code depends on public graph internals

## Example workflow package

A test or application-owned Native plugin is the readiness example; no workflow is registered implicitly.

It demonstrates:

- `PluginMetadata`
- `PluginContributions.workflows`
- `WorkflowContribution`
- `WorkflowDefinition`
- `WorkflowRequirements`

The example is useful because it shows the expected path without introducing application-specific control-plane logic.

## Scope Still Excluded

Application workflow readiness still excludes:

- service layer integration
- full execution path migration
- direct use of `WorkflowPreparer` by application workflow code

## Still Excluded

Application workflow readiness still excludes:

- direct use of apps/automation service helpers by workflow code
- direct use of `WorkflowPreparer` by workflow code
- direct use of `PluginRegistry` by workflow code

## Package Completion Dependency

Application workflow implementation remains deferred until:

- application-facing package facade is designed
- application-facing package facade is implemented
- package verification harness is in place
- service integration uses the package facade

`company_agent` is explicitly deferred until after a minimal application workflow example validates the package facade.

## Package Facade Dependency

Application workflow implementation remains deferred until the application-facing package facade is designed and implemented.
`cobalt_wren.api.engine` is the implemented provisional facade target.
`company_agent` remains deferred until a minimal application workflow validates the package facade.

## Boundary Hardening Gate

Application workflow implementation remains deferred until:

- boundary hardening is complete
- service integration is routed through `api.engine`
- L6 application-facing / service-facing tests exist

These conditions are now satisfied.
`company_agent` remains deferred.
The next step is the Minimal Application Workflow Example block.
