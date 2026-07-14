# Architecture

## Layers

- `apps/automation`
- `graphs`
- `workflows`
- `workflows/reference`
- `workflows/applications`
- `workflows/catalog`
- `integrations`
- `core`
- `apps/web`

## Responsibilities

### apps/automation

- control plane
- Run lifecycle
- workflow config
- runtime assembly

### graphs

- execution foundation
- registry mechanism
- runtime
- runner
- builders
- instrumentation

### workflows/catalog

- built-in workflow definitions の composition

### workflows/reference

- diagnostic / smoke-test workflows

### workflows/applications

- future application workflows

### integrations

- external I/O boundary
- LLM / tool / artifact / checkpoint / observability

### plugins

- extension points outside the foundation core
- plugin registration and name-based resolution
- plugin-specific validation and metadata

### plugin_registry

- lookup and registration boundary
- not a runtime assembly boundary
- does not load config sources or create plugin instances
- stores contribution definitions, factories, and metadata, not concrete runtime instances

### core

- redaction / result safety / summary helpers

### apps/web

- UI layer

## Dependency Direction

- `apps/automation/services` may depend on `workflows/catalog`, `workflows/reference/*`, `graphs` registry/runtime types, and integration interfaces.
- `graphs` must not depend on workflows.
- `workflows` may use graphs public/foundation types.
- `workflows` must not depend on `apps/automation/services`.

## Forbidden Dependencies

- `graphs -> workflows/reference` forbidden
- `graphs -> workflows/applications` forbidden
- `graphs -> apps/automation/services` forbidden
- `graphs/builders.py -> concrete workflow import` forbidden
- `graphs/registry.py -> concrete workflow import` forbidden

- `workflows/reference -> apps/automation/services` forbidden
- `workflows/reference -> Django ORM` forbidden
- `workflows/reference -> concrete LiteLLMClient` forbidden
- `workflows/reference -> concrete EchoTool` forbidden

- workflow nodes -> Django settings forbidden
- workflow nodes -> provider raw object persistence forbidden
- workflow nodes -> raw `ToolResult.output` persistence forbidden

## Boundary Intent

The execution foundation owns reusable runtime mechanics.

Concrete workflow definitions live in workflow packages and are composed through `workflows/catalog`.

Reference workflows exist to verify wiring and safety.

Application workflows are future layers and should not be pulled into `graphs`.


## Configuration Boundary

- Config must not depend on internal module paths.
- Workflow structure belongs in plugin code.
- Workflow behavior parameters belong in config.
- Runtime assembly must use validated normalized config, not raw config sources.

## Configuration Schema Boundary

- runtime does not read raw config sources.
- config source handling is isolated behind loader / normalizer / validator boundaries.
- provider / store / worker / observability implementations are resolved by name through registries.
- workflow-specific config is validated by workflow plugin schema, not core schema.

## Plugin Boundary

- `api.plugins` is a public facade for plugin vocabulary.
- `PluginRegistry` is an internal manual registration mechanism.
- `api.plugins` does not depend on `PluginRegistry`.
- `PluginRegistry` depends on `api.plugins` and `api.errors` only.
- `ConfigLoader`, `ConfigValidator`, and `RuntimeAssembly` are later layers.
- plugin taxonomy and responsibility boundaries are defined in `docs/PLUGINS.md`.
- manual registration, enabled plugins, and registry conflict policy are defined in `docs/PLUGIN_REGISTRATION.md`.
- validation hooks and factory hooks are defined in `docs/PLUGIN_API_SHAPE.md`.
- plugin API facade staging is defined in `docs/PLUGIN_API_FACADE.md`.
- error categories and primary failure preservation are defined in `docs/ERROR_TAXONOMY.md`.
- ConfigValidator calls contribution validation hooks.
- RuntimeAssembly calls contribution factory hooks.
- GraphRuntime and GraphDefinition remain outside the public facade.

## Error Boundary

- `api.errors` is a public facade boundary, not an implementation boundary.
- `ConfigLoader`, `PluginRegistry`, `ConfigValidator`, and `RuntimeAssembly` should share framework error categories without depending on each other's internals.
- provider, tool, store, and event sink execution errors remain internal or deferred until those boundaries are implemented.
- error taxonomy and `api.errors` staging are defined in `docs/ERROR_TAXONOMY.md` and `docs/API_ERRORS_FACADE.md`.

## Public API Direction

- A future public facade is expected under `langgraph_automation.api.*`.
- Plugin authors should not depend on internal modules directly.
- `workflows/catalog.py` is package composition internal / semi-internal, not a public entry point.
- Internal graph vocabulary may remain in foundation code, but public-facing vocabulary should move toward workflow terms.
- ConfigValidator, PluginRegistry, RuntimeAssembly, GraphRuntime, and EventSink have separate error boundaries.
- primary failure preservation is a framework-wide invariant.
