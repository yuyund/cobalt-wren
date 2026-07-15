# Package Verification Strategy

This document defines the verification strategy for package-facing boundaries.

## Levels

### L0: Import / Public API Check

- verify that public facades can be imported
- verify that package internals are not required for basic import

### L1: Contract Unit Tests

- verify config, plugin, runtime, and workflow contracts in isolation

### L2: Boundary Tests

- verify that forbidden imports are not present
- verify that internal modules stay behind the expected boundaries

### L3: Integration Tests

- verify that config -> runtime -> workflow preparation can flow through the package-facing entrypoint
- for this phase, the package-facing entrypoint is `langgraph_automation.api.engine`
- api.engine integration is verified in Block M

### L4: Headless Smoke Tests

- verify that the reference workflow can be prepared through the package-facing path
- reference.llm_echo_summary headless prepare is verified in Block M

### L5: Failure Matrix Tests

- verify that unknown workflow, missing provider, build failure, and factory failure paths fail safely
- facade-level failure coverage is verified in Block M
- execution-path raw output persistence remains covered by lower-level runtime tests

### L6: Application-Facing Tests

- verify that apps/automation or a sample application uses package facade entrypoints only

## Failure Matrix

At minimum, cover the following cases:

- unknown workflow kind
- missing provider profile
- missing tool
- missing artifact store
- missing checkpoint store
- missing event sink
- workflow build returns `None`
- workflow build raises an arbitrary exception
- provider failure
- tool failure
- unsafe raw output attempt
- secret-like metadata attempt

Expected behavior:

- safe_message only
- no raw traceback in user-facing paths
- no raw provider response saved
- no raw ToolResult.output saved
- no dangerous data in Run.error_message
- primary failure is not overwritten by secondary failure

## Transitional Bridge Note

The current service-layer workflow preparation bridge is acceptable as a transitional integration point.
It is not the final package-facing boundary.
The long-term direction is to route service/control-plane code through a package facade.

## Package Facade Verification

The first package-facade verification target should be:

- `create_engine(config_mapping)`
- `engine.prepare_workflow("reference.llm_echo_summary")`
- `EnginePreparedWorkflow`

Verification levels:

- L3: config -> runtime -> workflow preparation through `api.engine`
- L4: reference workflow headless prepare through `api.engine`
- L5: facade-level safe failures verified through `api.engine`

Headless smoke tests should only prepare workflows.
They should not require provider network calls or graph execution.

## Block N Update

L6 remains pending and depends on service integration via api.engine.
Boundary Hardening Block N prepares L6 by preventing new application/control-plane leakage into package internals.
