# Plugin Taxonomy

This document defines the plugin taxonomy for `langgraph-automation`.

Purpose:

- make plugin types explicit
- separate responsibilities by plugin type
- limit the public API surface plugins may depend on
- keep plugins off internal implementation modules
- separate config schema, plugin-specific validation, and runtime assembly
- distinguish Package MVP manual registration from Package Complete discovery

Manual registration, conflict policy, enabled plugin handling, and registry boundaries are defined in `docs/PLUGIN_REGISTRATION.md`.
Plugin object shape, contribution shape, validation hooks, and factory hooks are defined in `docs/PLUGIN_API_SHAPE.md`.
Public facade staging for plugin API types is defined in `docs/PLUGIN_API_FACADE.md`.

## System principles

- plugin is an extension point of the package core
- plugin depends on the public API facade, not internal modules
- config specifies plugin name, backend name, provider name, workflow kind, and tool name
- registry resolves names to implementations
- runtime assembly uses resolved config and registry output to build concrete dependencies
- plugin-specific config is validated by the plugin, not by the core schema

## Plugin types

### WorkflowPlugin

Purpose:

- add a workflow kind to the package
- provide graph structure, nodes, routing, state schema, prompt assembly, and domain policy

Provides:

- workflow kind
- workflow metadata
- graph definition or graph builder
- state schema
- node implementations
- workflow-specific config schema and validation
- optional output mapping
- optional UI metadata

Public API dependency:

- future public candidate: `langgraph_automation.api.workflow`
- current public surfaces that a workflow plugin may depend on: `langgraph_automation.api.llm`, `langgraph_automation.api.tools`, `langgraph_automation.api.stores`, `langgraph_automation.api.events`

Config relation:

- core schema knows `enabled`, `kind`, `llm_profile`, `tools`, and `limits`
- `workflows.<name>.config` stays opaque to the core schema
- workflow-specific parameters such as `departments`, `routing_policy`, and `output_format` are plugin-owned

Validation relation:

- core validates workflow kind existence and known references
- WorkflowPlugin validates `workflows.<name>.config`
- workflow plugin must not bypass safety or policy checks

Runtime assembly relation:

- runtime assembly uses the registered workflow implementation to build workflow-specific runtime behavior
- runtime assembly does not infer graph structure from config DSL

Package MVP:

- needed conceptually, but not implemented as a class in this phase

Package Complete:

- may expand into richer metadata, compatibility metadata, and discovery support

### ToolPlugin

Purpose:

- add a tool to the package
- provide execution implementation and safety metadata

Provides:

- tool name
- tool metadata
- capability classification
- input schema
- output schema
- callable implementation
- safety metadata
- optional redaction hints

Public API dependency:

- `langgraph_automation.api.tools`

Config relation:

- tool policy is separate from tool implementation
- `policies.tools` determines whether a workflow may use a tool
- tool presence does not imply permission

Validation relation:

- ToolPlugin validates its own input / output / tool-specific config
- core validates that allowlists reference known tool names
- ToolPlugin must not weaken ToolPolicy

Runtime assembly relation:

- runtime assembly resolves registered tool implementations by name
- runtime assembly still applies policy before execution

Package MVP:

- needed conceptually, but not implemented as a class in this phase

Package Complete:

- may expand to support richer capability metadata and discovery

### ProviderPlugin

Purpose:

- add an LLM or embedding backend
- resolve provider names to concrete clients

Provides:

- provider name
- supported profile schema
- client factory
- provider-specific validation
- optional default parameters

Public API dependency:

- `langgraph_automation.api.llm`

Config relation:

- config names providers and profiles
- config carries env var names, not secret values
- provider config is name-based, not class-path-based

Validation relation:

- ProviderPlugin validates provider-specific profile config
- core validates required provider profile references
- secret values are rejected before runtime assembly

Runtime assembly relation:

- runtime assembly resolves the provider name through the registry
- runtime assembly resolves env vars and constructs the concrete client

Package MVP:

- needed conceptually, but not implemented as a class in this phase

Package Complete:

- may add version compatibility and richer backend discovery

### StorePlugin

Purpose:

- add artifact or checkpoint storage backends

Provides:

- backend name
- store factory
- backend-specific config validation
- retention and size policy support

Public API dependency:

- `langgraph_automation.api.stores`

Config relation:

- config names backend types, not concrete classes
- config may refer to env vars for roots or credentials
- absolute local paths must not be surfaced as public values

Validation relation:

- StorePlugin validates backend-specific config
- core validates backend profile existence

Runtime assembly relation:

- runtime assembly resolves storage backend names and instantiates the concrete store

Package MVP:

- needed conceptually, but not implemented as a class in this phase

Package Complete:

- may add persistent backend discovery and richer policy metadata

### EventSinkPlugin

Purpose:

- add an observability backend
- send execution events and metadata to an external sink

Provides:

- backend name
- EventSink factory
- backend-specific config validation
- metadata limit handling

Public API dependency:

- `langgraph_automation.api.events`

Config relation:

- observability config controls capture level and backend selection
- config must stay redaction-safe

Validation relation:

- EventSinkPlugin validates backend-specific config
- core validates backend profile existence

Runtime assembly relation:

- runtime assembly resolves the sink backend name and constructs the sink
- EventSink failure must not overwrite the primary failure

Package MVP:

- needed conceptually, but not implemented as a class in this phase

Package Complete:

- may add richer observability backends and compatibility metadata

### WorkerPlugin

Purpose:

- add a worker or queue backend for long-running execution

Provides:

- backend name
- queue adapter or worker adapter
- scheduling and retry capability metadata
- backend-specific validation

Public API dependency:

- no dedicated public facade exists yet
- future surface may grow from `langgraph_automation.api.runtime`

Config relation:

- config names a worker backend and queue settings
- worker backend is separate from workflow behavior

Validation relation:

- WorkerPlugin validates backend-specific config
- core validates worker backend references

Runtime assembly relation:

- runtime assembly resolves the worker backend name and builds the adapter

Package MVP:

- taxonomy only in this phase

Package Complete:

- may add compatibility metadata and discovery support

### UIPlugin

Purpose:

- add UI metadata and visibility hints

Provides:

- display metadata
- labels
- field visibility hints
- action visibility hints
- optional UI fragment metadata

Public API dependency:

- no dedicated public facade exists yet
- UI remains a future extension surface

Config relation:

- UI config controls presentation only
- authorization stays in policy and access control, not in UI config

Validation relation:

- UIPlugin validates UI metadata if present
- core does not treat UI config as a permission system

Runtime assembly relation:

- runtime assembly may pass UI metadata through safe boundaries
- runtime assembly does not derive authorization from UI config

Package MVP:

- taxonomy only in this phase

Package Complete:

- may add richer display metadata and UI integration points

## Registration and discovery

### Package MVP

Package MVP uses manual, explicit registration.

Goals:

- keep the implementation simple
- verify registry boundaries directly
- defer entry point discovery complexity

Conceptual example only:

```python
register_plugin(company_agent_plugin)
register_plugin(github_tools_plugin)
```

### Package Complete

Package Complete may add:

- Python entry point discovery
- plugin version compatibility
- optional extras
- deprecation policy
- migration policy

P3-A does not implement discovery.

## Resolution boundary

- config holds plugin name, provider name, backend name, workflow kind, and tool name
- registry resolves names to plugin implementations
- runtime assembly consumes resolved config and registered plugins to build concrete dependencies

Examples:

```yaml
providers:
  llm:
    default:
      provider: litellm
```

```yaml
stores:
  artifact:
    backend: memory
```

```yaml
workflows:
  company_agent:
    kind: company_agent
```

Forbidden example:

```yaml
workflows:
  custom:
    builder: my_package.workflow.build_graph
```

Arbitrary imports and pip-install-by-config are forbidden.

## Validation boundary

- core validation covers top-level schema, security, and known-name existence
- plugin-specific validation covers workflow-specific, provider-specific, tool-specific, store-specific, worker-specific, and UI-specific config
- core keeps plugin-specific config opaque until plugin validation runs

## Dependency boundary

Allowed public facade today:

- `langgraph_automation.api.llm`
- `langgraph_automation.api.tools`
- `langgraph_automation.api.stores`
- `langgraph_automation.api.events`

Future public facade candidates:

- `langgraph_automation.api.workflow`
- `langgraph_automation.api.runtime`
- `langgraph_automation.api.errors`

Forbidden internal dependencies:

- `langgraph_automation.apps.automation.services.*`
- `langgraph_automation.apps.automation.models`
- `langgraph_automation.graphs.runner`
- `langgraph_automation.graphs.builders`
- `langgraph_automation.workflows.catalog`
- `langgraph_automation.core.result_safety`
- `langgraph_automation.core.redaction`
- concrete integrations
- Django settings and model internals

## P3-A done when

- plugin types are defined.
- responsibilities are separated by plugin type.
- plugin dependency boundaries are explicit.
- manual registration is the Package MVP path.
- entry point discovery is deferred to Package Complete.
- plugin-specific validation is owned by plugins.
- core schema keeps plugin-specific config opaque.
