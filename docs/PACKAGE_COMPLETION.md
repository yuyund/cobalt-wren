# Package Completion

This document defines what package completion means after the foundation MVP.

## Package Complete

Package Complete means the package-facing surface is ready for application and control-plane code to use without depending on package internals directly.

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
