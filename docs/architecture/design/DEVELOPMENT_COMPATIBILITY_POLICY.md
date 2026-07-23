# Development Compatibility Policy

The package is not released and has no production consumers. Backward compatibility is therefore not a design requirement during the current development phase.

## Policy

- Prefer the intended final API and data model over aliases, deprecation shims, and dual entry points.
- Rename or remove provisional APIs directly when the replacement is clearer.
- Do not preserve old payload shapes, workflow-kind aliases, or test-only public parameters solely to avoid updating callers in this repository.
- Keep temporary internal seams only when they make a migration independently testable or materially reduce implementation risk.
- Remove those seams when the migration step they support is complete.

## Not Compatibility Concerns

The following remain mandatory because they are correctness properties rather than consumer compatibility:

- an executing or prepared workflow uses a coherent engine snapshot;
- engine reload is atomic and preserves last-known-good state on candidate failure;
- concurrent runs are not redirected mid-execution;
- persisted output and errors remain safely normalized;
- configuration and plugin failures fail closed;
- observability failures do not replace primary execution results.

## Current Execution Path

The Django Run lifecycle uses only the public executable contract. LangGraph remains an internal implementation detail of the built-in reference workflow and graph-layer tests; it is not a control-plane fallback.
