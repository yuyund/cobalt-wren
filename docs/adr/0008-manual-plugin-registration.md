# ADR 0008: Manual plugin registration

## Status

Accepted

## Context

Package P3-A organized plugin taxonomy.

Config schema now names providers, backends, plugin names, workflow kinds, and tool names, and the registry boundary is intended to resolve names to implementations.

Before moving to plugin loader or entry point discovery, Package MVP needs a manual registration boundary.

Allowing arbitrary imports from config would weaken security, reproducibility, and loose coupling.

## Decision

- Package MVP uses manual, explicit registration.
- Application or bootstrap code registers plugin objects into a `PluginRegistry` instance.
- `PluginRegistry` handles registration, metadata lookup, contribution lookup, and conflict detection.
- `PluginRegistry` does not handle config loading, secret resolution, runtime dependency construction, Run lifecycle, or Django ORM access.
- Plugin package and plugin contribution are separate concepts.
- Same-scope duplicate contributions are rejected.
- Package MVP rejects duplicate registration.
- Override is denied by default.
- `plugins.enabled` is an activation list for registered plugins, not an import path or discovery mechanism.
- Registered plugins and enabled plugins are separate concepts, and the effective plugin set is derived from registry contents and `ValidatedPackageConfig`.
- Registry provides lookup helpers; validator orchestrates validation; runtime assembly constructs concrete dependencies.

## Consequences

- Config no longer depends on arbitrary Python import paths.
- Plugin discovery complexity can be deferred to Package Complete.
- Tests can use isolated registries easily.
- Bootstrap code has an explicit responsibility for plugin selection.
- ConfigLoader, PluginRegistry, and RuntimeAssembly responsibilities remain separated.
