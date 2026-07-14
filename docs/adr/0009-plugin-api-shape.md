# ADR 0009: Plugin API shape

## Status

Accepted

## Context

Package P3-A organized plugin taxonomy, and Package P3-B organized manual plugin registration.

Before implementing plugin registry, config validation, or runtime assembly, the project needs fixed shapes for plugin objects and contribution objects.

If one plugin package could only provide one contribution, integration plugins would become less extensible.

If the registry held concrete runtime instances, secret resolution, config profile shape, and runtime assembly responsibilities would blur together.

## Decision

- Separate plugin package from plugin contribution.
- Plugin objects hold metadata and contributions.
- `PluginMetadata` holds name, version, description, plugin_types, provides, and requires.
- `PluginContributions` groups workflows, tools, providers, stores, event_sinks, workers, and ui.
- Contribution types have separate validation and factory hooks.
- Validation hooks only validate config and do not create runtime dependencies.
- Factory hooks are called from RuntimeAssembly and create concrete runtime dependencies.
- PluginRegistry stores contribution definitions, factories, and metadata, and does not store concrete runtime instances.
- ConfigValidator calls validation hooks, and RuntimeAssembly calls factory hooks.
- Secrets are resolved through a SecretResolver-like boundary and are not stored in ValidatedPackageConfig or ResolvedWorkflowConfig.
- P3-C does not implement `api.plugins`, `api.workflow`, `api.runtime`, or `api.errors`.

## Consequences

- registry, validator, and runtime assembly responsibilities remain separated
- contribution-specific changes stay localized
- integration plugins can provide multiple tools, UI metadata, or providers without flattening into one monolithic interface
- premature public API freezing is avoided
- PluginRegistry is less likely to become a service locator
