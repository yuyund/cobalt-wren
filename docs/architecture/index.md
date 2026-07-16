# Architecture Docs

This folder explains the system shape, layer boundaries, and dataflow rules.

## Entry Points
- `layers/index.md`: the layer map and responsibilities.
- `dataflow/DATAFLOW.md`: the main dependency and flow summary.
- `audit/index.md`: the boundary audit entry point.
- `audit/PERSISTENCE_FAILURE_MODE_AUDIT.md`: the persistence durability and failure-mode audit.

## Read Next
- If you are changing imports or dependency direction, start with the layer map.
- If you are checking safety or boundary drift, move to the dataflow summary and audit.
