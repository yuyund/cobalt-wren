# Persistence Test Traceability

This traceability matrix links the durability contract to the current code and tests, and marks the missing coverage that must be closed later.

## Traceability Matrix

| Invariant | Failure mode | Implementation point | Current test | Required test layer | Coverage | Gap | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Store protocols remain minimal | API surface drift | `src/langgraph_automation/api/stores.py` | `tests/unit/api/test_public_api_imports.py` | L1 protocol test | `TEST_CONFIRMED` | none | low |
| ArtifactStore protocol is body-aware | protocol sufficiency | `src/langgraph_automation/api/stores.py`, `src/langgraph_automation/integrations/artifact/base.py` | `tests/unit/architecture/test_artifact_store_protocol_sufficiency.py` | L1 protocol sufficiency audit | `APPROVED_FOR_IMPLEMENTATION` | none | medium |
| Artifact backend runtime selection is typed and startup-only | config/runtime composition | `src/langgraph_automation/config/artifact_store.py`, `src/langgraph_automation/runtime/artifact_store.py`, `src/langgraph_automation/apps/automation/services/runtime.py`, `src/langgraph_automation/runtime/assembly.py` | `tests/unit/config/test_artifact_store_settings.py`, `tests/unit/runtime/test_runtime_assembler_stores.py`, `tests/unit/runtime/test_persistence_runtime_wiring.py`, `tests/unit/runtime/test_persistence_configuration_composition.py` | L1 / L3 / L5 | `TEST_CONFIRMED` | trusted package settings select the backend; workflow payload physical persistence config is rejected; filesystem selection is explicit opt-in; normalized package config is bound once at application composition | medium |
| Physical persistence configuration is bound once at application composition | composition ownership | `src/langgraph_automation/apps/automation/services/runtime.py`, `src/langgraph_automation/apps/automation/services/runs.py`, `src/langgraph_automation/apps/automation/services/execution.py` | `tests/unit/runtime/test_persistence_configuration_composition.py`, `tests/unit/architecture/test_persistence_orchestration_boundary.py`, `tests/unit/automation/test_run_safety.py` | L1 / L3 / L5 | `TEST_CONFIRMED` | no per-run package_settings override remains on the run service API | medium |
| Deployment startup config source is trusted and startup-only | application bootstrap | `src/langgraph_automation/config/settings.py`, `src/langgraph_automation/apps/automation/apps.py`, `src/langgraph_automation/apps/automation/services/runtime.py` | `tests/unit/automation/test_persistence_deployment_startup.py` | L1 / L5 | `TEST_CONFIRMED` | `LANGGRAPH_AUTOMATION` is loaded once through `AutomationConfig.ready()`, invalid deployment config fails startup, and Filesystem selection remains explicit opt-in | medium |
| Deployment startup binding is idempotent for same config and fail-closed for different config | application bootstrap | `src/langgraph_automation/apps/automation/apps.py` | `tests/unit/automation/test_persistence_deployment_startup.py` | L1 / L5 | `TEST_CONFIRMED` | same-config `ready()` is a no-op; different-config `ready()` fails closed | medium |
| FilesystemArtifactStore list path is metadata-bounded | list-time metadata validation | `src/langgraph_automation/integrations/artifact/filesystem_store.py` | `tests/contract/persistence/test_filesystem_artifact_store_contract.py`, `tests/unit/docs/test_filesystem_artifact_store_docs.py` | L2 / L7 | `TEST_CONFIRMED` | full body digest verification intentionally excluded from listing | medium |
| CheckpointStore protocol is versioned and approved for implementation | versioned checkpoint contract | `src/langgraph_automation/integrations/checkpoint/base.py`, `src/langgraph_automation/integrations/checkpoint/memory_store.py`, `src/langgraph_automation/integrations/checkpoint/filesystem_store.py` | `tests/unit/architecture/test_checkpoint_store_protocol_sufficiency.py`, `tests/unit/docs/test_checkpoint_store_protocol_sufficiency_docs.py`, `tests/unit/docs/test_checkpoint_store_contract_docs.py` | L1 protocol sufficiency audit | `TEST_CONFIRMED` | checkpoint runtime selection is typed and canonical | high |
| Checkpoint metadata fidelity is lossless and defensively isolated | metadata persistence fidelity | `src/langgraph_automation/integrations/checkpoint/base.py`, `src/langgraph_automation/integrations/checkpoint/memory_store.py`, `src/langgraph_automation/integrations/checkpoint/filesystem_store.py` | `tests/contract/persistence/test_checkpoint_store_baseline_contract.py`, `tests/contract/persistence/test_filesystem_checkpoint_store_contract.py`, `tests/unit/docs/test_checkpoint_store_contract_docs.py` | L2 reusable backend contract suite / L7 safety regression | `TEST_CONFIRMED` | checkpoint runtime selection is typed and canonical | high |
| Checkpoint metadata canonical equivalence is JSON-type aware | immutable request comparison | `src/langgraph_automation/integrations/checkpoint/base.py`, `src/langgraph_automation/integrations/checkpoint/memory_store.py`, `src/langgraph_automation/integrations/checkpoint/filesystem_store.py` | `tests/contract/persistence/test_checkpoint_store_baseline_contract.py`, `tests/contract/persistence/test_filesystem_checkpoint_store_contract.py` | L2 reusable backend contract suite / L6 concurrency-idempotency | `TEST_CONFIRMED` | runtime selection is typed and canonical | high |
| Checkpoint metadata conflict distinction preserves immutable identity | canonical request conflict | `src/langgraph_automation/integrations/checkpoint/memory_store.py`, `src/langgraph_automation/integrations/checkpoint/filesystem_store.py` | `tests/contract/persistence/test_checkpoint_store_baseline_contract.py`, `tests/contract/persistence/test_filesystem_checkpoint_store_contract.py` | L2 reusable backend contract suite / L6 concurrency-idempotency | `TEST_CONFIRMED` | runtime selection is typed and canonical | high |
| Checkpoint diagnostics do not expose payload metadata | repr / fault safety | `src/langgraph_automation/integrations/checkpoint/base.py`, `tests/support/persistence/faults.py` | `tests/contract/persistence/test_checkpoint_store_baseline_contract.py`, `tests/contract/persistence/test_persistence_fault_harness.py` | L7 safety regression / L4 fault-injection | `TEST_CONFIRMED` | safe identifiers remain bounded only | medium |
| Checkpoint idempotency is checked before head validation | AFTER retry safety | `src/langgraph_automation/integrations/checkpoint/memory_store.py`, `src/langgraph_automation/integrations/checkpoint/filesystem_store.py` | `tests/contract/persistence/test_checkpoint_store_baseline_contract.py`, `tests/contract/persistence/test_filesystem_checkpoint_store_contract.py`, `tests/contract/persistence/test_persistence_fault_harness.py` | L2 reusable backend contract suite / L4 fault-injection | `TEST_CONFIRMED` | runtime selection is typed and canonical | high |
| Checkpoint public API boundary is bounded | facade containment | `src/langgraph_automation/api/stores.py`, `src/langgraph_automation/integrations/checkpoint/__init__.py` | `tests/unit/api/test_public_api_imports.py` | L1 public API regression | `TEST_CONFIRMED` | no new checkpoint aliases beyond bounded facades | low |
| Filesystem checkpoint backend is PROCESS_DURABLE and restart durable | durable checkpoint backend | `src/langgraph_automation/integrations/checkpoint/filesystem_store.py`, `src/langgraph_automation/integrations/checkpoint/__init__.py` | `tests/contract/persistence/test_filesystem_checkpoint_store_contract.py`, `tests/contract/persistence/test_persistence_backend_registration.py`, `tests/unit/docs/test_filesystem_checkpoint_store_docs.py` | L2 reusable backend contract suite / L5 restart / L6 concurrency / L7 safety regression | `TEST_CONFIRMED` | checkpoint runtime selection is typed and canonical | high |
| Checkpoint runtime selection is typed and canonical | startup composition | `src/langgraph_automation/config/checkpoint_store.py`, `src/langgraph_automation/runtime/checkpoint_store.py`, `src/langgraph_automation/apps/automation/services/runtime.py`, `src/langgraph_automation/runtime/assembly.py` | `tests/unit/config/test_checkpoint_store_settings.py`, `tests/unit/runtime/test_runtime_assembler_stores.py`, `tests/unit/runtime/test_persistence_runtime_wiring.py`, `tests/unit/runtime/test_persistence_configuration_composition.py`, `tests/unit/automation/test_runtime_factory.py` | L1 / L3 runtime wiring | `TEST_CONFIRMED` | trusted package settings select the backend; workflow payload physical persistence config is rejected; filesystem selection is explicit opt-in; normalized package config is bound once at application composition | medium |
| Execution lifecycle does not yet persist artifacts or checkpoints | orchestration gap | `src/langgraph_automation/apps/automation/services/runs.py`, `src/langgraph_automation/apps/automation/services/execution.py`, `src/langgraph_automation/apps/automation/services/runtime.py`, `src/langgraph_automation/graphs/runner.py` | `tests/unit/architecture/test_persistence_orchestration_boundary.py`, `tests/unit/docs/test_persistence_orchestration_audit_docs.py` | L3 persistence orchestration audit | `TEST_CONFIRMED` | GraphRuntime now receives selected stores, but no execution-path store write exists yet | high |
| LangGraph checkpointer API is richer than current storage protocol | adapter compatibility | `venv/lib/python3.12/site-packages/langgraph/checkpoint/base/__init__.py`, `venv/lib/python3.12/site-packages/langgraph/checkpoint/memory/__init__.py` | `tests/unit/docs/test_persistence_orchestration_audit_docs.py` | L1 installed-source audit | `TEST_CONFIRMED` | pending writes and config mapping still block a full adapter | high |
| Reusable baseline persistence contract suite exists | baseline contract drift | `tests/contract/persistence/test_artifact_store_baseline_contract.py`, `tests/contract/persistence/test_checkpoint_store_baseline_contract.py`, `tests/contract/persistence/test_filesystem_checkpoint_store_contract.py` | new contract harness | L2 reusable backend contract suite | `TEST_CONFIRMED` | none | high |
| Memory stores are EPHEMERAL | restart durability loss | `src/langgraph_automation/integrations/artifact/memory_store.py`, `src/langgraph_automation/integrations/checkpoint/memory_store.py` | `tests/unit/artifact/test_memory_store.py`, `tests/unit/integrations/test_checkpoint_summary.py`, `tests/unit/runtime/test_persistence_runtime_wiring.py` | L2 reusable backend contract suite | `TEST_CONFIRMED` | durable restart coverage absent | high |
| Artifact writes are metadata-safe | S1 / S5 / S6 | `src/langgraph_automation/integrations/artifact/memory_store.py`, `src/langgraph_automation/integrations/observability/django_event_sink.py` | `tests/unit/artifact/test_keys.py`, `tests/integration/django/test_event_sink.py` | L7 safety regression | `TEST_CONFIRMED` | durable body semantics absent | medium |
| Checkpoint summaries are bounded and redacted | S1 / S6 | `src/langgraph_automation/integrations/checkpoint/summary.py`, `src/langgraph_automation/integrations/checkpoint/memory_store.py` | `tests/unit/integrations/test_checkpoint_summary.py` | L7 safety regression | `TEST_CONFIRMED` | body-read verification absent | medium |
| Runtime assembly wires in-memory stores | backend selection | `src/langgraph_automation/apps/automation/services/runtime.py` | `tests/unit/automation/test_runtime_factory.py` | L3 persistence orchestration integration | `TEST_CONFIRMED` | no durable backend selection tests | high |
| Backend registry stays synchronized with concrete implementations | registration drift | `tests/support/persistence/backends.py` | `tests/contract/persistence/test_persistence_backend_registration.py` | L1 / L2 registry guard | `TEST_CONFIRMED` | future backend onboarding still needs the same registry pattern | medium |
| Deterministic fault injection is available for store wrappers | fault timing / suppression | `tests/support/persistence/faults.py` | `tests/contract/persistence/test_persistence_fault_harness.py` | L4 fault-injection tests | `TEST_CONFIRMED` | orchestration faults remain deferred until body/metadata writes exist | medium |
| Graph runtime carries stores but runner does not call them | orchestration gap | `src/langgraph_automation/graphs/runtime.py`, `src/langgraph_automation/graphs/runner.py` | `tests/unit/graphs/test_runner.py`, `tests/unit/graphs/test_graph_runner_state_safety.py` | L3 / L4 | `TEST_CONFIRMED` for state safety only | no body-store call coverage | high |
| Safe run output/error persistence is preserved | S3 / S6 | `src/langgraph_automation/apps/automation/services/runs.py` | `tests/unit/automation/test_run_safety.py` | L7 safety regression | `TEST_CONFIRMED` | body store persistence absent | medium |
| Primary observability failure is preserved | secondary failure masking | `src/langgraph_automation/integrations/observability/failure_policy.py`, `src/langgraph_automation/graphs/runner.py` | `tests/unit/graphs/test_runner.py`, `tests/unit/automation/test_run_failure_observability_masking.py` | L4 fault-injection | `TEST_CONFIRMED` | none | low |
| Admin/UI do not expose raw payloads | safety exposure | `src/langgraph_automation/apps/automation/admin.py`, `src/langgraph_automation/apps/automation/ui/*`, `src/langgraph_automation/apps/web/*` | `tests/unit/apps/automation/test_admin_safety.py`, `tests/unit/apps/automation/test_ui_registry_safety.py`, `tests/unit/apps/web/test_dynamic_ui_safety.py` | L7 safety regression | `TEST_CONFIRMED` | template raw dump guard only, not persistence | low |
| CheckpointMetadata is metadata only | body-vs-metadata separation | `src/langgraph_automation/apps/automation/models/checkpoint.py` | `tests/integration/django/test_event_sink.py` | L3 persistence orchestration integration | `TEST_CONFIRMED` | no body read path yet | high |
| Artifact is metadata only | body-vs-metadata separation | `src/langgraph_automation/apps/automation/models/artifact.py` | `tests/integration/django/test_event_sink.py` | L3 persistence orchestration integration | `TEST_CONFIRMED` | no body read path yet | high |

## Required Reusable Contract Suite

The future reusable backend contract suite should be a single shared test module that can be applied to:

- `MemoryArtifactStore`
- `FutureDurableArtifactStore`
- `MemoryCheckpointStore`
- `FutureDurableCheckpointStore`

Recommended shared assertions:

- protocol shape is stable
- missing-key behavior is explicit
- body writes return normalized results
- same identity / same content is idempotent
- same identity / different content is a conflict
- integrity fields are present
- metadata never contains raw body or credentials

Capability-based assertions:

- `EPHEMERAL` backends skip restart durability checks
- `PROCESS_DURABLE` and `DEPLOYMENT_DURABLE` backends must pass restart durability checks
- `DEPLOYMENT_DURABLE` backends should also pass shared-instance checks

## Required Test Layers

- `L1 Protocol tests`: protocol shape, return types, missing-key contract
- `L2 Reusable backend contract suite`: shared assertions for all store implementations
- `L3 Persistence orchestration integration`: body write + Django metadata commit
- `L4 Fault-injection tests`: deterministic failures on body write, metadata commit, and receipt verification
- `L5 Restart durability tests`: recreate backend/application and re-read stored objects
- `L6 Concurrency / idempotency tests`: retry, duplicate, conflict, and parallel write behavior
- `L7 Safety exposure regression`: raw payload, secret, traceback, and path non-exposure

## Gap Summary

- current tests prove the in-memory stores and summary helpers
- current tests do not prove durable backend restart behavior
- current tests do not prove idempotent conflict semantics
- current tests do not prove checksum / serializer integrity semantics
- current tests do not prove body-store orchestration through the execution path
- current tests now prove the reusable baseline contract harness, backend registry guard, and deterministic fault harness
- current tests now prove the ArtifactStore protocol is body-aware and ready for implementation
- current tests now prove artifact backend runtime selection is typed, startup-only, and explicit
- current tests now prove checkpoint metadata is preserved as a lossless logical JSON value and defensively isolated
- current tests now prove checkpoint idempotency and conflict detection are JSON-type-aware
- current tests now prove the checkpoint protocol is versioned and approved for implementation
- current tests now prove filesystem checkpoint durability is implemented and process-durable
- checkpoint runtime selection is typed and canonical
- current tests now prove normalized package config is bound once at application composition and reused across run / retry execution
- current tests now prove deployment startup config is trusted, startup-only, and fail-safe
- current tests now prove `AutomationConfig.ready()` binds once per composition instance and fail-closes on divergent config
- filesystem selection remains explicit opt-in
- durable default is not enabled
- current tests now prove execution persistence orchestration is still absent from the production execution path, even though selected stores now propagate into `GraphRuntime`
- current tests now prove filesystem listing is metadata-bounded and body full verification remains a get-time responsibility

## Deferred Work

- checkpoint runtime selection is typed and canonical
- body/metadata orchestration is deferred
- deployment startup proof is complete
- run_workflow is deferred
- api.runtime is deferred
- true resume is deferred
- application workflow is deferred
- FilesystemArtifactStore implementation is deferred
