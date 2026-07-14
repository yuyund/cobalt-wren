# ADR 0004: Public / internal API surface

## Status

Accepted

## Context

Foundation C5/D0 established the execution foundation and the workflow catalog boundary.

The next step toward package / plugin framework support is to limit which API surface external plugin authors may depend on.

If external users import internal modules directly, future design changes will break plugins too easily.

## Decision

- Public API will be provided as a facade.
- Public vocabulary should move toward `workflow` terms.
- Internal implementation may keep `graph` vocabulary.
- Plugin authors should eventually depend on `langgraph_automation.api.*`.
- `apps/automation/services`, `graphs` runner/builders, core safety internals, and concrete integrations remain internal.
- `workflows/catalog.py` is package composition internal; future workflow extension should go through a registration API.
- Package P0-A is docs only, and `api/` modules are not implemented yet.

## Consequences

- The public surface can stay small.
- Internal implementation can change without breaking external users as often.
- Plugin API and config API design can be finalized before widening external exposure.
- Package P0-B can later evaluate a minimal facade or re-export layer.
