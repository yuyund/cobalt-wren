# ADR 0005: Configuration taxonomy

## Status

Accepted

## Context

Package P0 minimized the public API facade.

The next step before any package / plugin framework work is to define what configuration may change and what must remain in plugin code.

If config depends on internal implementation or arbitrary import paths, looseness and safety both degrade.

## Decision

- Config is limited to declarative behavior parameters.
- Workflow graph / node / routing / domain logic stay in plugin code.
- Foundation guarantees Run lifecycle, policy enforcement, safety, and observability.
- Config must not allow arbitrary Python imports, safety bypasses, secret values, or raw persistence.
- Package-level config, `Workflow.definition_payload`, and `Run.input_payload` are separate concerns.
- Config sources may be plural, but runtime assembly must use normalized validated config.

## Consequences

- Config loader / schema work can start with clear responsibility boundaries.
- Plugin APIs will be less likely to collapse into a config DSL.
- Provider / store / worker backends can still be resolved by name.
- Application workflows remain plugin code rather than config expressions.
