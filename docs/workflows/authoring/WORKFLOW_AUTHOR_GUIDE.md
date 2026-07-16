# Workflow Author Guide

This guide explains the minimum workflow author surface.

## How to model a workflow

- create the workflow as a `Plugin`
- return a `WorkflowContribution`
- put `metadata`, `requirements`, and `build` on `WorkflowDefinition`
- use `WorkflowRequirements` to declare needed providers, tools, stores, and sinks
- keep workflow-specific parameters in the workflow definition or workflow payload, not in framework internals

## What workflow authors should use

Use these public facades:

- `langgraph_automation.api.workflow`
- `langgraph_automation.api.plugins`
- `langgraph_automation.api.errors`
- `langgraph_automation.api.llm`
- `langgraph_automation.api.tools`
- `langgraph_automation.api.stores`
- `langgraph_automation.api.events`

## What workflow authors should not do

- do not call `RuntimeAssembler` directly
- do not register with `PluginRegistry` inside the workflow package
- do not import Django models or settings
- do not import `apps.automation` services
- do not store raw provider output or secrets in metadata
- do not treat graph internals as stable public API

## Example

`reference.llm_echo_summary` is the example to follow.

It shows the expected structure:

- `PluginMetadata`
- `PluginContributions.workflows`
- `WorkflowContribution`
- `WorkflowDefinition`
- `WorkflowRequirements`

The workflow contribution remains declarative. The registry and runtime layers are framework responsibilities.

## Preparation Boundary

Workflow authors do not call `WorkflowPreparer` directly in normal application code.
`WorkflowPreparer` is framework internal preparation machinery.
Workflow authors provide `Plugin`, `WorkflowContribution`, and `WorkflowDefinition`.

## Service Layer Boundary

Workflow authors do not call service-layer workflow preparation helpers.
Workflow authors provide `Plugin`, `WorkflowContribution`, and `WorkflowDefinition`.
The framework service layer prepares workflows.

## Package Facade Guidance

Workflow authors should not use:

- `apps/automation` service helpers
- `WorkflowPreparer` directly
- `PluginRegistry` directly
- `RuntimeAssembler` directly
- `ConfigValidator` directly

Workflow authors should target public facades first, and later the package facade `langgraph_automation.api.engine` for package-level orchestration. They should not call the package facade directly from normal workflow code.

## Boundary Guidance

Application workflow authors should use public API facades.
They should not import `apps/automation`, Django, `PluginRegistry`, `RuntimeAssembler`, `ConfigValidator`, `WorkflowPreparer`, or `workflows.catalog` / `workflows.prepare` / `workflows.adapter` / `workflows.requirements`.

`graphs.*` is not a public API for application workflows; it is provisional only where required for `WorkflowDefinition.build`.

Application/control-plane service integration now uses `langgraph_automation.api.engine` for workflow preparation.
