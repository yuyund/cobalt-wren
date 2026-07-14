# Manual Plugin Registration

This document defines the manual plugin registration boundary for `langgraph-automation`.

Purpose:

- make `PluginRegistry` responsibilities explicit
- fix the conceptual shape of manual registration
- separate plugin package from plugin contribution
- define the minimal plugin metadata shape
- fix name conflict, duplicate registration, and override policy
- define `plugins.enabled`
- distinguish registered plugins from enabled plugins
- clarify the validation call boundary for plugin-specific validation
- separate `ConfigLoader`, `ConfigValidator`, `PluginRegistry`, and `RuntimeAssembly`

## Basic policy

- Package MVP uses manual, explicit registration
- Package Complete may add Python entry point discovery

In Package MVP, application or bootstrap code registers plugin objects directly into a `PluginRegistry` instance.
Config does not name import paths. Config only activates already-registered plugins and supplies behavior parameters.
Manual registration registers plugin objects and their contributions. Plugin object and contribution shapes are defined in `docs/PLUGIN_API_SHAPE.md`.
Public facade staging for plugin API types is defined in `docs/PLUGIN_API_FACADE.md`.

Conceptual example only:

```python
registry = PluginRegistry()

registry.register(company_agent_plugin)
registry.register(github_tools_plugin)
registry.register(litellm_provider_plugin)
```

## PluginRegistry responsibilities

### Registry responsibilities

`PluginRegistry` is responsible for:

- plugin registration
- plugin metadata lookup
- workflow kind lookup
- tool name lookup
- provider name lookup
- store backend lookup
- event sink backend lookup
- worker backend lookup
- UI extension lookup
- duplicate registration detection
- name conflict detection

### Registry non-responsibilities

`PluginRegistry` does not handle:

- config file loading
- YAML/TOML parsing
- Django settings loading
- environment variable resolution
- secret value resolution
- runtime dependency construction
- `LLMClient` instance construction
- `ToolRegistry` instance construction
- `ArtifactStore` / `CheckpointStore` instance construction
- Run lifecycle
- Django ORM access
- workflow execution
- safety redaction execution
- result safety enforcement

Registry is a lookup boundary, not a runtime assembly boundary.

## Registry scope

The registry stores plugin packages, but indexes contribution types separately.

Contribution scopes:

- workflow contributions
- tool contributions
- provider contributions
- store contributions
- event sink contributions
- worker contributions
- UI contributions

Example shape:

```yaml
github:
  package_name: github
  contributions:
    tools:
      - github.search_issues
      - github.create_issue
    ui:
      - github.issue_link_renderer
```

Plugin package and plugin contribution are distinct concepts. One plugin package may provide multiple contributions.

Lookup examples:

```python
registry.get_tool("github.search_issues")
registry.get_provider("litellm")
registry.get_workflow("company_agent")
registry.get_store_backend("memory")
```

## Plugin package vs contribution

### Plugin package

A plugin package is a plugin unit that carries metadata, contributions, and validation hooks.

### Plugin contribution

A plugin contribution is a type/name-addressable offering such as a workflow, tool, provider, store backend, event sink backend, worker backend, or UI extension.

Example:

- Plugin package: `github`
- ToolPlugin contributions: `github.search_issues`, `github.create_issue`
- UIPlugin contribution: `github.issue_link_renderer`

## Plugin metadata

The minimal future metadata shape is:

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
- concrete runtime instances
- provider raw objects
- Django model objects
- Run objects
- raw config sources
- env var values

## Naming policy

### Workflow kind

Short-term compatibility may keep existing names such as:

- `llm_echo_summary`
- `company_agent`

Namespace style is recommended long term:

- `reference.llm_echo_summary`
- `company.agent`

### Tool name

Tool names should be namespace-oriented, or close to mandatory namespace-oriented naming.

Good examples:

- `github.search_issues`
- `github.create_issue`
- `filesystem.read_file`
- `slack.post_message`

Bad examples:

- `search`
- `create`
- `run`

### Provider name

Examples:

- `litellm`
- `openai`
- `ollama`
- `anthropic`

### Store backend name

Examples:

- `memory`
- `local_file`
- `s3`
- `postgres`

### EventSink backend name

Examples:

- `none`
- `stdout`
- `opentelemetry`
- `langfuse`

### Worker backend name

Examples:

- `local`
- `celery`
- `rq`

## Conflict policy

### Same-scope duplicate names

Duplicate names in the same registry scope are rejected.

Example:

- `github.search_issues`
- `github.search_issues`

Result:

- reject

### Different-scope same names

Same names across different scopes may be allowed.

Example:

- ProviderPlugin contribution: `memory`
- StorePlugin contribution: `memory`

Result:

- allowed because the scope differs

Lookup is always by scope plus name.

## Duplicate registration policy

- Package MVP rejects duplicate registration
- Package Complete may consider same-plugin-identity idempotent registration

Reason:

- keep MVP behavior simple
- avoid accidental double registration or override
- avoid startup-order ambiguity

## Override policy

- default deny

Overriding an existing contribution with a later registration is not allowed in Package MVP.

Package Complete may consider an explicit developer-only override option, but the default remains deny.

## Manual registration API shape

Conceptual core shape:

```python
registry = PluginRegistry()
registry.register(plugin)
```

Why this shape:

- avoids global state
- makes isolated test registries easy
- scales to multiple application instances or environments

Global helper APIs are future convenience only.

## plugins.enabled

`plugins.enabled` selects from manually registered plugins.

It is not:

- an import path
- a package install instruction
- a discovery instruction
- arbitrary Python import

Example:

```yaml
plugins:
  enabled:
    - github
    - company_agent
```

Behavior:

- registered and enabled: part of the effective plugin set
- registered but disabled: present in registry, excluded from this configuration
- enabled but not registered: validation error
- disabled plugin referenced by config: validation error
- duplicate registered plugin: registration error

## Registered vs enabled

### Registered plugin

A registered plugin is a plugin object that application or bootstrap code has added to `PluginRegistry`.

### Enabled plugin

An enabled plugin is a registered plugin whose name appears in `ValidatedPackageConfig.plugins.enabled`.

### EffectivePluginSet

The effective plugin set is the conceptual intersection of registered plugins and enabled plugin names.

`EffectivePluginSet` is a design concept only. It is not implemented in P3-B.

## Validation boundary

P1-B validation layering still applies:

- Layer 1: raw schema validation
- Layer 2: security validation
- Layer 3: semantic validation using registry lookup
- Layer 4: plugin-specific validation

### WorkflowPlugin validation

WorkflowPlugin validates `workflows.<name>.config`.

Core knows:

- `enabled`
- `kind`
- `llm_profile`
- `tools`
- `limits`

WorkflowPlugin knows:

- `workflows.<name>.config`

### ProviderPlugin validation

ProviderPlugin validates provider-specific profile parameters.

Core may validate the provider name and profile reference. Provider-specific options are validated by the provider plugin.

### ToolPlugin validation

ToolPlugin validates:

- tool-specific config
- tool input schema
- tool output schema

ToolPolicy enforcement remains in the foundation.

ToolPlugin provides capability. ToolPolicy grants usage.

### StorePlugin / EventSinkPlugin / WorkerPlugin / UIPlugin validation

- StorePlugin validates backend-specific config
- EventSinkPlugin validates observability backend-specific config
- WorkerPlugin validates worker backend-specific config
- UIPlugin validates display metadata and visibility hints

## Registry / validator / runtime assembly

### ConfigLoader

ConfigLoader reads raw config sources.

### ConfigNormalizer

ConfigNormalizer converts `RawPackageConfig` into `ValidatedPackageConfig`.

### PluginRegistry

PluginRegistry stores registered plugin contributions and exposes lookup helpers.

### ConfigValidator

ConfigValidator orchestrates semantic validation and plugin-specific validation using registry lookup.

### RuntimeAssembly

RuntimeAssembly uses `ResolvedWorkflowConfig` plus `PluginRegistry` lookup results to build runtime dependencies.

Important boundaries:

- ConfigLoader does not create plugin instances
- PluginRegistry does not read config sources
- PluginRegistry does not build runtime dependencies
- RuntimeAssembly does not read raw config sources
- Plugin code does not directly touch Django ORM or Run lifecycle

## Registry lookup boundaries

Registry lookup helpers conceptually include:

- `has_workflow_kind(kind)`
- `get_workflow(kind)`
- `has_tool(name)`
- `get_tool(name)`
- `has_provider(provider)`
- `get_provider(provider)`
- `has_store_backend(backend)`
- `get_store_backend(backend)`
- `has_event_sink_backend(backend)`
- `get_event_sink_backend(backend)`
- `has_worker_backend(backend)`
- `get_worker_backend(backend)`

Registry provides lookup. Validator orchestrates validation. RuntimeAssembly constructs concrete dependencies.

## Runtime assembly boundary

RuntimeAssembly consumes resolved config and registry lookup results.

Examples of lookup use:

```python
registry.get_provider("litellm")
registry.get_tool("github.search_issues")
registry.get_store_backend("memory")
```

RuntimeDependencies remain the concrete runtime outputs such as `LLMClient`, `ToolRegistry`, `ArtifactStore`, `CheckpointStore`, and `EventSink`.

P3-B does not implement any of these types or constructors.

## Validation result policy

Package MVP may use exceptions for validation errors.

Package Complete may consider a structured `ValidationResult`.

## Plugin API version compatibility

Package MVP records required public API version metadata only.

Example:

```yaml
requires:
  public_api_version: ">=0.1,<1.0"
```

Package Complete may reject incompatible plugins and define deprecation / migration policy.

## Plugin lifecycle

1. Application or bootstrap code constructs plugin objects.
2. Plugin objects are manually registered into `PluginRegistry`.
3. Registry indexes plugin contributions by type and name.
4. Config validation uses registry lookup and plugin-specific validation hooks.
5. RuntimeAssembly uses registry lookup to build concrete runtime dependencies.
6. Execution uses `RuntimeDependencies` and `GraphRuntimeConfig`.

## Bootstrapping boundary

Manual registration may occur from:

- Django app startup
- CLI entrypoint
- test fixture
- application bootstrap module

Responsibility split:

- package core provides registry types and registration API shape
- application/bootstrap decides which plugins to register
- config decides which registered plugins are enabled
- registry stores registered plugins and contributions

`plugins.enabled` never triggers plugin imports.

## Security boundary

Plugins are trusted extension code, but they still may not bypass safety or policy.

Forbidden even for plugins:

- ToolPolicy bypass
- safety redaction bypass
- raw persistence bypass
- direct Run lifecycle mutation
- Django model direct dependency
- internal service dependency

ToolPlugin provides capability. ToolPolicy grants usage.

## P3-B done when

- PluginRegistry responsibilities are fixed.
- manual registration is defined.
- package vs contribution is separated.
- plugin metadata minimum is fixed.
- name conflict, duplicate registration, and override policy are fixed.
- `plugins.enabled` is defined.
- registered vs enabled plugins are separated.
- validation boundary is fixed.
- registry / validator / runtime assembly relationship is fixed.
