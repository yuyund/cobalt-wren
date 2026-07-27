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

- `cobalt_wren.api.workflow`
- `cobalt_wren.api.plugins`
- `cobalt_wren.api.errors`
- `cobalt_wren.api.llm`
- `cobalt_wren.api.tools`
- `cobalt_wren.api.stores`
- `cobalt_wren.api.events`

## What workflow authors should not do

- do not call `RuntimeAssembler` directly
- do not register with `PluginRegistry` inside the workflow package
- do not import Django models or settings
- do not import `apps.automation` services
- do not store raw provider output or secrets in metadata
- do not treat graph internals as stable public API

## Examples

Copyable Native examples live under `examples/native/`. They are source examples only: importing the foundation or creating an engine does not register them. An application explicitly converts an example or application workflow to a `Plugin` and passes it to `create_engine(...)` or publishes it through the plugin entry-point group.

The examples cover sequential execution, ordinary Python branching, explicit retry and timeout, and bounded loop occurrence identities. Product workflow kinds must come from application or plugin distributions, not from example modules.

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

Workflow authors should target public facades first, and later the package facade `cobalt_wren.api.engine` for package-level orchestration. They should not call the package facade directly from normal workflow code.

## Boundary Guidance

Application workflow authors should use public API facades.
They should not import `apps/automation`, Django, `PluginRegistry`, `RuntimeAssembler`, `ConfigValidator`, `WorkflowPreparer`, or `workflows.catalog` / `workflows.prepare` / `workflows.adapter` / `workflows.requirements`.

`graphs.*` is not a public API for application workflows; it is provisional only where required for `WorkflowDefinition.build`.

Application/control-plane service integration now uses `cobalt_wren.api.engine` for workflow preparation.

## Workflow Freedom And Foundation Changes

Workflow authors own state shape, nodes, conditional edges, subgraphs, and whether the workflow uses LLMs, tools, artifacts, or checkpoints.
The foundation owns safety and integration boundaries, not business topology.

A new workflow should be addable through plugin and workflow contributions without modifying existing workflows, graph foundation, runtime assembly, or control-plane services.
A foundation change is justified only when the workflow introduces a genuinely new package capability or safety requirement.

External libraries may be used inside workflow or integration adapters, but provider-specific types, raw objects, and lifecycle must not leak into the public workflow contract.

## Public Build And Execution Contract

External workflows may use a context-aware builder:

```python
from cobalt_wren.api.workflow import WorkflowBuildContext

def build(context: WorkflowBuildContext) -> object:
    ...
```

`WorkflowBuildContext` exposes workflow-owned opaque config plus the named providers, tools, stores, and event sinks already validated by `WorkflowRequirements`. It does not expose `RuntimeDependencies`, `GraphRuntime`, the internal registry, Django models, or control-plane services.

The returned object is deliberately framework-neutral. The engine accepts an object with `execute(input_payload)`, an object with `invoke(input_payload)`, or a callable. This permits LangGraph, another orchestration framework, or a custom executor without making any of them the package architecture. Existing zero-argument builders remain supported as a compatibility path.

The foundation does not inspect the returned object to discover nodes, edges, state, checkpoints, interrupts, tools, or LLM calls. Rich framework integration requires an integration helper or explicit instrumentation. Future official helpers are expected to reduce registration and observability wiring to a small declaration while keeping the generic adapter unchanged.

Connection simplification and workflow implementation simplification are separate concerns. Scaffolding and OSS helpers simplify foundation connection. Native Authoring is a separate product surface and uses the same integration and control-plane contracts as external frameworks.

Workflow-specific config is supplied at preparation time and copied into the public context. It remains opaque to the foundation unless the contribution provides explicit validation.

## Publishing As A Separate Distribution

An external workflow distribution declares the foundation package as a dependency and publishes its plugin factory through an optional entry point:

```toml
[project]
name = "acme-workflows"
dependencies = ["cobalt-wren>=0.1.0rc1"]

[project.entry-points."cobalt_wren.plugins"]
acme = "acme_workflows:create_plugin"
```

The external distribution must import only public `cobalt_wren.api.*` contracts. Importing the engine, internal registry, runtime assembly, graph implementation, Django application, or control-plane services is unsupported.

Consumers may retain explicit registration for deterministic embedding, or opt into installed distribution discovery with `create_engine(..., discover_plugins=True)`.

## Workflow Configuration Validation

A contribution may validate workflow-owned config before requirements and build:

```python
def validate_config(*, config):
    if config.get("mode") not in {"normal", "strict"}:
        raise ValueError("invalid mode")
```

The validator receives a defensive top-level copy. Mutating it does not transform the config later passed to `WorkflowBuildContext`; validation should either return normally or raise. Internal exception details are retained only as the exception cause and are not exposed in the safe package error message.

## Store And Event-Sink Capabilities

Workflows declare artifact, checkpoint, and named event-sink requirements through `WorkflowRequirements`. The build context provides only initialized public capabilities; secret resolvers and factory contexts are not exposed. The same workflow code can therefore use memory, filesystem, or plugin-provided implementations selected by package configuration.

## Native Authoring Direction

Native Authoring is a separate convenience and execution surface for ordinary Python workflows. It is not a requirement for external workflows and does not replace the public `WorkflowContribution` contract.

The primary Native model is expected to preserve ordinary Python control flow while making operational boundaries explicit through named steps:

```python
@workflow(name="document-review")
async def document_review(ctx, request):
    document = await ctx.step("extract", extract_document, request)
    if document.sensitive:
        return await ctx.step("manual-route", route_manual, document)
    return await ctx.step("summarize", summarize, document)
```

Native is intended for bounded business pipelines, LLM and tool calls, external APIs, retry, timeout, cancellation, artifacts, and common UI. Durable checkpoint recovery, interrupt/resume, long waiting, time travel, graph cycles, and stateful subgraphs remain reasons to use an integration such as LangGraph.

See `NATIVE_AUTHORING_USE_CASE_DESIGN.md` for the use-case matrix, progressive disclosure model, provisional API, and MVP acceptance scenarios.

### Current Native P1 Surface

The provisional Native surface is now importable from `cobalt_wren.native`:

```python
from cobalt_wren.native import NativeWorkflowContext, workflow

@workflow(name="document-review")
async def document_review(ctx: NativeWorkflowContext, request):
    normalized = await ctx.step("normalize", normalize, request)
    return {"normalized": normalized}

plugin = document_review.plugin(
    plugin_name="acme-document-review",
    workflow_kind="acme.document_review",
)
```

The generated plugin follows the same public registration and distribution contract as any external workflow. Retry, timeout, and occurrence identities are implemented; recipes, progress, metrics, and durable waiting remain deferred.
