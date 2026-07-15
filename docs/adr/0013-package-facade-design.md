# ADR 0013: Package facade design

Status: accepted, provisional

## Context

Package / Foundation MVP is complete, but application and control-plane code still need a stable package-facing entrypoint.

Today the package contains the internal pieces needed for configuration, plugin registration, runtime assembly, workflow preparation, and built-in workflow wiring, but those pieces are still exposed as internal modules.

The service-layer workflow preparation bridge exists and works, but it is transitional.
It must not become the final package boundary.

## Decision

Introduce `langgraph_automation.api.engine` as the public-facing provisional facade for package orchestration.

The initial API shape is:

- `create_engine`
- `AutomationEngine`
- `EnginePreparedWorkflow`

The initial scope is preparation only.

`run_workflow` remains deferred.
`api.runtime` remains deferred.
Graph runner public API remains deferred.
Checkpoint / resume remains deferred.
Worker / queue remains deferred.
External plugin discovery remains deferred.
Entry point discovery remains deferred.

## Why this module name

`api.engine` is preferred because it communicates an orchestration entrypoint without implying a larger runtime contract than the package can safely expose today.

`api.runtime` is deferred because it suggests graph execution, checkpointing, resume, worker, and long-running runtime responsibilities.

`api.package` is less precise about the role of the facade.

## Consequences

Positive:

- application/control-plane code can depend on a stable package entrypoint rather than package internals
- package internals can continue to evolve behind the facade
- the eventual service bridge can route through a single supported boundary

Negative / tradeoffs:

- the facade must stay intentionally small so it does not become a dumping ground
- new public capabilities should be added deliberately rather than by deep import

## API Shape

- `create_engine(config: Mapping[str, object], *, plugins: Sequence[Plugin] = ()) -> AutomationEngine`
- `AutomationEngine.prepare_workflow(workflow_kind: str) -> EnginePreparedWorkflow`
- `EnginePreparedWorkflow(kind: str, graph: object)`

## Deferred Areas

- `run_workflow`
- `api.runtime`
- graph runner public API
- checkpoint / resume
- worker / queue
- long-running execution
- external plugin discovery
- entry point discovery
