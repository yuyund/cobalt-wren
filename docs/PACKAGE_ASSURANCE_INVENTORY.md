# Package Assurance Inventory

This audit is code-first.

Code is the source of truth.
Tests are the source of truth for guarantees.
Docs are supporting material only.

## Evidence Levels

- `CODE_CONFIRMED`: the implementation is present in `src/`
- `TEST_CONFIRMED`: tests assert the behavior
- `ARCH_GUARD_CONFIRMED`: an architecture guard asserts the boundary
- `DOC_ONLY`: only docs claim the behavior
- `ASSUMED`: the code shape suggests the behavior, but it is not directly proven
- `GAP`: the behavior should exist, but code/test evidence is missing
- `OUT_OF_SCOPE`: future work, deferred by design

## Capability Inventory

| Capability | Implementation points | Status | Evidence | Current tests |
| --- | --- | --- | --- | --- |
| Public API surface | `src/langgraph_automation/api/__init__.py`, `api/errors.py`, `api/plugins.py`, `api/workflow.py`, `api/engine.py`, `api/llm.py`, `api/tools.py`, `api/stores.py`, `api/events.py` | Public / provisional / internal mix | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `tests/unit/api/test_public_api_imports.py`, `tests/unit/api/test_public_errors_imports.py`, `tests/unit/api/test_public_plugins_imports.py`, `tests/unit/api/test_public_workflow_imports.py`, `tests/unit/api/test_public_engine_imports.py` |
| `api.engine` facade | `src/langgraph_automation/api/engine.py` | Public-facing provisional | `CODE_CONFIRMED` + `TEST_CONFIRMED` + `ARCH_GUARD_CONFIRMED` | `tests/unit/api/test_engine_create.py`, `tests/unit/api/test_engine_prepare_workflow.py`, `tests/unit/api/test_engine_errors.py`, `tests/integration/api/test_engine_facade_smoke.py`, `tests/integration/api/test_engine_facade_failure_matrix.py`, `tests/integration/api/test_engine_facade_plugins.py`, `tests/unit/architecture/test_engine_facade_boundary.py` |
| Config loading / normalization / validation | `src/langgraph_automation/config/loader.py`, `normalizer.py`, `security.py`, `validator.py`, `models.py` | Internal / provisional | `CODE_CONFIRMED` + `TEST_CONFIRMED` + `ARCH_GUARD_CONFIRMED` | `tests/unit/config/test_config_loader.py`, `tests/unit/config/test_config_normalizer.py`, `tests/unit/config/test_config_security.py`, `tests/unit/config/test_config_validator_*.py`, `tests/unit/architecture/test_config_core_boundary.py`, `tests/unit/architecture/test_config_validator_boundary.py` |
| Plugin registration / contribution resolution | `src/langgraph_automation/api/plugins.py`, `src/langgraph_automation/plugins/registry.py` | Public vocabulary + internal registry | `CODE_CONFIRMED` + `TEST_CONFIRMED` + `ARCH_GUARD_CONFIRMED` | `tests/unit/api/test_plugin_contributions.py`, `tests/unit/api/test_public_plugins_imports.py`, `tests/unit/plugins/test_registry.py`, `tests/unit/plugins/test_registry_workflows.py`, `tests/unit/architecture/test_plugin_public_boundary.py` |
| Runtime assembly | `src/langgraph_automation/runtime/dependencies.py`, `context.py`, `secrets.py`, `assembly.py` | Internal / provisional | `CODE_CONFIRMED` + `TEST_CONFIRMED` + `ARCH_GUARD_CONFIRMED` | `tests/unit/runtime/test_factory_context.py`, `tests/unit/runtime/test_secret_resolver.py`, `tests/unit/runtime/test_runtime_assembler_*.py`, `tests/unit/architecture/test_runtime_assembly_boundary.py` |
| Workflow contribution / preparation | `src/langgraph_automation/api/workflow.py`, `workflows/prepare.py`, `workflows/adapter.py`, `workflows/requirements.py`, `workflows/catalog.py`, `workflows/reference/llm_echo_summary/definition.py` | Public vocabulary + internal preparation path | `CODE_CONFIRMED` + `TEST_CONFIRMED` + `ARCH_GUARD_CONFIRMED` | `tests/unit/workflows/test_workflow_preparer.py`, `tests/unit/workflows/test_builtin_workflow_preparation.py`, `tests/unit/workflows/test_builtin_workflow_catalog.py`, `tests/unit/workflows/reference/test_llm_echo_summary_contribution.py`, `tests/unit/architecture/test_workflow_preparation_boundary.py`, `tests/unit/architecture/test_builtin_workflow_wiring_boundary.py` |
| Service integration via `api.engine` | `src/langgraph_automation/apps/automation/services/workflow_preparation.py` | Transitional bridge now routed through facade | `CODE_CONFIRMED` + `TEST_CONFIRMED` + `ARCH_GUARD_CONFIRMED` | `tests/unit/apps/automation/services/test_workflow_preparation_service.py`, `tests/unit/apps/automation/services/test_workflow_graph_resolution.py`, `tests/unit/apps/automation/services/test_service_integration_via_engine.py`, `tests/unit/architecture/test_apps_automation_package_boundary.py`, `tests/unit/architecture/test_service_workflow_integration_boundary.py` |
| Safety / redaction / safe errors | `src/langgraph_automation/core/result_safety.py`, `core/redaction.py`, `graphs/runner.py`, `apps/automation/services/runs.py` | Runtime-safe persistence path | `CODE_CONFIRMED` + `TEST_CONFIRMED` | `tests/unit/core/test_result_safety.py`, `tests/unit/core/test_core_redaction.py`, `tests/unit/graphs/test_runner.py`, `tests/unit/graphs/test_graph_runner_state_safety.py`, `tests/unit/automation/test_run_safety.py`, `tests/unit/automation/test_run_failure_observability_masking.py`, `tests/integration/api/test_engine_facade_smoke.py`, `tests/integration/api/test_engine_facade_failure_matrix.py` |
| Architecture boundaries | `tests/unit/architecture/*`, `tests/support/import_scan.py` | Test-only enforcement layer | `ARCH_GUARD_CONFIRMED` | `tests/unit/architecture/test_engine_facade_boundary.py`, `tests/unit/architecture/test_apps_automation_package_boundary.py`, `tests/unit/architecture/test_application_workflow_public_api_boundary.py`, `tests/unit/architecture/test_workflow_preparation_boundary.py`, `tests/unit/architecture/test_service_workflow_integration_boundary.py`, `tests/unit/architecture/test_application_readiness_boundary.py` |
| Docs / contract consistency | `docs/API_SURFACE.md`, `docs/ARCHITECTURE.md`, `docs/CONTRACTS.md`, `docs/PACKAGE_COMPLETION.md`, `docs/PACKAGE_FACADE_DESIGN.md`, `docs/PACKAGE_VERIFICATION_STRATEGY.md` | Mixed: some claims confirmed, some doc-only, some drift | `TEST_CONFIRMED` + `DOC_ONLY` | `tests/unit/docs/test_package_completion_docs.py`, `tests/unit/docs/test_package_facade_design_docs.py`, `tests/unit/docs/test_application_readiness_docs.py` |

## Observations

- `run_workflow` is still deferred and not exported.
- `api.runtime` does not exist yet.
- `UnknownWorkflowKindError` is still mentioned in docs, but `api.workflow` does not export it.
- `apps/automation/services/runtime.py` and `workflow_config.py` still import graph foundation modules directly.
