# Plugin API Facade

This document defines the plugin API facade staging policy for `langgraph-automation`.

Purpose:

- define which plugin author import surfaces are intended to be public
- stage `api.plugins`, `api.workflow`, `api.runtime`, and `api.errors`
- classify public / provisional / future / deferred
- avoid premature public API fixation
- keep internal `RuntimeAssembly` and `ConfigValidator` out of the public facade while exposing only framework-neutral workflow contracts
- connect plugin shape docs with public API surface docs

## Current implemented public facade

Current implemented public facade:

- `langgraph_automation.api.llm`
- `langgraph_automation.api.tools`
- `langgraph_automation.api.stores`
- `langgraph_automation.api.events`
- `langgraph_automation.api.errors`
- `langgraph_automation.api.plugins`
- `langgraph_automation.api.workflow`

Roles:

- `api.llm`: `LLMClient`, `LLMRequest`, `LLMResult`
- `api.tools`: `ToolRegistry`, `ToolResult`, `ToolPolicy`, `ToolPolicyContext`, `ToolPolicyDecision`
- `api.stores`: `ArtifactStore`, `CheckpointStore`
- `api.events`: `EventSink`
- `api.errors`: `FrameworkError`, `ConfigError`, `PluginRegistrationError`, `PluginResolutionError`, `PluginValidationError`, `RuntimeAssemblyError`, `SafetyBoundaryError`
- `api.plugins`: `Plugin`, `PluginMetadata`, `PluginContributions`, `ToolContribution`, `ProviderContribution`, `StoreContribution`, `EventSinkContribution`
- `api.workflow`: `WorkflowMetadata`, `WorkflowRequirements`, `WorkflowDefinition`, `WorkflowContribution`

Not implemented yet:

- `langgraph_automation.api.runtime`

## Facade hierarchy

```text
langgraph_automation.api
  ├─ llm.py        # implemented
  ├─ tools.py      # implemented
  ├─ stores.py     # implemented
  ├─ events.py     # implemented
  ├─ plugins.py    # implemented
  ├─ workflow.py   # implemented
  ├─ runtime.py    # future
  └─ errors.py     # implemented
```

Stages:

- Current: `api.llm`, `api.tools`, `api.stores`, `api.events`, `api.errors`, `api.plugins`, `api.workflow`
- Still deferred: `api.runtime`

## api.plugins staging

`api.plugins` minimal public facade is now implemented.

### Implemented in MVP

- `Plugin`
- `PluginMetadata`
- `PluginContributions`
- `ToolContribution`
- `ProviderContribution`
- `StoreContribution`
- `EventSinkContribution`

`PluginContributions` aggregates workflow contributions via `workflows`, but `WorkflowContribution` itself is defined in `langgraph_automation.api.workflow`.

### Deferred from api.plugins

- `WorkerContribution`
- `UIContribution`
- `ValidationContext`
- `FactoryContext`
- `SecretResolver`
- `PluginRegistry`
- `ConfigValidator`
- `RuntimeAssembly`
- `RuntimeDependencies`
- plugin error taxonomy

Why deferred:

- worker / queue / outbox / long-running semantics are not implemented
- UI registry and permission / visibility boundaries are not implemented
- `ConfigValidator` and `RuntimeAssembly` are later layers and still own their own context shapes
- `SecretResolver` is a security boundary and should be staged carefully
- implementation boundaries are not verified yet
- exposing them too early would freeze internal structure
- registry / validator / runtime assembly are close to package internals

### Internal mechanism

- `PluginRegistry` remains internal at `langgraph_automation.plugins.registry`
- `api.plugins` does not export `PluginRegistry`

## Why PluginRegistry is not public yet

`PluginRegistry` is a future public candidate, but P3-D does not expose it.

Reasons:

- registration API shape is still unimplemented
- conflict, duplicate, and enabled plugin enforcement are still unverified
- `EffectivePluginSet` is not part of the workflow facade
- connection to `ConfigValidator` and `RuntimeAssembly` is not implemented
- exposing it too early would freeze registry internals
- the design should avoid service-locator behavior

Future direction:

- if exposed, prefer a thin protocol or registration API over a concrete class-shaped public contract

## Workflow facade staging

`api.workflow` is now the public workflow vocabulary facade.

`WorkflowContribution`, `WorkflowDefinition`, `WorkflowRequirements`, and `WorkflowMetadata` are implemented there.

Reasons for keeping workflow vocabulary in a dedicated facade:

- workflow is the user-facing term that plugin authors should import
- `api.plugins` can aggregate workflow contributions without owning workflow-specific vocabulary
- built-in workflows are ordinary `Plugin` objects that register `WorkflowContribution` through `PluginRegistry`
- internal graph vocabulary remains free to evolve separately
- built-in wiring stays in `workflows.catalog` and `workflows.adapter`

## Why api.runtime is deferred

`api.runtime` is deferred.

Reasons:

- the removed graph runtime is not a compatibility surface
- `RuntimeDependencies` are internal runtime plumbing
- `RuntimeAssembly` is already internal/provisional
- `FactoryContext` is not a public facade type
- runtime is close to internal foundation concerns

Still not exposed:

- `RuntimeDependencies`
- `RuntimeAssembly`
- `FactoryContext`

Future direction:

- if `api.runtime` exists later, it should likely expose minimal capability protocols rather than concrete runtime classes

## Why api.errors is no longer deferred

`api.errors` is implemented as the minimal public error facade.
The error taxonomy and facade staging are defined in `../../contracts/errors/ERROR_TAXONOMY.md` and `../../api/errors/API_ERRORS_FACADE.md`.

## Tool / Provider / Store / EventSink contributions

These are public candidates and are implemented in `api.plugins`.

- `ToolContribution`: public candidate, connects to `api.tools`
- `ProviderContribution`: public candidate, connects to `api.llm`
- `StoreContribution`: public candidate, connects to `api.stores`
- `EventSinkContribution`: public candidate, connects to `api.events`

Notes:

- `ToolDefinition` / `ToolAdapter` are still deferred, so the implementation surface remains staged
- provider type handling remains provisional
- factory context and secret resolver remain deferred

## Worker / UI contributions

These remain future and should not be exposed in P3-D.

- `WorkerContribution`: future
- `UIContribution`: future

Reasons:

- worker / queue / outbox / long-running semantics are not implemented
- UI registry / permission / visibility boundaries are not implemented

## Premature fixation policy

P3-D does not implement `api.runtime`.

Reason:

- `RuntimeDependencies`, and runtime execution shapes are not fixed
- once a public facade is shipped, changing it later is expensive
- docs should classify candidates before code exists

## Facade classification summary

Implemented public facade:

- `api.llm`
- `api.tools`
- `api.stores`
- `api.events`
- `api.errors`
- `api.plugins`
- `api.workflow`

Future facade:

- `api.runtime`

Built-in workflow wiring:

- built-in/reference workflows are represented as ordinary `Plugin` objects
- `WorkflowContribution` is staged through `api.workflow` and registered with `PluginRegistry`
- `WorkflowDefinition.build` is called only by the internal workflow adapter
