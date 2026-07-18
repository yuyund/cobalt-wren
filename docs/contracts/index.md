# Contracts Docs

This folder holds the invariants that cross package and subsystem boundaries.

## Entry Points
- `core/index.md`: repo-wide contracts and responsibilities.
- `errors/index.md`: error categories and preservation rules.
- `integrations/index.md`: integration-specific durable backend contracts.

## Read Next
- Read the core contracts doc before making broad refactors.
- Use the error taxonomy when changing failure shapes or public exceptions.
- Use the integration contracts when changing durable artifact or checkpoint storage.
