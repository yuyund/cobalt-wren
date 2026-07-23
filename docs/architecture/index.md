# Architecture Docs

This folder explains the system shape, layer boundaries, and dataflow rules.

## Entry Points
- `layers/index.md`: the layer map and responsibilities.
- `dataflow/DATAFLOW.md`: the main dependency and flow summary.
- `audit/index.md`: the boundary audit entry point.
- `audit/PERSISTENCE_FAILURE_MODE_AUDIT.md`: the persistence durability and failure-mode audit.
- `audit/PERSISTENCE_ORCHESTRATION_SUFFICIENCY_AUDIT.md`: the execution persistence sufficiency audit.
- `design/index.md`: package-wide design principles, target backend design notes, and implementation boundaries.

## Read Next
- Start with `design/DESIGN_PRINCIPLES.md` when reviewing a new abstraction, adapter, workflow extension, or UI boundary.
- If you are changing imports or dependency direction, start with the layer map.
- If you are checking safety or boundary drift, move to the dataflow summary and audit.
