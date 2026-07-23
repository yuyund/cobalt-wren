---
type: architecture
status: current
authority: normative
summary: Converged control-plane execution through public workflow executables and framework-neutral results.
code_refs:
  - src/langgraph_automation/api/engine.py
  - src/langgraph_automation/api/workflow.py
  - src/langgraph_automation/workflows/prepare.py
  - src/langgraph_automation/runtime/assembly.py
  - src/langgraph_automation/apps/automation/services/execution.py
  - src/langgraph_automation/apps/automation/services/runs.py
  - src/langgraph_automation/apps/automation/services/runtime.py
test_refs:
  - tests/integration/api/test_public_execution_persistence.py
  - tests/unit/automation/test_run_execution_public_workflow.py
  - tests/unit/architecture/test_public_execution_architecture.py
  - tests/unit/architecture/test_execution_convergence_final_boundary.py
verified:
  date: 2026-07-23
  commit: WORKTREE
  base_commit: ed0702a
  method:
    - code-and-test-review
---
# Execution Lifecycle Convergence

## Current State

The Django control plane has one persisted `Run` lifecycle and one execution path. Every Run resolves a `WorkflowReference`, prepares an `EnginePreparedWorkflow`, and calls its public `execute()` method. `runs.py` retains ownership of transitions, safe output persistence, safe error persistence, retry policy, and terminal timestamps.

## Preserved Invariants

- Run execution does not construct `GraphRuntime`.
- The built-in reference workflow uses LangGraph only inside its public executable implementation.
- `Run.output_payload` is always written through `safe_run_output_payload`.
- `Run.error_message` is always written through `safe_run_error_message`.
- Observability failures do not replace primary execution failures.
- The public executable adapter creates only a top-level execution span. Workflow-owned node, LLM, tool, artifact, and checkpoint events remain the workflow/runtime capability's responsibility.
- Resume remains unsupported.

## Remaining Work

1. Migrate the built-in reference workflow from the internal LangGraph execution path to the public executable contract.
2. Remove the internal LangGraph Run adapter after the reference workflow migration is complete.
3. Add async, streaming, cancellation, and resume only after the synchronous lifecycle is fully converged.

## Control-plane Workflow Reference

A Django `Workflow` selects the public executable path with this stable payload shape:

```json
{
  "workflow": {
    "kind": "acme.review",
    "config": {
      "mode": "strict"
    }
  }
}
```

`workflow.kind` is required and non-empty. `workflow.config` is optional and must be a mapping. The `workflow` section is required. Missing or invalid references fail as workflow configuration errors; there is no graph fallback.

## Deployment Engine Ownership

`AutomationConfig` binds one `RunExecutionServices` instance to the normalized deployment config. The services contain a `DeploymentEngineOwner` that retains the raw deployment mapping and constructs one `AutomationEngine` lazily on the first public workflow preparation. Django startup therefore continues to avoid provider, tool, store, secret, and plugin runtime assembly side effects.

The engine owner is process-scoped, thread-safe, and reused across Run start and retry operations. Installed plugin discovery is enabled for the deployment owner; explicit plugins remain available for tests and embedding.

## Execution Selection

A valid `definition_payload.workflow` reference is required. It is prepared with the deployment engine and executed through `public_executable`. Missing, unknown, or malformed references fail closed; there is no graph fallback.

## Framework-neutral Control-plane Result

The public execution adapter converts `WorkflowExecutionResult` into `ControlPlaneExecutionResult`. `runs.py` has no graph-specific result dependency.

## Lifecycle Event Ownership

A prepared workflow declares one owner through `EnginePreparedWorkflow.lifecycle_events_owner`:

- `control_plane` (default): the public execution adapter emits top-level run events and one top-level execution span.
- `workflow`: the control plane emits no public-path lifecycle events or span, preventing duplicate events when the workflow/runtime owns them.

Workflow definitions may request workflow ownership through `WorkflowDefinition.extra["lifecycle_events_owner"] = "workflow"`. Unsupported values normalize to `control_plane`. Safe Run state persistence remains owned by the control plane in both modes.

## Engine Cache Generation And Reload

`DeploymentEngineOwner` identifies an engine generation from:

- the deployment package configuration mapping;
- explicit plugin metadata and provided capabilities;
- the plugin-discovery enabled flag;
- installed plugin entry-point name, target, distribution name, and distribution version.

Workflow-owned config in `definition_payload.workflow.config`, Run input, and Run state are not part of the engine identity because they are applied at preparation or execution time.

The owner starts at generation `0` with no engine. Lazy first construction creates generation `1`. A successful `reconfigure(...)` builds a complete candidate before taking the short swap lock, then atomically replaces the cached engine and increments the generation. Identical identity is a no-op unless `force=True`.

Candidate failure preserves the last-known-good engine, configuration, signature, and generation. Existing readers continue to receive the old engine while a candidate is being built. Reload operations are serialized, while normal reads are not blocked by candidate construction.

Every control-plane-prepared `EnginePreparedWorkflow` records `engine_generation` and the hashed `engine_signature`. It remains a snapshot: a later reload does not mutate or redirect an already prepared executable. Execution-result details record this generation for diagnosis.

### Discovery Scope

A reconfiguration with discovery enabled re-enumerates installed entry-point metadata. A changed distribution or entry-point signature causes a new generation. This does not guarantee Python module hot reload: already imported module code remains subject to normal Python import caching. Updating plugin code in place therefore requires a process restart unless the deployment provides a separate code-loading mechanism.

### Process Scope

The cache and generation are process-local. Calling `reconfigure()` affects only the current Django worker or process. Multi-worker deployments must use a rolling restart or an external coordination mechanism such as a shared generation record and worker notification. A management command launched as a separate process cannot mutate the in-memory cache of existing web workers.
