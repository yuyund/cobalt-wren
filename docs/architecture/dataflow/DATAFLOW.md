# Dataflow

This document summarizes the important dependency and flow paths.

## Primary Flows
- config flows from `config/loader.py` to `config/normalizer.py` to `config/validator.py` to `runtime/assembly.py`
- workflow preparation flows through `api.engine` and `workflows.prepare`
- execution input flows from `Run.input_payload` into graph execution input and then into safe persistence
- observability flows through the Django event sink and observed client/registry wrappers
- external OSS signals flow through an integration helper into canonical control-plane records and bounded versioned projections
- dynamic presentation flows from canonical records plus registered integration view sections into renderer-owned safe blocks

## Boundary Rules
- `graphs` must stay free of workflow catalog imports
- `workflows` must not depend on control-plane internals
- `apps/automation` should keep direct graph/runtime usage only in the exact execution adapters
- `apps/web` should render from builders and redaction helpers, not model internals

## Read Next
- Read the layer map first, then use the boundary audit for enforcement details.

