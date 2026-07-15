# Package Facade Design

This document defines the application-facing package facade for the package layer.

## Goal

The goal is to let application and control-plane code use the package without knowing package internals.

The facade should hide the moving parts that are still free to evolve:

- `PluginRegistry`
- `WorkflowPreparer`
- `PreparedWorkflow`
- `create_builtin_workflow_registry`
- `workflows.catalog`
- `workflows.prepare`
- `workflows.adapter`
- `workflows.requirements`
- `ConfigValidator`
- `RuntimeAssembler`
- `RuntimeDependencies`

The implementation is now in place, but the contract remains provisional so the boundary can keep evolving without breaking application code.

## Facade Module Name

The facade module name is:

- `langgraph_automation.api.engine`

Status:

- public-facing provisional
- implemented as the initial package facade in Block L

## Why `api.engine`

`api.engine` is the preferred name because it reads as an orchestration entrypoint for the package.

Why not `api.runtime` yet:

- it implies graph execution, checkpointing, resume, worker, and long-running runtime contracts
- that surface is heavier than the current design needs
- it should remain deferred until the runtime contract is designed explicitly

Why not `api.package`:

- it signals a package boundary, but not the operational role of the facade
- it is less clear for application and control-plane code

## Public / Provisional / Internal Classification

Public-facing provisional:

- `langgraph_automation.api.engine`
- `create_engine`
- `AutomationEngine`
- `EnginePreparedWorkflow`

Existing public facades:

- `langgraph_automation.api.errors`
- `langgraph_automation.api.plugins`
- `langgraph_automation.api.workflow`
- `langgraph_automation.api.llm`
- `langgraph_automation.api.tools`
- `langgraph_automation.api.stores`
- `langgraph_automation.api.events`

Internal and hidden behind the facade:

- `langgraph_automation.plugins.registry`
- `langgraph_automation.config.*`
- `langgraph_automation.runtime.*`
- `langgraph_automation.workflows.prepare`
- `langgraph_automation.workflows.catalog`
- `langgraph_automation.workflows.adapter`
- `langgraph_automation.workflows.requirements`

Internal foundation:

- `langgraph_automation.graphs.*`

## API Shape

The design shape is intentionally small:

```python
@dataclass(frozen=True)
class EnginePreparedWorkflow:
    kind: str
    graph: object

class AutomationEngine:
    def prepare_workflow(self, workflow_kind: str) -> EnginePreparedWorkflow:
        ...

def create_engine(
    config: Mapping[str, object],
    *,
    plugins: Sequence[Plugin] = (),
) -> AutomationEngine:
    ...
```

## Input Design

`create_engine` should accept raw `Mapping[str, object]` config.

This keeps application/control-plane code simple and lets the facade hide:

- `ConfigLoader`
- `ConfigValidator`
- `RuntimeAssembler`

Explicit plugins are accepted as a sequence so manual registration remains available without requiring plugin discovery.

## Output Design

`EnginePreparedWorkflow` is the public-facing provisional result.

It contains:

- `kind`
- `graph`

The `graph` field is an opaque internal graph object.
It must not become a stable public contract.

## Initial Scope

The initial facade should cover preparation only:

- load config
- normalize config
- validate config
- assemble runtime dependencies
- register explicit plugins
- resolve workflow kind
- prepare the workflow

It should not expose:

- `run_workflow`
- graph runner internals
- checkpoint / resume
- worker / queue
- long-running execution
- Django Run lifecycle
- event-driven scheduling

`run_workflow` is deferred because it would prematurely expose input handling, output persistence, error persistence, checkpoint semantics, cancellation / resume, event sink semantics, graph runner semantics, execution timeout, and retry policy.

## Secret Resolver

The initial facade should use the default `EnvSecretResolver` internally.

Public secret resolver injection is deferred until the runtime and secret boundaries are designed explicitly.

## Migration Direction

The existing service-layer workflow preparation bridge is transitional.

Current path:

- `apps/automation/services/workflow_preparation.py`
- uses workflow internals directly

Future path:

- `apps/automation/services/workflow_preparation.py`
- calls `langgraph_automation.api.engine`

The transitional bridge is acceptable now, but it must not become the permanent boundary.

## Verification Target

The first package-facade verification target should be:

- `create_engine(config_mapping)`
- `engine.prepare_workflow("reference.llm_echo_summary")`
- `EnginePreparedWorkflow`

Verification levels:

- L3: config -> runtime -> workflow preparation through `api.engine`
- L4: reference workflow headless prepare through `api.engine`
- L5: safe failures for unknown workflow, missing provider, and build failure

Headless smoke tests should only prepare workflows.
They should not require provider network calls or graph execution.

## Deferred APIs

Deferred until later design blocks:

- `run_workflow`
- `api.runtime`
- graph runner public API
- checkpoint / resume
- worker / queue
- external plugin discovery
- entry point discovery
