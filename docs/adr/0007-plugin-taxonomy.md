# ADR 0007: Plugin taxonomy

## Status

Accepted

## Context

Package P0 minimized the public API facade, and Package P1 organized configuration taxonomy and schema boundaries.

Before implementing the plugin framework, the project needs fixed boundaries for plugin types, responsibilities, config validation, and registration / resolution.

If plugins depend on internal modules, foundation changes will leak into external plugins too easily.

## Decision

- Split plugin taxonomy into `WorkflowPlugin`, `ToolPlugin`, `ProviderPlugin`, `StorePlugin`, `EventSinkPlugin`, `WorkerPlugin`, and `UIPlugin`.
- Plugins depend on the public API facade, not internal modules.
- Config specifies plugin / provider / backend / workflow kind / tool names, and registries resolve names to implementations.
- Package MVP uses manual, explicit registration.
- Package Complete may add Python entry point discovery.
- Workflow-specific and plugin-specific config stay opaque in core schema and are validated by plugin-specific validation.
- ToolPlugin remains subject to ToolPolicy and cannot bypass it.

## Consequences

- Plugin API responsibilities are fixed before implementation starts.
- Config schema does not need arbitrary imports or implementation paths.
- External plugins remain less coupled to foundation internals.
- Package MVP can validate registry boundaries without discovery complexity.
