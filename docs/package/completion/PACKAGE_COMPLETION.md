# Package Completion

This document defines what package completion means after the foundation MVP.

## Package Complete

Package Complete means the package-facing surface is ready for application and control-plane code to use without depending on package internals directly.

## Package Facade Implementation Status

- `cobalt_wren.api.engine` is implemented as the initial package facade
- the facade remains public-facing provisional
- preparation-only scope is still intentional
- `run_workflow` remains deferred
- `api.runtime` remains deferred

## Verification Harness Status

- `api.engine` integration, smoke, and failure-matrix coverage is implemented
- explicit plugins passed to `create_engine` are registered and auto-enabled for validation and runtime assembly
- the facade-level verification harness covers the package-facing preparation path
- explicit test-plugin headless preparation is verified through `api.engine`

Required:

- application-facing package facade exists
- package facade hides `PluginRegistry`
- package facade hides `WorkflowPreparer`
- package facade hides `workflows.catalog`
- package facade hides `workflows.adapter`
- package facade hides `workflows.requirements`
- package facade hides `ConfigValidator`
- package facade hides `RuntimeAssembler`
- application/control-plane code can use the package through a stable facade
- verification harness covers package-facing entrypoints
- apps/automation does not rely on package internals as the final architecture
- workflows/applications do not depend on control-plane or package internals

## Still Not Required

Package Complete does not require:

- `company_agent`
- a production application workflow
- worker / queue / outbox
- true resume
- plugin API version migration
- broken-plugin partial-startup policy
- long-running execution semantics

## Future Package Complete+

A later package-complete-plus phase may add:

- external plugin discovery
- Python entry point discovery
- plugin version compatibility
- deprecation policy

## Package Facade Module

The preferred facade module name is `cobalt_wren.api.engine`.

Why not `api.runtime` yet:

- it suggests a broader runtime contract than the package needs at this stage
- it can easily imply graph execution, checkpointing, resume, and worker semantics
- it remains deferred

Why not `api.package`:

- it is less explicit about the orchestration role of the facade

## Initial Facade Scope

The initial facade should focus on:

- package context creation
- workflow preparation
- explicit test-workflow verification

It should not prematurely expose:

- full workflow execution
- graph runner internals
- long-running execution
- checkpoint / resume semantics
- `run_workflow` as a broad public contract

## Package Complete Status

Package Complete is complete.

It is complete because:

- `cobalt_wren.api.engine` is implemented
- `cobalt_wren.api.engine` is verified
- boundary hardening is complete
- the service bridge routes through `api.engine`
- the temporary exception has been removed
- L6 application-facing / service-facing tests exist

## Package Complete+

Package Complete does not require:

- `run_workflow`
- `api.runtime`
- graph execution public API
- worker / queue / outbox
- true resume
- plugin API version migration
- broken-plugin partial-startup policy
- `company_agent`
- production application workflow
