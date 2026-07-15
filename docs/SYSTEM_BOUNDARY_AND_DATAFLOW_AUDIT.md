# System Boundary And Dataflow Audit

This document records the code-first assurance matrix for the full system.

Code is the source of truth.
Tests are the source of truth.
Docs are intent only.
The supplemental report is hypothesis only.

Evidence levels used below:

- `CODE_CONFIRMED`: implementation file proves the behavior
- `TEST_CONFIRMED`: tests exercise the behavior
- `ARCH_GUARD_CONFIRMED`: import guard enforces the boundary
- `DOC_ONLY`: docs claim it, but code/test do not prove it here
- `ASSUMED`: inferred from code shape, but not directly proven
- `GAP`: expected guarantee is missing or incomplete
- `CONTRACT_DRIFT`: docs and code disagree
- `OUT_OF_SCOPE`: future work outside the current assurance target

## Layer / Dependency Matrix

| Layer | Expected dependency policy | Implementation evidence | Test evidence | Evidence level | Gap / risk |
| --- | --- | --- | --- | --- | --- |
| `api` | Public facades only; no `apps/automation`, Django, concrete workflow, or graph runner imports from `api.engine` | `src/langgraph_automation/api/engine.py`, `api/errors.py`, `api/plugins.py`, `api/workflow.py` | `tests/unit/api/test_public_engine_imports.py`, `tests/unit/architecture/test_engine_facade_boundary.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` + `ARCH_GUARD_CONFIRMED` | `LOW`: public surface now canonicalizes unknown workflow kinds through `PluginResolutionError`; `api.runtime` remains deferred |
| `config` | Load/normalize/validate declarative config only; no runtime execution or graph deps | `src/langgraph_automation/config/loader.py`, `normalizer.py`, `security.py`, `validator.py`, `models.py` | `tests/unit/config/*`, `tests/unit/architecture/test_config_core_boundary.py`, `test_config_validator_boundary.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` + `ARCH_GUARD_CONFIRMED` | `GAP`: config validation is strong, but system-level control-plane still bypasses the package facade in runtime services |
| `plugins` | Manual registry only; no runtime assembly or graph execution | `src/langgraph_automation/plugins/registry.py`, `api/plugins.py` | `tests/unit/plugins/*`, `tests/unit/architecture/test_plugin_public_boundary.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` + `ARCH_GUARD_CONFIRMED` | `GAP`: plugin vocabulary is public, but application/control-plane paths still import internal layers directly elsewhere |
| `runtime` | Assemble dependencies from validated config; no workflow execution | `src/langgraph_automation/runtime/assembly.py`, `dependencies.py`, `secrets.py`, `context.py` | `tests/unit/runtime/*`, `tests/unit/architecture/test_runtime_assembly_boundary.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` + `ARCH_GUARD_CONFIRMED` | `ASSUMED`: runtime assembly remains an internal boundary; control-plane execution adapters are still distinct from the package facade |
| `workflows` | Declare contributions and prepare workflows; do not execute them | `src/langgraph_automation/workflows/prepare.py`, `requirements.py`, `adapter.py`, `catalog.py`, `reference/llm_echo_summary/*` | `tests/unit/workflows/*`, `tests/unit/architecture/test_workflow_preparation_boundary.py`, `test_builtin_workflow_wiring_boundary.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` + `ARCH_GUARD_CONFIRMED` | `GAP`: workflow preparation is verified, but the system still has direct graph-path usage in control-plane services |
| `graphs` | Internal execution foundation only; no workflow catalog or Django ORM imports | `src/langgraph_automation/graphs/*` | `tests/unit/graphs/*`, `tests/unit/architecture/test_no_django_orm_import_in_graphs.py`, `test_workflow_registry_boundary.py`, `test_no_status_update_in_graph_runner.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` + `ARCH_GUARD_CONFIRMED` | `ASSUMED`: graph foundation is stable, but the public surface intentionally remains absent |
| `core` | Safe summaries, redaction, and bounded errors | `src/langgraph_automation/core/*` | `tests/unit/core/*`, `tests/unit/automation/test_run_safety.py`, `tests/unit/automation/test_run_failure_observability_masking.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `GAP`: core safety is strong, but UI/admin exposure still needs system-wide scrutiny |
| `integrations` | External I/O adapters with bounded metadata and failure masking | `src/langgraph_automation/integrations/*` | `tests/unit/integrations/*`, `tests/integration/django/test_event_sink.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `P1`: no durable artifact/checkpoint backend yet; only in-memory stores are present |
| `apps/automation` | Control-plane should route workflow preparation through `api.engine`; direct graph/runtime imports remain only in exact execution adapters | `src/langgraph_automation/apps/automation/services/runtime.py`, `execution.py`, `runs.py`, `workflow_preparation.py` | `tests/unit/apps/automation/services/*`, `tests/unit/architecture/test_apps_automation_package_boundary.py`, `test_service_workflow_integration_boundary.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` + `ARCH_GUARD_CONFIRMED` | `LOW`: `workflow_preparation.py` routes through `api.engine`; `runtime.py`, `execution.py`, and `runs.py` remain the exact execution-adapter boundary |
| `apps/web` | UI should render via builders and redaction, not model internals | `src/langgraph_automation/apps/web/views/*`, `apps/web/templates/*` | `tests/integration/django/test_web_ui.py`, `tests/unit/architecture/test_no_direct_service_map_in_web_views.py`, `test_no_model_meta_in_templates.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` + `ARCH_GUARD_CONFIRMED` | `P2`: template TODO placeholders remain |

## Dataflow Matrix

| Claim / invariant | Implementation evidence | Test evidence | Evidence level | Gap / risk |
| --- | --- | --- | --- | --- |
| Raw package config is loaded, normalized, validated, and assembled into runtime dependencies | `config/loader.py`, `config/normalizer.py`, `config/validator.py`, `runtime/assembly.py`, `api/engine.py` | `tests/unit/config/*`, `tests/unit/runtime/test_runtime_assembler_boundaries.py`, `tests/unit/api/test_engine_create.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `ASSUMED`: control-plane still uses direct runtime assembly in non-facade services |
| `Workflow.definition_payload` is parsed into graph-local runtime config and then into `GraphRuntime` | `apps/automation/services/runtime.py`, `apps/automation/services/workflow_config.py`, `graphs/config.py`, `graphs/runtime.py` | `tests/unit/automation/test_runtime_factory.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `LOW`: this remains the current execution adapter path and is intentionally separate from `api.engine` preparation |
| Raw `Run.input_payload` is transformed into `GraphExecutionInput` and then summarized into graph state | `graphs/inputs.py`, `graphs/runner.py`, `graphs/runtime.py`, `core/summary.py` | `tests/unit/graphs/test_graph_runner_state_safety.py`, `tests/unit/graphs/test_runner.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `ASSUMED`: graph input remains transient and safe, but the service layer still owns direct runner calls |
| Graph execution result is normalized into safe persisted output/error by the service layer | `graphs/runner.py`, `core/result_safety.py`, `apps/automation/services/runs.py` | `tests/unit/automation/test_run_safety.py`, `tests/unit/automation/test_run_failure_observability_masking.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `GAP`: runner result error strings are internal raw strings; safe persistence depends on service-layer normalization |
| `api.engine` produces a public provisional `EnginePreparedWorkflow` without exposing package internals | `api/engine.py`, `apps/automation/services/workflow_preparation.py` | `tests/unit/api/test_engine_prepare_workflow.py`, `tests/unit/apps/automation/services/test_service_integration_via_engine.py`, `tests/integration/api/test_engine_facade_smoke.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `ASSUMED`: graph object remains opaque by contract rather than by structural restriction |
| Observability events and spans are emitted with bounded metadata and failure suppression | `integrations/observability/django_event_sink.py`, `integrations/observability/failure_policy.py`, `integrations/llm/observed_client.py`, `integrations/tools/observed_registry.py` | `tests/integration/django/test_event_sink.py`, `tests/unit/integrations/test_observed_llm_client.py`, `tests/unit/integrations/test_tool_registry.py`, `tests/unit/automation/test_run_failure_observability_masking.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `P1`: observability is strong, but it is still coupled to Django-backed persistence in the control plane |

## Lifecycle Matrix

| Claim / invariant | Implementation evidence | Test evidence | Evidence level | Gap / risk |
| --- | --- | --- | --- | --- |
| Run lifecycle supports pending, running, succeeded, failed, and cancelled | `apps/automation/models/run.py`, `apps/automation/services/runs.py`, `apps/automation/policies/runs.py` | `tests/unit/automation/test_run_policies.py`, `tests/unit/automation/test_run_safety.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `ASSUMED`: lifecycle transitions are enforced by service/policy paths rather than model constraints |
| Retry is supported; resume is explicitly unsupported | `apps/automation/services/runs.py`, `apps/automation/policies/runs.py`, `graphs/runner.py` | `tests/unit/automation/test_run_safety.py`, `tests/unit/graphs/test_runner.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `OUT_OF_SCOPE`: true resume is deferred |
| Execution spans transition through pending/running/succeeded/failed/cancelled/skipped | `apps/automation/models/execution.py`, `integrations/observability/django_event_sink.py` | `tests/integration/django/test_event_sink.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `ASSUMED`: span lifecycles are observability-driven and not independently state-machine tested |

## Safety Matrix

| Safety object | Where it is handled | Evidence | Evidence level | Gap / risk |
| --- | --- | --- | --- | --- |
| Raw input payload | Stored raw in `Run.input_payload`, summarized into graph state via `GraphExecutionInput` and `summarize_mapping` | `apps/automation/models/run.py`, `graphs/inputs.py`, `graphs/runner.py`, `core/summary.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `ASSUMED`: raw input persistence is intentional, but caller paths must avoid leaking it into summaries |
| Raw LLM response | Kept in provider result objects; not persisted to run output, span output, or event payloads | `integrations/llm/base.py`, `integrations/llm/observed_client.py`, `core/result_safety.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `GAP`: no durable external provider contract exists yet |
| Raw ToolResult.output | Summarized/redacted before persistence and observability | `integrations/tools/base.py`, `integrations/tools/observed_registry.py`, `integrations/tools/safe_tools.py`, `core/result_safety.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `ASSUMED`: safe tool wrappers remain the default path, but registry-level direct use can still expose raw tool results internally |
| Secret values and secret-like metadata | Redaction and config prechecks prevent unsafe literals and bounded metadata | `config/security.py`, `runtime/secrets.py`, `core/redaction.py`, `integrations/observability/django_event_sink.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `P1`: admin detail views still need explicit redaction coverage |
| Raw traceback | Converted to safe messages before persistence; observability failures are suppressed | `core/result_safety.py`, `integrations/observability/failure_policy.py`, `apps/automation/services/runs.py`, `graphs/runner.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `ASSUMED`: internal `ExecutionResult.error_message` can still contain raw text until service-layer normalization |
| Absolute local path | Redaction and summary helpers bound visible path content | `core/redaction.py`, `core/result_safety.py`, `integrations/observability/django_event_sink.py`, `apps/automation/ui/redaction.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `P2`: template TODO placeholders can obscure UI guarantees even when logic is safe |
| Checkpoint body / artifact body | DB stores metadata only; bodies live in store backends | `apps/automation/models/checkpoint.py`, `apps/automation/models/artifact.py`, `integrations/checkpoint/base.py`, `integrations/artifact/base.py`, `integrations/checkpoint/memory_store.py`, `integrations/artifact/memory_store.py` | `CODE_CONFIRMED` | `P1`: only in-memory stores exist today; durable stores are deferred |

## Error Matrix

| Error type | Where it originates | Safe surface | Evidence level | Gap / risk |
| --- | --- | --- | --- | --- |
| Config error | `config/loader.py`, `normalizer.py`, `security.py` | `ConfigError` with safe message and metadata | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `LOW`: public docs now treat unknown workflow kinds as `PluginResolutionError` |
| Plugin error | `plugins/registry.py`, `config/validator.py` | `PluginRegistrationError`, `PluginResolutionError`, `PluginValidationError` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `ASSUMED`: validation vs registration responsibilities are stable, but external plugin discovery is still out of scope |
| Runtime assembly error | `runtime/assembly.py`, `runtime/secrets.py`, `api/engine.py` | `RuntimeAssemblyError` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `ASSUMED`: runtime assembly remains internal; exact control-plane execution adapters intentionally still call it directly |
| Workflow preparation error | `workflows/prepare.py`, `workflows/requirements.py`, `workflows/adapter.py`, `api/engine.py` | `PluginResolutionError` or `RuntimeAssemblyError` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `LOW`: workflow preparation now routes through the package facade and no longer bypasses it in the service bridge |
| Graph execution error | `graphs/runner.py` | `ExecutionResult` plus service-layer safe persistence | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `ASSUMED`: runner internals are safe only when consumed through services |
| LLM / tool / observability error | `integrations/llm/observed_client.py`, `integrations/tools/observed_registry.py`, `integrations/observability/failure_policy.py` | safe event payloads and suppressed secondary failures | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `P1`: internal raw exceptions can still exist before redaction/suppression is applied |
| Unsupported resume | `apps/automation/services/runs.py`, `graphs/runner.py` | `NotImplementedError` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `OUT_OF_SCOPE`: true resume remains deferred |
| Invalid lifecycle transition | `apps/automation/policies/runs.py` and service-layer checks | `PermissionError` or policy denial | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `ASSUMED`: transition policy is centralized, but not fully enforced at the model layer |

## Persistence Matrix

| Persisted object | What is stored | What must not be stored | Evidence | Evidence level | Gap / risk |
| --- | --- | --- | --- | --- | --- |
| `Workflow` | definition payload, name, timestamps | secret values, raw provider payloads | `apps/automation/models/workflow.py` | `CODE_CONFIRMED` | `ASSUMED`: workflow payload is trusted input, not a runtime secret store |
| `Run` | lifecycle state, raw input payload, safe output payload, safe error message, timestamps | raw provider response, raw tool output, traceback | `apps/automation/models/run.py`, `core/result_safety.py`, `apps/automation/services/runs.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `P0`: raw input is intentionally stored; downstream code must preserve safety boundary |
| `ExecutionSpan` | summaries, metrics, metadata, timing | raw prompt, raw response, raw tool output | `apps/automation/models/execution.py`, `integrations/observability/django_event_sink.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `P1`: span metadata is bounded, but it is still a rich surface area |
| `RunEvent` | redacted payload and safe message | secrets, raw traceback, raw payload bodies | `apps/automation/models/event.py`, `integrations/observability/django_event_sink.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `ASSUMED`: event payloads are safe because the sink redacts before persistence |
| `Artifact` / `CheckpointMetadata` | metadata and location/indexing fields | artifact body, checkpoint body, raw secret data | `apps/automation/models/artifact.py`, `apps/automation/models/checkpoint.py` | `CODE_CONFIRMED` | `P1`: only in-memory body stores exist now; durable stores are deferred |

## UI Exposure Matrix

| Claim / invariant | Implementation evidence | Test evidence | Evidence level | Gap / risk |
| --- | --- | --- | --- | --- |
| Dynamic pages render from registry-driven specs | `apps/automation/ui/registry.py`, `apps/automation/ui/builders.py`, `apps/web/views/dynamic_pages.py` | `tests/integration/django/test_web_ui.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `ASSUMED`: registry-driven rendering is correct, but only selected views are exercised |
| Dynamic action visibility follows policy | `apps/automation/ui/actions.py`, `apps/automation/ui/registry.py`, `apps/automation/policies/runs.py` | `tests/integration/django/test_web_ui.py`, `tests/unit/automation/test_run_policies.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `ASSUMED`: start/cancel/retry are covered; resume remains absent |
| UI builders redact displayed values | `apps/automation/ui/redaction.py`, `apps/automation/ui/builders.py` | `tests/unit/ui/test_redaction.py`, `tests/integration/django/test_web_ui.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `P1`: Django admin uses default `ModelAdmin` registration and has no explicit redaction guard |
| Admin registration exposes control-plane models | `apps/automation/admin.py` | no dedicated redaction coverage | `CODE_CONFIRMED` | `P1`: privileged admin screens may show raw model fields unless separately constrained |
| Resume is not exposed in UI | `apps/automation/policies/runs.py`, `apps/web/views/dynamic_actions.py`, `tests/unit/architecture/test_no_direct_service_map_in_web_views.py` | `tests/unit/automation/test_run_policies.py`, `tests/unit/architecture/test_no_direct_service_map_in_web_views.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` + `ARCH_GUARD_CONFIRMED` | `OUT_OF_SCOPE`: resume stays deferred |
| Template fragments are still partial | `apps/web/templates/dynamic/*` | none beyond presence checks | `CODE_CONFIRMED` | `P2`: TODO placeholders remain in some template partials |

## Observability Matrix

| Claim / invariant | Implementation evidence | Test evidence | Evidence level | Gap / risk |
| --- | --- | --- | --- | --- |
| Run, span, node, LLM, tool, artifact, and checkpoint events are persisted through the Django sink | `integrations/observability/django_event_sink.py` | `tests/integration/django/test_event_sink.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `ASSUMED`: sink is bounded and redacted, but still Django-backed |
| Secondary observability failures do not overwrite the primary failure | `integrations/observability/failure_policy.py`, `graphs/runner.py`, `integrations/llm/observed_client.py`, `integrations/tools/observed_registry.py`, `apps/automation/services/runs.py` | `tests/unit/automation/test_run_failure_observability_masking.py`, `tests/unit/integrations/test_observed_llm_client.py`, `tests/unit/graphs/test_runner.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `LOW`: control-plane observability remains part of the exact execution-adapter boundary |
| Observability metadata is redacted and bounded | `integrations/observability/django_event_sink.py` | `tests/integration/django/test_event_sink.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `P1`: no separate backend assurance exists for non-Django sinks yet |

## Extension Matrix

| Claim / invariant | Implementation evidence | Test evidence | Evidence level | Gap / risk |
| --- | --- | --- | --- | --- |
| Plugins are metadata plus contributions | `api/plugins.py` | `tests/unit/api/test_plugin_contributions.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `ASSUMED`: public vocabulary is stable, but the extension matrix should be revisited when application workflows are added |
| Workflow contributions are declarative | `api/workflow.py`, `workflows/prepare.py`, `workflows/catalog.py` | `tests/unit/workflows/*`, `tests/unit/api/test_engine_prepare_workflow.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `ASSUMED`: workflow build remains internal-only for now |
| Explicit plugins are auto-enabled for validation and assembly in `api.engine` | `api/engine.py` | `tests/integration/api/test_engine_facade_plugins.py`, `tests/unit/api/test_engine_create.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `P1`: this behavior is well tested for current use cases but should be revisited if enabled-vs-registered semantics split later |
| Built-in reference workflow uses the same plugin path as external workflows | `workflows/catalog.py`, `workflows/reference/llm_echo_summary/definition.py`, `api/engine.py` | `tests/unit/workflows/test_builtin_workflow_catalog.py`, `tests/unit/workflows/reference/test_llm_echo_summary_contribution.py`, `tests/integration/api/test_engine_facade_smoke.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `ASSUMED`: current reference workflow is still the only built-in workflow example |
| Application workflows are not implemented yet | `workflows/applications/__init__.py`, architecture guards | `tests/unit/architecture/test_application_workflow_public_api_boundary.py`, `tests/unit/architecture/test_application_readiness_boundary.py` | `CODE_CONFIRMED` + `TEST_CONFIRMED` + `ARCH_GUARD_CONFIRMED` | `OUT_OF_SCOPE`: future work |
