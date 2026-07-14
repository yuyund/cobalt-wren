# Plugin API Facade

This document defines the plugin API facade staging policy for `langgraph-automation`.

Purpose:

- define which plugin author import surfaces are intended to be public
- stage `api.plugins`, `api.workflow`, `api.runtime`, and `api.errors`
- classify public / provisional / future / deferred
- avoid premature public API fixation
- keep internal `GraphRuntime`, `GraphDefinition`, `RuntimeAssembly`, and `ConfigValidator` out of the public facade
- connect plugin shape docs with public API surface docs

## Current implemented public facade

Current implemented public facade:

- `langgraph_automation.api.llm`
- `langgraph_automation.api.tools`
- `langgraph_automation.api.stores`
- `langgraph_automation.api.events`

Roles:

- `api.llm`: `LLMClient`, `LLMRequest`, `LLMResult`
- `api.tools`: `ToolRegistry`, `ToolResult`, `ToolPolicy`, `ToolPolicyContext`, `ToolPolicyDecision`
- `api.stores`: `ArtifactStore`, `CheckpointStore`
- `api.events`: `EventSink`

Not implemented yet:

- `langgraph_automation.api.plugins`
- `langgraph_automation.api.workflow`
- `langgraph_automation.api.runtime`
- `langgraph_automation.api.errors`

## Facade hierarchy

```text
langgraph_automation.api
  ├─ llm.py        # implemented
  ├─ tools.py      # implemented
  ├─ stores.py     # implemented
  ├─ events.py     # implemented
  ├─ plugins.py    # future
  ├─ workflow.py   # future
  ├─ runtime.py    # future
  └─ errors.py     # future
```

Stages:

- Current: `api.llm`, `api.tools`, `api.stores`, `api.events`
- Next public candidate: `api.plugins`
- Still deferred: `api.workflow`, `api.runtime`, `api.errors`

## api.plugins staging

`api.plugins` is the next public candidate, but it is not implemented in P3-D.

### Public candidate

`api.plugins` public candidate:

- `Plugin`
- `PluginMetadata`
- `PluginContributions`
- `ToolContribution`
- `ProviderContribution`
- `StoreContribution`
- `EventSinkContribution`

Why these are public candidates:

- they form the core vocabulary for plugin packages and contributions
- they connect naturally to the current public facades for tools, llm, stores, and events
- they are more stable than worker / UI / workflow / runtime surfaces

### Provisional

`api.plugins` provisional:

- `WorkflowContribution`
- `ValidationContext`
- `FactoryContext`
- `SecretResolver`

Why provisional:

- `WorkflowDefinition` and `WorkflowRequirements` are not defined as public facades yet
- `ConfigValidator` does not exist yet, so validation context shape may move
- `RuntimeAssembly` does not exist yet, so factory context shape may move
- `SecretResolver` is a security boundary and should be staged carefully

### Future

`api.plugins` future:

- `WorkerContribution`
- `UIContribution`

Why future:

- worker / queue / outbox / long-running semantics are not implemented
- UI registry and permission / visibility boundaries are not implemented

### Deferred

Deferred from `api.plugins`:

- `PluginRegistry`
- `ConfigValidator`
- `RuntimeAssembly`
- `WorkflowDefinition`
- `RuntimeDependencies`
- plugin error taxonomy

Why deferred:

- implementation boundaries are not verified yet
- exposing them too early would freeze internal structure
- registry / validator / runtime assembly are close to package internals

## Why PluginRegistry is not public yet

`PluginRegistry` is a future public candidate, but P3-D does not expose it.

Reasons:

- registration API shape is still unimplemented
- conflict, duplicate, and enabled plugin enforcement are still unverified
- `EffectivePluginSet` is not implemented
- connection to `ConfigValidator` and `RuntimeAssembly` is not implemented
- exposing it too early would freeze registry internals
- the design should avoid service-locator behavior

Future direction:

- if exposed, prefer a thin protocol or registration API over a concrete class-shaped public contract

## Why WorkflowContribution is provisional

`WorkflowContribution` is a provisional public candidate.

Reasons:

- `WorkflowDefinition` facade is not defined yet
- `WorkflowRequirements` facade is not defined yet
- internal `GraphDefinition` and `GraphRuntimeRequirements` should not leak
- `api.workflow` is not designed yet
- workflow shape is tightly coupled to graph/runtime capability

Future direction:

- `api.workflow` may eventually include `WorkflowDefinition`, `WorkflowRequirements`, `WorkflowBuildContext`, and `WorkflowMetadata`

## Why api.runtime is deferred

`api.runtime` is deferred.

Reasons:

- `GraphRuntime` remains provisional
- `RuntimeDependencies` are not implemented
- `RuntimeAssembly` is not implemented
- `FactoryContext` is not fixed
- runtime is close to internal foundation concerns

Still not exposed:

- `GraphRuntime`
- `GraphRuntimeConfig`
- `RuntimeDependencies`
- `RuntimeAssembly`
- `FactoryContext`

Future direction:

- if `api.runtime` exists later, it should likely expose minimal capability protocols rather than concrete runtime classes

## Why api.errors is deferred

`api.errors` is deferred.

Reasons:

- error mapping to UI/API is not yet designed
- safe error message policy and plugin/runtime error mapping need alignment
- config validation and plugin validation error domains are not unified yet
- recoverable vs fatal classification is not established

Future candidate errors:

- `PluginRegistrationError`
- `PluginConflictError`
- `DuplicatePluginError`
- `UnknownPluginError`
- `PluginValidationError`
- `IncompatiblePluginError`
- `ConfigValidationError`
- `UnsafeConfigError`
- `RuntimeAssemblyError`

P3-D does not create error classes.

## Tool / Provider / Store / EventSink contributions

These are public candidates, but not implemented in P3-D.

- `ToolContribution`: public candidate, connects to `api.tools`
- `ProviderContribution`: public candidate, connects to `api.llm`
- `StoreContribution`: public candidate, connects to `api.stores`
- `EventSinkContribution`: public candidate, connects to `api.events`

Notes:

- `ToolDefinition` / `ToolAdapter` are still deferred, so the implementation surface remains staged
- provider type handling remains provisional
- factory context and secret resolver remain deferred

## Worker / UI contributions

These are future and should not be exposed in P3-D.

- `WorkerContribution`: future
- `UIContribution`: future

Reasons:

- worker / queue / outbox / long-running semantics are not implemented
- UI registry / permission / visibility boundaries are not implemented

## Premature fixation policy

P3-D does not implement `api.plugins`, `api.workflow`, `api.runtime`, or `api.errors`.

Reason:

- `PluginRegistry`, `ConfigValidator`, and `RuntimeAssembly` are not implemented
- `WorkflowDefinition`, `RuntimeDependencies`, and error taxonomy are not fixed
- once a public facade is shipped, changing it later is expensive
- docs should classify candidates before code exists

## Facade classification summary

Implemented public facade:

- `api.llm`
- `api.tools`
- `api.stores`
- `api.events`

Future facade:

- `api.plugins`
- `api.workflow`
- `api.runtime`
- `api.errors`

`api.plugins` public candidate:

- `Plugin`
- `PluginMetadata`
- `PluginContributions`
- `ToolContribution`
- `ProviderContribution`
- `StoreContribution`
- `EventSinkContribution`

`api.plugins` provisional:

- `WorkflowContribution`
- `ValidationContext`
- `FactoryContext`
- `SecretResolver`

`api.plugins` future:

- `WorkerContribution`
- `UIContribution`

Deferred:

- `PluginRegistry`
- `ConfigValidator`
- `RuntimeAssembly`
- `WorkflowDefinition`
- `RuntimeDependencies`
- plugin error taxonomy

## P3-D done when

- current facade and future facade are classified
- `api.plugins` candidate boundaries are staged
- `api.workflow`, `api.runtime`, and `api.errors` remain deferred
- internal GraphRuntime and GraphDefinition remain outside the public facade
- premature public API fixation is avoided
