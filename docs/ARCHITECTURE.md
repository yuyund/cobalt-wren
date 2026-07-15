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

## Config Core Boundary

- `langgraph_automation.config.*` is internal/provisional
- config core normalizes Mapping input into typed package config
- config core does not depend on `api.plugins`
- config core does not depend on `PluginRegistry`
- `ConfigValidator` and `RuntimeAssembly` are later layers
- no public `api.config` facade exists yet

## Plugin Boundary

- `api.plugins` is a public facade for plugin vocabulary.
- `PluginRegistry` is an internal manual registration mechanism.
- `api.plugins` does not depend on `PluginRegistry`.
- `PluginRegistry` depends on `api.plugins`, `api.workflow`, and `api.errors` only.
- `ConfigLoader`, `ConfigValidator`, and `RuntimeAssembly` are later layers.
- plugin taxonomy and responsibility boundaries are defined in `docs/PLUGINS.md`.
- manual registration, enabled plugins, and registry conflict policy are defined in `docs/PLUGIN_REGISTRATION.md`.
- validation hooks and factory hooks are defined in `docs/PLUGIN_API_SHAPE.md`.
- plugin API facade staging is defined in `docs/PLUGIN_API_FACADE.md`.
- workflow API facade staging is defined in `docs/API_SURFACE.md`.
- error categories and primary failure preservation are defined in `docs/ERROR_TAXONOMY.md`.
- ConfigValidator calls contribution validation hooks.
- RuntimeAssembly calls contribution factory hooks.
- GraphRuntime and GraphDefinition remain outside the public facade.
- Built-in reference workflows are composed through `workflows.catalog` and `workflows.adapter`, while `workflows.reference.*` stays internal.

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


## Config Validation Boundary

- `langgraph_automation.config.validator` is the first config layer allowed to depend on `langgraph_automation.plugins.registry`
- `langgraph_automation.config.models`, `loader`, `normalizer`, and `security` remain free of registry and plugin facade dependencies
- `api.workflow` defines the public workflow vocabulary for plugin contributions
- `ConfigValidator` turns `NormalizedPackageConfig` into `ValidatedPackageConfig`
- `EffectivePluginSet` is a validation-time projection of enabled plugins, not the full registry
- `RuntimeAssembly` remains a later layer and still does not exist yet


## Runtime Assembly Boundary

- `langgraph_automation.runtime.*` is internal/provisional
- runtime assembly consumes `ValidatedPackageConfig` and `EffectivePluginSet`
- runtime assembly does not depend on `PluginRegistry`
- runtime assembly does not perform validation
- runtime assembly does not execute workflows or graph nodes
- `api.runtime` remains unimplemented

## Built-in Wiring Boundary

- built-in/reference workflows are represented as ordinary `Plugin` objects
- built-in workflow contributions are routed through `api.workflow` and `PluginRegistry`
- `workflows.adapter` is the only place that calls `WorkflowDefinition.build`
- `workflows.requirements` is the internal `WorkflowRequirements` / `RuntimeDependencies` checker
- built-in wiring does not require `ConfigValidator` or `RuntimeAssembler` to expand their responsibilities
- `graphs.*` remains the internal graph foundation and does not import workflow catalog code

## Application Readiness Boundary

- application workflows are expected to be represented as ordinary `Plugin` objects
- application workflows contribute `WorkflowContribution`
- application workflows declare `WorkflowRequirements`
- public workflow vocabulary lives in `api.workflow`
- runtime assembly and registry usage remain framework responsibilities
- application workflow code must not depend on control-plane or Django internals directly
- `reference.llm_echo_summary` is the built-in readiness example
- it demonstrates the `Plugin -> WorkflowContribution -> WorkflowDefinition -> requirements/build` boundary

## Workflow Preparation

- workflow preparation resolves a workflow kind through `PluginRegistry`
- workflow preparation obtains `WorkflowContribution` and `WorkflowDefinition`
- workflow preparation checks `WorkflowRequirements` against `RuntimeDependencies`
- workflow preparation builds the internal graph through `workflows.adapter`
- workflow preparation returns `PreparedWorkflow`
- workflow preparation does not execute graphs
- workflow preparation does not modify the Run lifecycle
- workflow preparation does not call `RuntimeAssembler`
- workflow preparation does not call `ConfigValidator`

## Service Workflow Integration

- service layer creates or receives `RuntimeDependencies`
- service layer resolves workflow kinds through `WorkflowPreparer`
- service layer may use the built-in workflow registry helper
- `WorkflowPreparer` returns `PreparedWorkflow`
- service layer can pass `PreparedWorkflow.graph` to the existing runner path
- service layer does not bypass safe output or safe error contracts

## Package Facade Direction

- the service-layer workflow preparation bridge is transitional
- it is not the final package API
- it is not the application-facing API
- the provisional package facade is `langgraph_automation.api.engine`
- package facade should hide `PluginRegistry`, `WorkflowPreparer`, `workflows.catalog`, `workflows.adapter`, `workflows.requirements`, `ConfigValidator`, and `RuntimeAssembler`
- `apps/automation` should not become the final permanent dependency on package internals
- future service integration should route through the package facade instead of package internals

## Package Facade Boundary Hardening

application/control-plane code should use `langgraph_automation.api.engine` as the package-facing facade.

`apps/automation/services/workflow_preparation.py` now routes through `api.engine`; the transitional exception is removed.

Package internals hidden from control-plane:

- `PluginRegistry`
- `ConfigValidator`
- `RuntimeAssembler`
- `RuntimeDependencies`
- `WorkflowPreparer`
- `workflows.catalog`
- `workflows.prepare`
- `workflows.adapter`
- `workflows.requirements`
- `graphs.*`
