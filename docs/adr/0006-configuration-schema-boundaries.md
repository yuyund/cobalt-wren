# ADR 0006: Configuration schema boundaries

## Status

Accepted

## Context

Package P1-A organized configuration taxonomy.

Before implementing config loader, schema, or plugin integration, the project needs fixed boundaries between raw config, validated config, and resolved workflow config.

If runtime reads raw source or DB payloads directly, source additions and schema changes will spread across the system.

## Decision

- Split config schema into `RawPackageConfig`, `ValidatedPackageConfig`, and `ResolvedWorkflowConfig`.
- Runtime assembly must not read raw config sources directly; it only sees validated / resolved config.
- `Run.input_payload` is not a config override.
- Use source precedence of built-in defaults < config file < environment override < Django settings.
- Treat `Workflow.definition_payload` as workflow-instance-specific config layered on top of validated package defaults.
- Core config rejects unknown fields.
- Workflow-specific config is kept as an opaque mapping in core and validated by plugin-specific schema.
- Provider / store / worker / observability resolution is name-based, not arbitrary import-based.
- Secret values are not stored in config; only env var references are allowed.

## Consequences

- Adding config sources will have less blast radius on runtime behavior.
- Plugin-specific config can expand without polluting the core schema.
- Provider / store / worker implementation swaps can be absorbed by registry boundaries.
- Safety, validation, and resolution responsibilities are fixed before config loader implementation begins.
