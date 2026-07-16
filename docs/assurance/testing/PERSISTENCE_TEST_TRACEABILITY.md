# Persistence Test Traceability

This traceability matrix links the durability contract to the current code and tests, and marks the missing coverage that must be closed later.

## Traceability Matrix

| Invariant | Failure mode | Implementation point | Current test | Required test layer | Coverage | Gap | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Store protocols remain minimal | API surface drift | `src/langgraph_automation/api/stores.py` | `tests/unit/api/test_public_api_imports.py` | L1 protocol test | `TEST_CONFIRMED` | none | low |
| Memory stores are EPHEMERAL | restart durability loss | `src/langgraph_automation/integrations/artifact/memory_store.py`, `src/langgraph_automation/integrations/checkpoint/memory_store.py` | `tests/unit/artifact/test_memory_store.py`, `tests/unit/integrations/test_checkpoint_summary.py` | L2 reusable backend contract suite | `TEST_CONFIRMED` | durable restart coverage absent | high |
| Artifact writes are metadata-safe | S1 / S5 / S6 | `src/langgraph_automation/integrations/artifact/memory_store.py`, `src/langgraph_automation/integrations/observability/django_event_sink.py` | `tests/unit/artifact/test_keys.py`, `tests/integration/django/test_event_sink.py` | L7 safety regression | `TEST_CONFIRMED` | durable body semantics absent | medium |
| Checkpoint summaries are bounded and redacted | S1 / S6 | `src/langgraph_automation/integrations/checkpoint/summary.py`, `src/langgraph_automation/integrations/checkpoint/memory_store.py` | `tests/unit/integrations/test_checkpoint_summary.py` | L7 safety regression | `TEST_CONFIRMED` | body-read verification absent | medium |
| Runtime assembly wires in-memory stores | backend selection | `src/langgraph_automation/apps/automation/services/runtime.py` | `tests/unit/automation/test_runtime_factory.py` | L3 persistence orchestration integration | `TEST_CONFIRMED` | no durable backend selection tests | high |
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

## Deferred Work

- durable artifact/checkpoint backend is deferred
- run_workflow is deferred
- api.runtime is deferred
- true resume is deferred
- application workflow is deferred
