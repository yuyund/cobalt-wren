# Package Completion

This document defines what package completion means after the foundation MVP.

## Package Complete

Package Complete means the package-facing surface is ready for application and control-plane code to use without depending on package internals directly.

## Package Facade Implementation Status

- `langgraph_automation.api.engine` is implemented as the initial package facade
- the facade remains public-facing provisional
- preparation-only scope is still intentional
- `run_workflow` remains deferred
- `api.runtime` remains deferred

## Verification Harness Status

- `api.engine` integration, smoke, and failure-matrix coverage is implemented
- explicit plugins passed to `create_engine` are registered and auto-enabled for validation and runtime assembly
- the facade-level verification harness covers the package-facing preparation path
- `reference.llm_echo_summary` headless preparation is verified through `api.engine`

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
- external plugin discovery
- entry point discovery
- long-running execution semantics

## Future Package Complete+

A later package-complete-plus phase may add:

- external plugin discovery
- Python entry point discovery
- plugin version compatibility
- deprecation policy

## Package Facade Module

The preferred facade module name is `langgraph_automation.api.engine`.

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
- reference workflow verification

It should not prematurely expose:

- full workflow execution
- graph runner internals
- long-running execution
- checkpoint / resume semantics
- `run_workflow` as a broad public contract

## Package Complete Is Still Pending

Package Complete remains not complete because:

- boundary hardening is complete at the guard / document level, but the service bridge is still transitional
- the service bridge is not yet routed through `api.engine`
- L6 application-facing tests are still deferred

## Boundary Hardening Status

Boundary hardening is complete at the guard/document level, but the service bridge remains transitional.

Package Complete remains pending because:

- the service bridge is still transitional
- service integration via api.engine is not complete
- L6 application-facing tests are still deferred
