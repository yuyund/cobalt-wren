# Plugin API Shape

This document defines the plugin API shape for `langgraph-automation`.

Purpose:

- define the minimal shape of plugin objects
- separate plugin package from plugin contribution
- organize contribution type shapes
- separate validation hooks from factory hooks
- fix dependency direction between registry, validator, and runtime assembly
- organize future public API facades
- preserve loose coupling, extensibility, and reduced blast radius

## Design principles

- plugin package and contribution are separate
- registry holds definition, factory, and metadata, not concrete runtime instances
- validation hooks only validate config and do not create runtime dependencies
- factory hooks are called from RuntimeAssembly and create concrete dependencies
- config holds names and behavior parameters only
- plugin depends on public API facades, not internal modules
- common base should stay small
- do not force all contribution types into one class hierarchy

Coupling goals:

- registry, validator, runtime assembly, and config loader responsibilities must stay separate
- one plugin package may provide multiple contributions
- contribution-specific factory and validation shapes should be separate so changes do not fan out across all contribution types

## Implemented in MVP

- `Plugin`
- `PluginMetadata`
- `PluginContributions`
- `WorkflowContribution`
- `ToolContribution`
- `ProviderContribution`
- `StoreContribution`
- `EventSinkContribution`

Deferred from MVP:

- `WorkerContribution`
- `UIContribution`
- `ValidationContext`
- `FactoryContext`
- `SecretResolver`

## Plugin object

Conceptual shape only:

```python
class Plugin:
    metadata: PluginMetadata
    contributions: PluginContributions
```

Plugin objects do not hold runtime dependencies, Django model objects, Run objects, or raw config sources.

## PluginMetadata

Minimal future shape:

```text
PluginMetadata:
  name
  version
  description
  plugin_types
  provides
  requires
```

Conceptual example:

```yaml
name: github
version: 0.1.0
description: GitHub integration plugin
plugin_types:
  - tool
  - ui
provides:
  tools:
    - github.search_issues
    - github.create_issue
  ui:
    - github.issue_link_renderer
requires:
  public_api_version: ">=0.1,<1.0"
```

Metadata may include:

- plugin name
- plugin version
- description
- plugin types
- provided contribution names
- required public API version
- optional capability metadata

Metadata must not include:

- secret values
- env var values
- concrete runtime instances
- provider raw objects
- Django model objects
- Run objects
- raw config sources

## PluginContributions

`PluginContributions` is the set of contributions a plugin package provides.

Supported collections:

- workflows
- tools
- providers
- stores
- event_sinks
- workers
- ui

One plugin package may provide multiple contribution types and multiple contributions.

Examples:

- github plugin package: tools + UI
- litellm plugin package: providers
- company_agent plugin package: workflows

## Common contribution shape

All contributions share a thin common shape:

- `name`
- `description`
- `metadata`
- `validate_config` hook

Common metadata should be shared. Execution / factory hooks should stay type-specific.

Reason:

- ToolContribution, ProviderContribution, and WorkflowContribution have different return values and contexts
- forcing one universal interface increases optional fields, `Any`, and type branching
- that raises coupling and blast radius

## WorkflowContribution

`WorkflowContribution` is implemented in `langgraph_automation.api.workflow` and is a first-class plugin contribution type.

### Purpose

WorkflowContribution adds a workflow kind and provides graph structure, nodes, routing, state schema, prompt assembly, and output mapping.

### Conceptual shape

```python
WorkflowContribution:
    kind: str
    metadata: WorkflowMetadata
    requirements: WorkflowRequirements
    validate_config(config, context) -> None
    build_workflow(context) -> WorkflowDefinition
```

`WorkflowDefinition` and `WorkflowRequirements` are implemented in `langgraph_automation.api.workflow`.
`GraphDefinition` / `GraphRuntimeRequirements` remain internal foundation vocabulary and are not exposed through a public facade here.
Built-in reference workflows are still ordinary workflow contributions; the workflow adapter is the only place that calls `WorkflowDefinition.build`.
Application workflows are expected to use the same `Plugin` / `WorkflowContribution` path as built-in reference workflows.

### Validation

WorkflowContribution validates `workflows.<name>.config`.
The validation hook is retained on the contribution shape, but registry lookup and registration do not invoke it.

Core knows:

- enabled
- kind
- llm_profile
- tools
- limits

WorkflowContribution knows:

- departments
- routing_policy
- summary_style
- output_format
- application-specific behavior parameters

`WorkflowDefinition.build` is retained on the definition shape, but registry lookup and registration do not invoke it.

## ToolContribution

### Purpose

ToolContribution provides tool name, capability, input-output boundary, and callable implementation.

### Conceptual shape

```python
ToolContribution:
    name: str
    capabilities: set[str]
    validate_config(config, context) -> None
    create_tool(context) -> ToolAdapter
```

`ToolContribution` is implemented in `langgraph_automation.api.plugins`.
`ToolAdapter` and `ToolDefinition` remain deferred.

### ToolPolicy boundary

- ToolContribution provides capability
- ToolPolicy decides whether the tool may be used
- RuntimeAssembly only inserts allowed tools into ToolRegistry
- Workflow execution must not bypass ToolPolicy

## ProviderContribution

### Purpose

ProviderContribution resolves provider names to `LLMClient` or embedding client implementations.

### Conceptual shape

```python
ProviderContribution:
    name: str
    provider_type: str
    validate_profile(profile_config, context) -> None
    create_client(profile_config, factory_context) -> LLMClient
```

### Secret handling

ValidatedPackageConfig may contain env var names such as `api_key_env: LLM_API_KEY`.
RuntimeAssembly resolves env values through a `SecretResolver` boundary.
ProviderContribution uses resolved secrets to create the client.

ValidatedPackageConfig and ResolvedWorkflowConfig never contain secret values.

ProviderContribution must not read secrets from raw config sources, store secret values in config, or move provider raw responses into state, output, or EventSink.

## StoreContribution

### Purpose

StoreContribution adds artifact or checkpoint backends.

### Conceptual shape

```python
StoreContribution:
    backend_name: str
    store_type: "artifact" | "checkpoint"
    validate_config(config, context) -> None
    create_store(config, factory_context) -> ArtifactStore | CheckpointStore
```

### Safety

- absolute local paths must not be exposed in UI/API
- secret values must not be stored in config
- checkpoint raw dump without schema/version is forbidden

## EventSinkContribution

### Purpose

EventSinkContribution adds an observability backend.

### Conceptual shape

```python
EventSinkContribution:
    backend_name: str
    validate_config(config, context) -> None
    create_sink(config, factory_context) -> EventSink
```

### Safety

- EventSink failure must not overwrite the primary failure
- event metadata must be redacted and bounded
- full prompt, raw tool output, and redaction bypass are forbidden

## WorkerContribution

WorkerContribution is future-oriented.

### Purpose

Add a worker or queue backend.

### Conceptual shape

```python
WorkerContribution:
    backend_name: str
    validate_config(config, context) -> None
    create_worker_adapter(config, factory_context) -> WorkerAdapter
```

`WorkerContribution` remains deferred.
`WorkerAdapter` remains deferred.

Long-running capability remains a foundation concern. Worker backend selection is a plugin concern. Application-specific long-running behavior remains in workflow plugins.

## UIContribution

### Purpose

UIContribution adds display metadata and action visibility hints.

### Conceptual shape

```python
UIContribution:
    name: str
    target_type: "workflow" | "tool" | "artifact" | "run"
    target_name: str
    get_metadata(config, context) -> UiMetadata
```

UIContribution provides display metadata only. Policy and authorization remain separate.

Forbidden:

- permission bypass
- hidden field forcing
- raw payload display
- secret display

## Validation hook shape

Validation hooks validate plugin-specific config only.
They do not create runtime dependencies.
They do not receive secret values.

Package MVP may use exceptions for validation errors.
Package Complete may consider a structured `ValidationResult`.

### ValidationContext

Conceptual context:

- plugin name
- contribution name
- environment
- known provider profiles
- known tool names
- enabled plugin set

ValidationContext must not contain:

- LLMClient instance
- ToolRegistry instance
- ArtifactStore instance
- CheckpointStore instance
- EventSink instance
- Django model object
- Run object
- secret value
- raw config source

## Factory hook shape

Factory hooks are called from RuntimeAssembly.
They receive resolved config plus a factory context and create concrete dependencies.

### FactoryContext

Conceptual context:

- environment
- secret resolver
- logger
- limits
- observability settings

FactoryContext must not contain:

- raw config source
- raw Run.input_payload
- Django ORM object
- Run object
- provider raw object from another provider

### SecretResolver

`SecretResolver` is a conceptual boundary that resolves secret values from names such as `LLM_API_KEY`.
It is not implemented in P3-C.

Example flow:

```yaml
ValidatedPackageConfig:
  api_key_env: LLM_API_KEY

FactoryContext:
  secret_resolver

ProviderContribution.create_client:
  secret_resolver.resolve_env("LLM_API_KEY")
```

## Registry keeps no concrete instances

Bad example:

```python
registry.register_provider("litellm", LiteLLMClient(...))
```

Good example:

```python
registry.register_provider(litellm_provider_contribution)
```

Reasons:

- profile-specific instances can be created per config
- secret resolution stays in RuntimeAssembly
- tests can swap factories more easily
- startup avoids unnecessary external connections
- registry does not become a service locator

Registry holds definition / factory / metadata.
RuntimeAssembly holds concrete instances.

## RuntimeAssembly connection

Conceptual flow:

```text
ResolvedWorkflowConfig
  ↓
PluginRegistry contributions
  ↓
RuntimeAssembly factory hook calls
  ↓
RuntimeDependencies
```

Example:

```text
ResolvedWorkflowConfig:
  provider: litellm
  tools.allowed:
    - github.search_issues
  stores.artifact.backend: memory

PluginRegistry:
  litellm ProviderContribution
  github.search_issues ToolContribution
  memory StoreContribution

RuntimeAssembly:
  ProviderContribution.create_client(...)
  ToolContribution.create_tool(...)
  StoreContribution.create_store(...)

RuntimeDependencies:
  llm_client
  tool_registry
  artifact_store
  checkpoint_store
  event_sink
```

RuntimeAssembly calls factory hooks. Registry does not create concrete instances.

## ConfigValidator connection

Validation flow:

```text
RawPackageConfig
  ↓
raw schema validation
  ↓
security validation
  ↓
semantic validation with registry lookup
  ↓
plugin-specific validation hooks
  ↓
ValidatedPackageConfig
```

Example hooks:

- WorkflowContribution.validate_config -> workflow-specific config
- ProviderContribution.validate_profile -> provider profile
- ToolContribution.validate_config -> tool-specific config
- StoreContribution.validate_config -> store backend config
- EventSinkContribution.validate_config -> event sink backend config

Validation hooks do not create runtime dependencies.
Factory hooks do not replace validation.

## Future public facade

Current public facade:

- `langgraph_automation.api.llm`
- `langgraph_automation.api.tools`
- `langgraph_automation.api.stores`
- `langgraph_automation.api.events`

Future public facade candidates:

- `langgraph_automation.api.plugins`
- `langgraph_automation.api.workflow`
- `langgraph_automation.api.runtime`
- `langgraph_automation.api.errors`

P3-C does not create those modules.
Public API should not be frozen prematurely.

## Future errors

Future candidate errors may include:

- `PluginRegistrationError`
- `PluginConflictError`
- `DuplicatePluginError`
- `UnknownPluginError`
- `PluginValidationError`
- `IncompatiblePluginError`

P3-C does not create `api.errors` or any error classes.

## P3-C done when

- plugin object shape is defined
- plugin metadata shape is fixed
- plugin contributions are separated by type
- validation and factory hooks are separated
- ValidationContext and FactoryContext are defined conceptually
- SecretResolver is defined conceptually
- registry keeps no concrete runtime instances
- RuntimeAssembly and ConfigValidator boundaries are fixed
- public API facades are not prematurely frozen

Plugin API facade staging is defined in `PLUGIN_API_FACADE.md`.


## Factory Hooks

Contribution factory hooks are the runtime assembly boundary:

- `ProviderContribution.create_client`
- `ToolContribution.create_tool`
- `StoreContribution.create_store`
- `EventSinkContribution.create_sink`

RuntimeAssembly calls factory hooks with keyword arguments:

- `config`
- `context`

Validation hooks remain ConfigValidator responsibility.
