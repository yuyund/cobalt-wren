# Package Test Traceability

This matrix is code-first.

If a claim is only documented, it is not treated as proven here.

## Coverage Levels

- `NONE`
- `DOC_ONLY`
- `CODE_ONLY`
- `TESTED_UNIT`
- `TESTED_INTEGRATION`
- `TESTED_ARCH_GUARD`
- `TESTED_FAILURE_MATRIX`

## Traceability Matrix

| Requirement / Invariant | Implementation point | Current tests | Coverage level | Gap | Risk |
| --- | --- | --- | --- | --- | --- |
| Public facades are importable | `src/langgraph_automation/api/*` | `tests/unit/api/test_public_api_imports.py`, `tests/unit/api/test_public_errors_imports.py`, `tests/unit/api/test_public_plugins_imports.py`, `tests/unit/api/test_public_workflow_imports.py`, `tests/unit/api/test_public_engine_imports.py` | `TESTED_UNIT` | none | Low |
| `api.runtime` is still deferred | `src/langgraph_automation/api/engine.py`, `src/langgraph_automation/api/__init__.py` | `tests/unit/architecture/test_engine_facade_boundary.py::test_api_runtime_facade_is_not_created_yet` | `TESTED_ARCH_GUARD` | none | Low |
| `create_engine(config_mapping)` builds the engine | `src/langgraph_automation/api/engine.py::create_engine` | `tests/unit/api/test_engine_create.py::test_create_engine_builds_engine_from_mapping_and_hides_internal_state` | `TESTED_UNIT` | none | Low |
| Explicit plugins are registered and used by the engine | `src/langgraph_automation/api/engine.py::create_engine` | `tests/unit/api/test_engine_create.py::test_create_engine_accepts_explicit_plugins`, `tests/integration/api/test_engine_facade_plugins.py::test_explicit_plugins_are_registered_and_auto_enabled_for_validation_and_assembly` | `TESTED_INTEGRATION` | none | Low |
| Duplicate plugin names and contribution conflicts are rejected | `src/langgraph_automation/plugins/registry.py::PluginRegistry.register` | `tests/unit/api/test_engine_create.py::test_create_engine_raises_on_duplicate_plugin_names`, `tests/integration/api/test_engine_facade_plugins.py::test_duplicate_explicit_workflow_kind_raises_plugin_registration_error`, `tests/unit/plugins/test_registry.py`, `tests/unit/plugins/test_registry_workflows.py` | `TESTED_UNIT` | none | Low |
| `engine.prepare_workflow()` returns `EnginePreparedWorkflow` | `src/langgraph_automation/api/engine.py::AutomationEngine.prepare_workflow` | `tests/unit/api/test_engine_prepare_workflow.py`, `tests/integration/api/test_engine_facade_smoke.py` | `TESTED_INTEGRATION` | none | Low |
| Headless reference workflow preparation does not execute provider or tool calls | `src/langgraph_automation/api/engine.py::AutomationEngine.prepare_workflow` | `tests/integration/api/test_engine_facade_smoke.py::test_api_engine_headless_prepare_does_not_execute_provider_or_tool` | `TESTED_INTEGRATION` | none | Low |
| Unknown workflow kinds fail safely | `src/langgraph_automation/workflows/prepare.py::WorkflowPreparer.prepare` | `tests/unit/api/test_engine_prepare_workflow.py::test_prepare_workflow_unknown_kind_raises_resolution_error`, `tests/integration/api/test_engine_facade_failure_matrix.py::test_unknown_workflow_kind_is_safe`, `tests/unit/apps/automation/services/test_workflow_preparation_service.py::test_prepare_run_workflow_rejects_unknown_workflow_kind` | `TESTED_FAILURE_MATRIX` | none | Low |
| Missing workflow requirements fail safely | `src/langgraph_automation/workflows/requirements.py::check_workflow_requirements` | `tests/unit/workflows/test_workflow_requirements.py`, `tests/unit/api/test_engine_prepare_workflow.py::test_prepare_workflow_missing_provider_requirement_raises_runtime_assembly_error`, `tests/integration/api/test_engine_facade_failure_matrix.py::test_missing_provider_requirement_is_safe` | `TESTED_FAILURE_MATRIX` | none | Low |
| Workflow build failures are wrapped safely | `src/langgraph_automation/workflows/adapter.py::build_workflow_graph` | `tests/unit/workflows/test_workflow_adapter.py`, `tests/integration/api/test_engine_facade_failure_matrix.py::test_workflow_build_failures_are_safe` | `TESTED_FAILURE_MATRIX` | none | Low |
| Factory failures are wrapped safely | `src/langgraph_automation/runtime/assembly.py::RuntimeAssembler` | `tests/unit/runtime/test_runtime_assembler_*.py`, `tests/integration/api/test_engine_facade_failure_matrix.py::test_factory_failures_are_safe` | `TESTED_FAILURE_MATRIX` | none | Low |
| Safe error messages do not leak traceback or secret values | `src/langgraph_automation/api/errors.py`, `src/langgraph_automation/core/result_safety.py`, `src/langgraph_automation/runtime/secrets.py` | `tests/unit/api/test_engine_errors.py`, `tests/unit/core/test_result_safety.py`, `tests/unit/graphs/test_runner.py`, `tests/unit/automation/test_run_failure_observability_masking.py` | `TESTED_UNIT` | none | Low |
| `apps/automation/services/workflow_preparation.py` routes through `api.engine` | `src/langgraph_automation/apps/automation/services/workflow_preparation.py::prepare_run_workflow`, `resolve_graph_for_run` | `tests/unit/apps/automation/services/test_workflow_preparation_service.py`, `tests/unit/apps/automation/services/test_service_integration_via_engine.py`, `tests/unit/architecture/test_apps_automation_package_boundary.py` | `TESTED_ARCH_GUARD` | none | Medium |
| `apps/automation` is fully free of package-internal imports | `src/langgraph_automation/apps/automation/*` | No package-wide guard covers `runtime.py`, `workflow_config.py`, `execution.py`, `runs.py` yet | `NONE` | gap exists | P0 |
| Application workflow packages avoid control-plane and package-internal imports | `src/langgraph_automation/workflows/applications/*` | `tests/unit/architecture/test_application_workflow_public_api_boundary.py` | `TESTED_ARCH_GUARD` | package currently empty | Low |
| `UnknownWorkflowKindError` is implemented in `api.workflow` | `docs/API_SURFACE.md` says it is implemented, but `src/langgraph_automation/api/workflow.py` does not export it | none | `DOC_ONLY` / `CONTRACT_DRIFT` | doc drift | Medium |
| Code-first audit uses source, not docs, as authority | audit process itself | `tests/unit/docs/test_package_assurance_audit_docs.py` | `DOC_ONLY` | meta statement only | Low |

## Notes

- `TESTED_UNIT` means the behavior is covered by at least one unit test.
- `TESTED_INTEGRATION` means the behavior is covered by an integration-style test.
- `TESTED_ARCH_GUARD` means a boundary test enforces the dependency rule.
- `TESTED_FAILURE_MATRIX` means failure behavior is explicitly enumerated.
- `DOC_ONLY` and `CONTRACT_DRIFT` are the main audit findings to close next.
