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
- for this phase, the package-facing entrypoint is `cobalt_wren.api.engine`
- api.engine integration is verified in Block M

### L4: Headless Smoke Tests

- verify that an explicitly registered workflow can be prepared through the package-facing path
- explicit test-plugin headless prepare is verified in Block M

### L5: Failure Matrix Tests

- verify that unknown workflow, missing provider, build failure, and factory failure paths fail safely
- facade-level failure coverage is verified in Block M
- execution-path raw output persistence remains covered by lower-level runtime tests

### L6: Application-Facing Tests

- verify that apps/automation or a sample application uses package facade entrypoints only
- L6 is implemented through the service bridge now routing through `api.engine`

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

## Service Integration Note

The service-layer workflow preparation bridge now routes through `api.engine`.
The long-term direction remains to keep application/control-plane code on the package-facing facade and away from package internals.

## Package Facade Verification

The first package-facade verification target should be:

- `create_engine(config_mapping)`
- `engine.prepare_workflow("acme.document_summary")`
- `EnginePreparedWorkflow`

Verification levels:

- L3: config -> runtime -> workflow preparation through `api.engine`
- L4: explicit test workflow headless prepare through `api.engine`
- L5: facade-level safe failures verified through `api.engine`

Headless smoke tests should only prepare workflows.
They should not require provider network calls or graph execution.

## Block O Update

L6 is implemented.
Service Integration via Package Facade Block O verifies that apps/automation can prepare workflows through `api.engine` without package internal imports.
