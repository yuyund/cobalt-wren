# Package Invariants

This document records the invariants that are currently supported by code and tests.

## Boundary Invariants

| Invariant | Implementation evidence | Test evidence | Evidence level | Gap / risk |
| --- | --- | --- | --- | --- |
| `api.engine` is the package-facing boundary for application/control-plane code | `src/cobalt_wren/api/engine.py::create_engine`, `AutomationEngine.prepare_workflow`, `EnginePreparedWorkflow` | `tests/unit/api/test_public_engine_imports.py::test_public_engine_api_exports`, `tests/unit/architecture/test_engine_facade_boundary.py::test_api_engine_imports_only_allowed_package_facades_and_internal_layers`, `tests/integration/api/test_engine_facade_smoke.py::test_api_engine_headless_prepare_does_not_execute_provider_or_tool` | `TEST_CONFIRMED` + `ARCH_GUARD_CONFIRMED` | Low risk |
| `api.engine` does not expose `run_workflow` or `api.runtime` | `src/cobalt_wren/api/engine.py`, `src/cobalt_wren/api/__init__.py` | `tests/unit/api/test_public_engine_imports.py::test_public_engine_api_exports`, `tests/unit/architecture/test_engine_facade_boundary.py::test_api_runtime_facade_is_not_created_yet` | `TEST_CONFIRMED` + `ARCH_GUARD_CONFIRMED` | Low risk |
| `apps/automation` limits package-internal imports to the exact execution adapters | `src/cobalt_wren/apps/automation/services/runtime.py`, `execution.py`, `runs.py` | `tests/unit/architecture/test_apps_automation_package_boundary.py::test_apps_automation_package_does_not_import_package_internals_outside_exact_execution_adapters`, `tests/unit/architecture/test_apps_automation_package_boundary.py::test_execution_adapters_have_exact_graph_runtime_allowlist` | `TEST_CONFIRMED` + `ARCH_GUARD_CONFIRMED` | Low risk |
| `workflows/applications` must avoid control-plane imports | `tests/unit/architecture/test_application_workflow_public_api_boundary.py` | Guard exists but the package is currently empty | `ARCH_GUARD_CONFIRMED` | Low risk until files are added |

## Safety Invariants

| Invariant | Implementation evidence | Test evidence | Evidence level | Gap / risk |
| --- | --- | --- | --- | --- |
| Headless workflow preparation does not execute provider network calls | `src/cobalt_wren/api/engine.py::create_engine`, `AutomationEngine.prepare_workflow` | `tests/integration/api/test_engine_facade_smoke.py::test_api_engine_headless_prepare_does_not_execute_provider_or_tool` | `TEST_CONFIRMED` | Low risk |
| Headless workflow preparation does not execute tool calls | `src/cobalt_wren/api/engine.py::create_engine`, `AutomationEngine.prepare_workflow` | `tests/integration/api/test_engine_facade_smoke.py::test_api_engine_headless_prepare_does_not_execute_provider_or_tool` | `TEST_CONFIRMED` | Low risk |
| Safe errors do not leak traceback or secret values | `src/cobalt_wren/api/errors.py`, `src/cobalt_wren/api/engine.py`, `src/cobalt_wren/workflows/adapter.py`, `src/cobalt_wren/runtime/secrets.py` | `tests/unit/api/test_engine_errors.py`, `tests/integration/api/test_engine_facade_failure_matrix.py`, `tests/unit/core/test_result_safety.py`, `tests/unit/graphs/test_runner.py`, `tests/unit/automation/test_run_failure_observability_masking.py` | `TEST_CONFIRMED` | Low risk |
| Primary failure is preserved over secondary observability failure | `src/cobalt_wren/graphs/runner.py`, `src/cobalt_wren/apps/automation/services/runs.py` | `tests/unit/graphs/test_runner.py::test_run_graph_once_preserves_primary_failure_when_span_failed_fails`, `tests/unit/automation/test_run_failure_observability_masking.py::test_start_run_preserves_primary_failure_when_run_failed_observability_fails` | `TEST_CONFIRMED` | Low risk |
| Raw input / raw tool output / raw provider output stay out of safe persistence | `src/cobalt_wren/core/result_safety.py`, `src/cobalt_wren/graphs/runner.py`, `src/cobalt_wren/apps/automation/services/runs.py` | `tests/unit/core/test_result_safety.py`, `tests/unit/graphs/test_graph_runner_state_safety.py`, `tests/unit/automation/test_run_safety.py` | `TEST_CONFIRMED` | Low risk |

## Config Invariants

| Invariant | Implementation evidence | Test evidence | Evidence level | Gap / risk |
| --- | --- | --- | --- | --- |
| Raw package config must be a mapping and version 1 | `src/cobalt_wren/config/loader.py::load_package_config_from_mapping` | `tests/unit/config/test_config_loader.py` | `TEST_CONFIRMED` | Low risk |
| Unsafe config shapes are rejected before normalization | `src/cobalt_wren/config/security.py::precheck_package_config_mapping` | `tests/unit/config/test_config_security.py` | `TEST_CONFIRMED` | Low risk |
| Normalization applies defaults and typed models | `src/cobalt_wren/config/normalizer.py::normalize_package_config` | `tests/unit/config/test_config_normalizer.py` | `TEST_CONFIRMED` | Low risk |
| `ConfigValidator` resolves only enabled plugins | `src/cobalt_wren/config/validator.py::ConfigValidator.validate` | `tests/unit/config/test_config_validator_*.py` | `TEST_CONFIRMED` | Low risk |
| Validation hooks may run, factory hooks must not run during validation | `src/cobalt_wren/config/validator.py::_invoke_validation_hook` | `tests/unit/config/test_config_validator_*.py` | `TEST_CONFIRMED` | Low risk |

## Plugin Invariants

| Invariant | Implementation evidence | Test evidence | Evidence level | Gap / risk |
| --- | --- | --- | --- | --- |
| `PluginContributions` aggregates workflow, tool, provider, store, and event sink contributions | `src/cobalt_wren/api/plugins.py::PluginContributions` | `tests/unit/api/test_plugin_contributions.py`, `tests/unit/api/test_public_plugins_imports.py` | `TEST_CONFIRMED` | Low risk |
| `PluginRegistry` stores definitions and rejects duplicate names / contributions | `src/cobalt_wren/plugins/registry.py::PluginRegistry.register` | `tests/unit/plugins/test_registry.py`, `tests/unit/plugins/test_registry_workflows.py` | `TEST_CONFIRMED` | Low risk |
| `PluginRegistry` does not call validation or factory hooks during registration | `src/cobalt_wren/plugins/registry.py::PluginRegistry.register` | `tests/unit/plugins/test_registry.py`, `tests/unit/plugins/test_registry_workflows.py` | `TEST_CONFIRMED` | Low risk |
| Unknown plugin / tool / provider / store / workflow lookups surface safe resolution errors | `src/cobalt_wren/plugins/registry.py::PluginRegistry.get_*` | `tests/unit/plugins/test_registry.py`, `tests/unit/plugins/test_registry_workflows.py` | `TEST_CONFIRMED` | Low risk |

## Runtime Assembly Invariants

| Invariant | Implementation evidence | Test evidence | Evidence level | Gap / risk |
| --- | --- | --- | --- | --- |
| Runtime assembly consumes `ValidatedPackageConfig` and `SecretResolver` | `src/cobalt_wren/runtime/assembly.py::RuntimeAssembler`, `src/cobalt_wren/runtime/secrets.py::EnvSecretResolver` | `tests/unit/runtime/test_runtime_assembler_*.py`, `tests/unit/runtime/test_secret_resolver.py` | `TEST_CONFIRMED` | Low risk |
| Missing provider/tool/store/event sink factories are safe failures | `src/cobalt_wren/runtime/assembly.py` | `tests/unit/runtime/test_runtime_assembler_*.py` | `TEST_CONFIRMED` | Low risk |
| Arbitrary factory exceptions are wrapped as `RuntimeAssemblyError` | `src/cobalt_wren/runtime/assembly.py` | `tests/unit/runtime/test_runtime_assembler_*.py` | `TEST_CONFIRMED` | Low risk |
| Missing secrets are safe failures with bounded metadata | `src/cobalt_wren/runtime/secrets.py::EnvSecretResolver.resolve` | `tests/unit/api/test_engine_errors.py`, `tests/integration/api/test_engine_facade_failure_matrix.py`, `tests/unit/runtime/test_secret_resolver.py` | `TEST_CONFIRMED` | Low risk |

## Workflow Preparation Invariants

| Invariant | Implementation evidence | Test evidence | Evidence level | Gap / risk |
| --- | --- | --- | --- | --- |
| `WorkflowPreparer` resolves registered workflow kinds | `src/cobalt_wren/workflows/prepare.py::WorkflowPreparer.prepare` | `tests/unit/workflows/test_workflow_preparer.py`, `tests/unit/workflows/test_builtin_workflow_preparation.py` | `TEST_CONFIRMED` | Low risk |
| Workflow requirements are checked before build | `src/cobalt_wren/workflows/prepare.py::WorkflowPreparer.prepare`, `src/cobalt_wren/workflows/requirements.py::check_workflow_requirements` | `tests/unit/workflows/test_workflow_requirements.py`, `tests/unit/workflows/test_workflow_preparer.py`, `tests/integration/api/test_engine_facade_failure_matrix.py` | `TEST_CONFIRMED` | Low risk |
| `WorkflowDefinition.build` is called only through the adapter | `src/cobalt_wren/workflows/adapter.py::build_workflow_graph` | `tests/unit/workflows/test_workflow_adapter.py`, `tests/unit/workflows/test_workflow_preparer.py` | `TEST_CONFIRMED` | Low risk |
| Preparation does not execute graphs | `src/cobalt_wren/workflows/prepare.py`, `src/cobalt_wren/api/engine.py` | `tests/integration/api/test_engine_facade_smoke.py`, `tests/unit/workflows/test_workflow_preparer.py`, `tests/unit/apps/automation/services/test_workflow_graph_resolution.py` | `TEST_CONFIRMED` | Low risk |

## Facade Invariants

| Invariant | Implementation evidence | Test evidence | Evidence level | Gap / risk |
| --- | --- | --- | --- | --- |
| `EnginePreparedWorkflow` is the public-facing handle returned by `api.engine` | `src/cobalt_wren/api/engine.py::EnginePreparedWorkflow`, `AutomationEngine.prepare_workflow` | `tests/unit/api/test_engine_prepare_workflow.py`, `tests/integration/api/test_engine_facade_smoke.py` | `TEST_CONFIRMED` | Low risk |
| `api.engine` hides registry, validator, assembler, dependencies, and preparer internals | `src/cobalt_wren/api/engine.py::AutomationEngine`, `create_engine` | `tests/unit/api/test_engine_create.py`, `tests/unit/api/test_public_engine_imports.py`, `tests/unit/architecture/test_engine_facade_boundary.py` | `TEST_CONFIRMED` + `ARCH_GUARD_CONFIRMED` | Low risk |
| `api.engine` does not export `run_workflow` | `src/cobalt_wren/api/engine.py`, `src/cobalt_wren/api/__init__.py` | `tests/unit/api/test_public_engine_imports.py`, `tests/unit/architecture/test_engine_facade_boundary.py` | `TEST_CONFIRMED` + `ARCH_GUARD_CONFIRMED` | Low risk |

## Service Integration Invariants

| Invariant | Implementation evidence | Test evidence | Evidence level | Gap / risk |
| --- | --- | --- | --- | --- |

## Design Evidence Status

| Design claim | Current evidence | Evidence level | Gap / risk |
| --- | --- | --- | --- |
| Internal loose coupling is the package-wide review standard | `docs/architecture/design/DESIGN_PRINCIPLES.md`, architecture and contract cross-references | `DOCUMENTED` | Replacement tests are still required for several adapters |
| A separately distributed workflow can be built as its own wheel, installed, discovered through an optional entry point, and executed without importing foundation internals or control-plane code | `tests/external_distributions/acme_workflows`, `tests/integration/api/test_external_workflow_distribution.py`, `tests/unit/architecture/test_external_workflow_distribution_boundary.py` | `TEST_CONFIRMED` + `ARCH_GUARD_CONFIRMED` | The test reuses the development environment only for third-party dependencies; both project distributions are independently wheel-built and installed |
| Dynamic UI is a safe projection separate from renderer mechanics | UI specs, registry, builders, and dynamic templates | `IMPLEMENTED_PARTIALLY` | Django adapter, control-plane registration, and renderer independence need a boundary audit and second-renderer evidence |
| Filesystem persistence is PROCESS_DURABLE but true resume is separate | filesystem store implementations and persistence docs/tests | `TEST_CONFIRMED_FOR_STORAGE` | LangGraph saver convergence and real resume remain unimplemented |
| External libraries remain implementation details behind package contracts | current LLM/tool/store/event boundaries | `PARTIALLY_TEST_CONFIRMED` | Structural config validation and tracing adapters still need replacement experiments |

| External workflow persistence and observability capabilities can be replaced without changing workflow code | `tests/integration/api/test_external_workflow_package_extension.py` | `TEST_CONFIRMED` | Artifact and checkpoint replacement are confirmed for memory/filesystem; event sink replacement is confirmed with a non-Django recording sink |
