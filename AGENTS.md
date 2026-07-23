# Project Map

This file is a compact table of contents for the repository.
Use it to find where code, docs, tests, and local-only artifacts live.

## Root
- `AGENTS.md`: this navigation index for the repository.
- `README.md`: high-level project overview, architecture summary, and getting-started notes.
- `manage.py`: Django management entrypoint for local commands.
- `pyproject.toml`: build metadata, dependencies, and pytest configuration.
- `.gitignore`: excludes local-only files, caches, and generated output.
- `.env`: local environment variables and secrets for development.
- `db.sqlite3`: local SQLite database snapshot for development work.

## Source Package
- `src/langgraph_automation/`: the installable Python package.
- `src/langgraph_automation/__init__.py`: top-level package marker.
- `src/langgraph_automation.egg-info/`: generated packaging metadata from editable installs or builds.
- Package markers: `src/langgraph_automation/api/__init__.py`, `src/langgraph_automation/apps/__init__.py`, `src/langgraph_automation/apps/automation/__init__.py`, `src/langgraph_automation/apps/automation/migrations/__init__.py`, `src/langgraph_automation/apps/automation/models/__init__.py`, `src/langgraph_automation/apps/automation/policies/__init__.py`, `src/langgraph_automation/apps/automation/selectors/__init__.py`, `src/langgraph_automation/apps/automation/services/__init__.py`, `src/langgraph_automation/apps/automation/ui/__init__.py`, `src/langgraph_automation/apps/web/__init__.py`, `src/langgraph_automation/apps/web/templatetags/__init__.py`, `src/langgraph_automation/apps/web/views/__init__.py`, `src/langgraph_automation/config/__init__.py`, `src/langgraph_automation/core/__init__.py`, `src/langgraph_automation/entrypoints/__init__.py`, `src/langgraph_automation/graphs/__init__.py`, `src/langgraph_automation/graphs/nodes/__init__.py`, `src/langgraph_automation/integrations/__init__.py`, `src/langgraph_automation/integrations/artifact/__init__.py`, `src/langgraph_automation/integrations/checkpoint/__init__.py`, `src/langgraph_automation/integrations/llm/__init__.py`, `src/langgraph_automation/integrations/observability/__init__.py`, `src/langgraph_automation/integrations/tools/__init__.py`, `src/langgraph_automation/plugins/__init__.py`, `src/langgraph_automation/runtime/__init__.py`, `src/langgraph_automation/workflows/__init__.py`, `src/langgraph_automation/workflows/applications/__init__.py`, `src/langgraph_automation/workflows/reference/__init__.py`, and `src/langgraph_automation/workflows/reference/llm_echo_summary/__init__.py`.

## Public Facade
- `src/langgraph_automation/api/__init__.py`: public API package marker.
- `src/langgraph_automation/api/engine.py`: package facade for engine creation and workflow preparation.
- `src/langgraph_automation/api/errors.py`: public error types and error mapping surface.
- `src/langgraph_automation/api/events.py`: public event-facing helpers and types.
- `src/langgraph_automation/api/llm.py`: public LLM-facing facade.
- `src/langgraph_automation/api/plugins.py`: public plugin-facing facade.
- `src/langgraph_automation/api/stores.py`: public artifact and checkpoint store facade.
- `src/langgraph_automation/api/tools.py`: public tool-facing facade.
- `src/langgraph_automation/api/workflow.py`: public workflow-facing facade.

## Django Apps
- `src/langgraph_automation/apps/`: Django application namespace.
- `src/langgraph_automation/apps/__init__.py`: app namespace marker.

### Automation App
- `src/langgraph_automation/apps/automation/`: control-plane app for workflows, runs, spans, events, artifacts, and checkpoints.
- `src/langgraph_automation/apps/automation/apps.py`: Django app configuration.
- `src/langgraph_automation/apps/automation/admin.py`: Django admin registrations and safe display helpers.
- `src/langgraph_automation/apps/automation/migrations/`: database migrations.
- `src/langgraph_automation/apps/automation/migrations/0001_initial.py`: initial schema migration.
- `src/langgraph_automation/apps/automation/models/`: Django model definitions.
- `src/langgraph_automation/apps/automation/models/workflow.py`: workflow definition model.
- `src/langgraph_automation/apps/automation/models/run.py`: run lifecycle model.
- `src/langgraph_automation/apps/automation/models/execution.py`: execution span model.
- `src/langgraph_automation/apps/automation/models/event.py`: run event model.
- `src/langgraph_automation/apps/automation/models/artifact.py`: artifact model.
- `src/langgraph_automation/apps/automation/models/checkpoint.py`: checkpoint metadata model.
- `src/langgraph_automation/apps/automation/policies/`: application policies for runs and related control-plane rules.
- `src/langgraph_automation/apps/automation/policies/runs.py`: run policy logic.
- `src/langgraph_automation/apps/automation/selectors/`: query helpers for app data.
- `src/langgraph_automation/apps/automation/selectors/workflows.py`: workflow selectors.
- `src/langgraph_automation/apps/automation/selectors/runs.py`: run selectors.
- `src/langgraph_automation/apps/automation/selectors/events.py`: event selectors.
- `src/langgraph_automation/apps/automation/selectors/spans.py`: span selectors.
- `src/langgraph_automation/apps/automation/selectors/artifacts.py`: artifact selectors.
- `src/langgraph_automation/apps/automation/selectors/checkpoints.py`: checkpoint selectors.
- `src/langgraph_automation/apps/automation/services/`: service layer for workflow preparation, runtime assembly, execution, and configuration.
- `src/langgraph_automation/apps/automation/services/workflows.py`: workflow service helpers.
- `src/langgraph_automation/apps/automation/services/workflow_preparation.py`: workflow preparation service.
- `src/langgraph_automation/apps/automation/services/runtime.py`: runtime assembly bridge.
- `src/langgraph_automation/apps/automation/services/execution.py`: execution orchestration helpers.
- `src/langgraph_automation/apps/automation/services/runs.py`: run lifecycle orchestration.
- `src/langgraph_automation/apps/automation/services/errors.py`: service-layer errors.
- `src/langgraph_automation/apps/automation/ui/`: presentation-only dynamic UI builders and safety helpers.
- `src/langgraph_automation/apps/automation/ui/builders.py`: page-spec builders for lists, details, forms, and fragments.
- `src/langgraph_automation/apps/automation/ui/registry.py`: UI model registry.
- `src/langgraph_automation/apps/automation/ui/specs.py`: typed page-spec and field-spec structures.
- `src/langgraph_automation/apps/automation/ui/formatters.py`: display formatting helpers.
- `src/langgraph_automation/apps/automation/ui/redaction.py`: UI redaction helpers.
- `src/langgraph_automation/apps/automation/ui/actions.py`: declarative UI actions.

### Web App
- `src/langgraph_automation/apps/web/`: Django web presentation app for dynamic pages and fragments.
- `src/langgraph_automation/apps/web/apps.py`: Django app configuration.
- `src/langgraph_automation/apps/web/urls.py`: URL routing for dynamic pages and fragments.
- `src/langgraph_automation/apps/web/views/`: view functions for dynamic pages, actions, and fragments.
- `src/langgraph_automation/apps/web/views/dynamic_pages.py`: dynamic list/detail/form views.
- `src/langgraph_automation/apps/web/views/dynamic_actions.py`: action handlers for dynamic pages.
- `src/langgraph_automation/apps/web/views/fragments.py`: fragment rendering views.
- `src/langgraph_automation/apps/web/templatetags/`: template tags for UI rendering.
- `src/langgraph_automation/apps/web/templatetags/ui_render.py`: helper tags and filters for dynamic UI templates.
- `src/langgraph_automation/apps/web/templates/base.html`: shared HTML base template.
- `src/langgraph_automation/apps/web/templates/dynamic/`: dynamic list/detail/form/fragment templates, partials, and field renderers.
- `src/langgraph_automation/apps/web/templates/dynamic/list.html`: list page template.
- `src/langgraph_automation/apps/web/templates/dynamic/detail.html`: detail page template.
- `src/langgraph_automation/apps/web/templates/dynamic/form.html`: form page template.
- `src/langgraph_automation/apps/web/templates/dynamic/fragment.html`: fragment page template.
- `src/langgraph_automation/apps/web/templates/dynamic/partials/`: reusable table, action, and status partials.
- `src/langgraph_automation/apps/web/templates/dynamic/partials/table.html`: table partial.
- `src/langgraph_automation/apps/web/templates/dynamic/partials/actions.html`: action partial.
- `src/langgraph_automation/apps/web/templates/dynamic/partials/status.html`: status partial.
- `src/langgraph_automation/apps/web/templates/dynamic/fields/`: field renderers for different display types.
- `src/langgraph_automation/apps/web/templates/dynamic/fields/text.html`: plain text field renderer.
- `src/langgraph_automation/apps/web/templates/dynamic/fields/multiline.html`: multiline field renderer.
- `src/langgraph_automation/apps/web/templates/dynamic/fields/link.html`: link field renderer.
- `src/langgraph_automation/apps/web/templates/dynamic/fields/status_badge.html`: status badge renderer.
- `src/langgraph_automation/apps/web/templates/dynamic/fields/json.html`: JSON field renderer.

## Configuration
- `src/langgraph_automation/config/`: Django settings, config loading, validation, and bootstrapping.
- `src/langgraph_automation/config/__init__.py`: config package marker.
- `src/langgraph_automation/config/settings.py`: Django settings module.
- `src/langgraph_automation/config/urls.py`: project URL routing.
- `src/langgraph_automation/config/asgi.py`: ASGI entrypoint.
- `src/langgraph_automation/config/wsgi.py`: WSGI entrypoint.
- `src/langgraph_automation/config/loader.py`: config loading helpers.
- `src/langgraph_automation/config/normalizer.py`: config normalization logic.
- `src/langgraph_automation/config/models.py`: config data models.
- `src/langgraph_automation/config/security.py`: config security helpers.
- `src/langgraph_automation/config/validator.py`: config validation rules.

## Core
- `src/langgraph_automation/core/`: shared low-level helpers used across the codebase.
- `src/langgraph_automation/core/__init__.py`: core package marker.
- `src/langgraph_automation/core/errors.py`: core error types.
- `src/langgraph_automation/core/logging.py`: logging helpers.
- `src/langgraph_automation/core/redaction.py`: redaction and sensitive-value detection.
- `src/langgraph_automation/core/result_safety.py`: safe-output helpers.
- `src/langgraph_automation/core/summary.py`: bounded summary and display-safe value helpers.
- `src/langgraph_automation/core/types.py`: shared core typing helpers.

## Entrypoints
- `src/langgraph_automation/entrypoints/`: explicit entrypoint namespace for future launch surfaces.
- `src/langgraph_automation/entrypoints/__init__.py`: package marker.

## Integrations
- `src/langgraph_automation/integrations/`: concrete adapters for artifact storage, checkpointing, LLMs, observability, and tools.
- `src/langgraph_automation/integrations/artifact/`: artifact store interfaces and memory implementation.
- `src/langgraph_automation/integrations/artifact/base.py`: artifact store base types.
- `src/langgraph_automation/integrations/artifact/keys.py`: artifact key helpers.
- `src/langgraph_automation/integrations/artifact/memory_store.py`: in-memory artifact store.
- `src/langgraph_automation/integrations/checkpoint/`: checkpoint store interfaces and memory implementation.
- `src/langgraph_automation/integrations/checkpoint/base.py`: checkpoint store base types.
- `src/langgraph_automation/integrations/checkpoint/memory_store.py`: in-memory checkpoint store.
- `src/langgraph_automation/integrations/checkpoint/summary.py`: checkpoint summary helpers.
- `src/langgraph_automation/integrations/llm/`: LLM client interfaces and adapters.
- `src/langgraph_automation/integrations/llm/base.py`: LLM base types.
- `src/langgraph_automation/integrations/llm/litellm_client.py`: LiteLLM adapter.
- `src/langgraph_automation/integrations/llm/observed_client.py`: observed LLM client wrapper.
- `src/langgraph_automation/integrations/observability/`: event sink, context, and failure policy helpers.
- `src/langgraph_automation/integrations/observability/base.py`: observability base types.
- `src/langgraph_automation/integrations/observability/context.py`: observability context binding.
- `src/langgraph_automation/integrations/observability/django_event_sink.py`: Django-backed event sink.
- `src/langgraph_automation/integrations/observability/events.py`: observability event types.
- `src/langgraph_automation/integrations/observability/failure_policy.py`: failure masking and suppression policy.
- `src/langgraph_automation/integrations/observability/types.py`: observability typing helpers.
- `src/langgraph_automation/integrations/tools/`: tool policy, registry, and safe-tool wrappers.
- `src/langgraph_automation/integrations/tools/base.py`: tool base types.
- `src/langgraph_automation/integrations/tools/registry.py`: concrete tool registry.
- `src/langgraph_automation/integrations/tools/policy.py`: tool allow/deny policy logic.
- `src/langgraph_automation/integrations/tools/policy_registry.py`: policy-aware registry composition.
- `src/langgraph_automation/integrations/tools/observed_registry.py`: observed tool registry wrapper.
- `src/langgraph_automation/integrations/tools/safe_tools.py`: safe built-in tools.

## Plugins
- `src/langgraph_automation/plugins/`: plugin registry namespace.
- `src/langgraph_automation/plugins/__init__.py`: package marker.
- `src/langgraph_automation/plugins/registry.py`: plugin registry implementation.

## Runtime
- `src/langgraph_automation/runtime/`: runtime assembly, dependency wiring, context, and secret resolution.
- `src/langgraph_automation/runtime/__init__.py`: runtime package marker.
- `src/langgraph_automation/runtime/assembly.py`: runtime assembly logic.
- `src/langgraph_automation/runtime/context.py`: runtime context object.
- `src/langgraph_automation/runtime/dependencies.py`: runtime dependency definitions.
- `src/langgraph_automation/runtime/secrets.py`: secret resolution helpers.

## Workflows
- `src/langgraph_automation/workflows/`: workflow catalog, preparation, adapter, and reference workflow implementations.
- `src/langgraph_automation/workflows/__init__.py`: workflows package marker.
- `src/langgraph_automation/workflows/adapter.py`: workflow adapter surface.
- `src/langgraph_automation/workflows/catalog.py`: built-in workflow catalog.
- `src/langgraph_automation/workflows/prepare.py`: workflow preparation logic.
- `src/langgraph_automation/workflows/requirements.py`: workflow requirement checks.
- `src/langgraph_automation/workflows/applications/`: future application workflow namespace.
- `src/langgraph_automation/workflows/applications/__init__.py`: application workflow package marker.
- `src/langgraph_automation/workflows/reference/`: reference and diagnostic workflows.
- `src/langgraph_automation/workflows/reference/__init__.py`: reference workflow package marker.
- `src/langgraph_automation/workflows/reference/llm_echo_summary/`: current built-in reference workflow.
- `src/langgraph_automation/workflows/reference/llm_echo_summary/__init__.py`: reference workflow package marker.
- `src/langgraph_automation/workflows/reference/llm_echo_summary/definition.py`: workflow definition entry.
- `src/langgraph_automation/workflows/reference/llm_echo_summary/executable.py`: executable implementation and internal LangGraph assembly.
- `src/langgraph_automation/workflows/reference/llm_echo_summary/state.py`: checkpoint-safe workflow state definition.

## Documentation
- Start with `docs/index.md`.
- `docs/AGENTS.md`: docs subtree guidance and reading order.
- `docs/agent/`: Codex and repo-operation guidance.
- `docs/architecture/`: system shape, layer boundaries, and dataflow rules.
- `docs/api/`: public facade surfaces and staged API contracts.
- `docs/configuration/`: config model, schema, and validation.
- `docs/contracts/`: invariants, error taxonomy, and cross-cutting rules.
- `docs/package/`: package completion, facade design, and verification material.
- `docs/plugins/`: plugin model, registration, and API shape.
- `docs/workflows/`: workflow authoring and readiness guidance.
- `docs/roadmap/`: roadmap and completion gates.
- `docs/assurance/`: system assurance scope, gaps, and safety contracts.
- `docs/adr/`: architecture decision records.

## Tests
- `tests/`: unit, integration, and end-to-end test suites.
- `tests/__init__.py`: test package marker.
- `tests/support/`: shared fixtures, doubles, and helpers for tests.
- `tests/support/engine_fixtures.py`: engine fixture helpers.
- `tests/support/failing_event_sink.py`: failure-mode event sink double.
- `tests/support/import_scan.py`: import scanning helper.
- `tests/support/llm_doubles.py`: LLM test doubles.
- `tests/support/observability_doubles.py`: observability test doubles.
- `tests/support/recording_event_sink.py`: recording event sink double.
- `tests/support/tool_doubles.py`: tool registry and tool doubles.
- `tests/e2e/.gitkeep`: keeps the E2E directory in version control.
- `tests/integration/api/`: public engine facade integration tests.
- `tests/integration/api/test_engine_facade_failure_matrix.py`: failure-matrix coverage for the engine facade.
- `tests/integration/api/test_engine_facade_plugins.py`: plugin-related engine facade coverage.
- `tests/integration/api/test_engine_facade_smoke.py`: smoke coverage for the engine facade.
- `tests/integration/django/`: Django integration tests.
- `tests/integration/django/.gitkeep`: keeps the Django integration directory in version control.
- `tests/integration/django/test_event_sink.py`: Django event sink integration coverage.
- `tests/integration/django/test_web_ui.py`: web UI integration coverage.
- `tests/integration/integrations/.gitkeep`: keeps the integrations directory in version control.
- `tests/unit/api/`: public API, facade, and import boundary tests.
- `tests/unit/api/test_engine_create.py`: engine creation coverage.
- `tests/unit/api/test_engine_errors.py`: engine error coverage.
- `tests/unit/api/test_engine_prepare_workflow.py`: workflow preparation coverage.
- `tests/unit/api/test_framework_errors.py`: framework error surface tests.
- `tests/unit/api/test_plugin_contributions.py`: plugin contribution tests.
- `tests/unit/api/test_public_api_imports.py`: package import boundary tests.
- `tests/unit/api/test_public_engine_imports.py`: engine import boundary tests.
- `tests/unit/api/test_public_errors_imports.py`: error import boundary tests.
- `tests/unit/api/test_public_plugins_imports.py`: plugin import boundary tests.
- `tests/unit/api/test_public_workflow_imports.py`: workflow import boundary tests.
- `tests/unit/api/test_workflow_definitions.py`: workflow definition tests.
- `tests/unit/apps/automation/`: automation app safety and service tests.
- `tests/unit/apps/automation/services/`: service-layer behavior tests.
- `tests/unit/apps/automation/services/test_service_integration_via_engine.py`: service integration via the engine facade.
- `tests/unit/apps/automation/services/test_workflow_graph_resolution.py`: workflow graph resolution tests.
- `tests/unit/apps/automation/services/test_workflow_preparation_service.py`: workflow preparation service tests.
- `tests/unit/apps/automation/test_admin_safety.py`: admin exposure safety tests.
- `tests/unit/apps/automation/test_ui_registry_safety.py`: UI registry safety tests.
- `tests/unit/apps/web/`: dynamic web UI safety tests.
- `tests/unit/apps/web/test_dynamic_ui_safety.py`: dynamic UI rendering safety tests.
- `tests/unit/architecture/`: boundary and import-rule tests.
- `tests/unit/architecture/test_application_readiness_boundary.py`: application readiness boundary tests.
- `tests/unit/architecture/test_application_workflow_public_api_boundary.py`: application workflow public API boundary tests.
- `tests/unit/architecture/test_apps_automation_package_boundary.py`: automation package boundary tests.
- `tests/unit/architecture/test_builtin_workflow_wiring_boundary.py`: built-in workflow wiring boundary tests.
- `tests/unit/architecture/test_config_core_boundary.py`: config/core boundary tests.
- `tests/unit/architecture/test_config_validator_boundary.py`: config validator boundary tests.
- `tests/unit/architecture/test_engine_facade_boundary.py`: engine facade boundary tests.
- `tests/unit/architecture/test_graph_runtime_config_boundary.py`: graph runtime config boundary tests.
- `tests/unit/architecture/test_no_direct_service_map_in_web_views.py`: web view service-map guard tests.
- `tests/unit/architecture/test_no_django_orm_import_in_graphs.py`: graph ORM import guard tests.
- `tests/unit/architecture/test_no_legacy_artifacts.py`: legacy artifact guard tests.
- `tests/unit/architecture/test_no_llm_config_coupling.py`: LLM config coupling guard tests.
- `tests/unit/architecture/test_no_minimal_workflow_coupling.py`: minimal workflow coupling guard tests.
- `tests/unit/architecture/test_no_model_meta_in_templates.py`: template model-meta guard tests.
- `tests/unit/architecture/test_no_obj_dict_in_ui_builders.py`: UI builder object-dict guard tests.
- `tests/unit/architecture/test_no_status_update_in_graph_runner.py`: graph runner status-update guard tests.
- `tests/unit/architecture/test_no_tool_policy_coupling.py`: tool policy coupling guard tests.
- `tests/unit/architecture/test_plugin_public_boundary.py`: plugin public boundary tests.
- `tests/unit/architecture/test_runtime_assembly_boundary.py`: runtime assembly boundary tests.
- `tests/unit/architecture/test_safety_exposure_boundary.py`: safety exposure boundary tests.
- `tests/unit/architecture/test_service_workflow_integration_boundary.py`: service/workflow integration boundary tests.
- `tests/unit/architecture/test_workflow_api_boundary.py`: workflow API boundary tests.
- `tests/unit/architecture/test_workflow_preparation_boundary.py`: workflow preparation boundary tests.
- `tests/unit/architecture/test_workflow_registry_boundary.py`: workflow registry boundary tests.
- `tests/unit/artifact/`: artifact store and key tests.
- `tests/unit/artifact/test_keys.py`: artifact key tests.
- `tests/unit/artifact/test_memory_store.py`: in-memory artifact store tests.
- `tests/unit/automation/`: execution, runtime, policy, and safety tests for automation flows.
- `tests/unit/automation/.gitkeep`: keeps the automation unit-test directory in version control.
- `tests/unit/automation/test_execution_dispatch.py`: execution dispatch tests.
- `tests/unit/automation/test_run_execution_minimal_llm.py`: minimal LLM run execution tests.
- `tests/unit/automation/test_run_failure_observability_masking.py`: failure observability masking tests.
- `tests/unit/automation/test_run_policies.py`: run policy tests.
- `tests/unit/automation/test_run_safety.py`: run safety tests.
- `tests/unit/automation/test_runtime_context.py`: runtime context tests.
- `tests/unit/automation/test_runtime_factory.py`: runtime factory tests.
- `tests/unit/config/`: config loader, model, validator, security, and normalization tests.
- `tests/unit/config/__init__.py`: config test package marker.
- `tests/unit/config/test_config_loader.py`: config loader tests.
- `tests/unit/config/test_config_models.py`: config model tests.
- `tests/unit/config/test_config_normalizer.py`: config normalization tests.
- `tests/unit/config/test_config_security.py`: config security tests.
- `tests/unit/config/test_config_validator_effective_plugins.py`: effective plugin validation tests.
- `tests/unit/config/test_config_validator_event_sinks.py`: event sink validation tests.
- `tests/unit/config/test_config_validator_providers.py`: provider validation tests.
- `tests/unit/config/test_config_validator_stores.py`: store validation tests.
- `tests/unit/config/test_config_validator_tools.py`: tool validation tests.
- `tests/unit/core/`: redaction, result safety, and summary tests.
- `tests/unit/core/test_core_redaction.py`: core redaction tests.
- `tests/unit/core/test_result_safety.py`: result safety tests.
- `tests/unit/core/test_summary.py`: summary helper tests.
- `tests/unit/docs/`: documentation existence and contract coverage tests.
- `tests/unit/docs/test_application_readiness_docs.py`: application readiness docs coverage.
- `tests/unit/docs/test_package_assurance_audit_docs.py`: package assurance docs coverage.
- `tests/unit/docs/test_package_completion_docs.py`: package completion docs coverage.
- `tests/unit/docs/test_package_facade_design_docs.py`: package facade design docs coverage.
- `tests/unit/docs/test_system_assurance_audit_docs.py`: system assurance docs coverage.
- `tests/unit/docs/test_system_safety_exposure_contract_docs.py`: system safety exposure contract docs coverage.
- `tests/unit/graphs/`: graph registry, runtime, runner, instrumentation, and state-safety tests.
- `tests/unit/graphs/.gitkeep`: keeps the graphs unit-test directory in version control.
- `tests/unit/graphs/test_execution_input.py`: execution input tests.
- `tests/unit/graphs/test_graph_registry.py`: graph registry tests.
- `tests/unit/graphs/test_graph_runner_state_safety.py`: graph runner state safety tests.
- `tests/unit/graphs/test_graph_runtime_config.py`: graph runtime config tests.
- `tests/unit/graphs/test_instrumentation.py`: graph instrumentation tests.
- `tests/unit/graphs/test_minimal_llm_workflow.py`: minimal workflow integration tests.
- `tests/unit/graphs/test_minimal_llm_workflow_nodes.py`: minimal workflow node tests.
- `tests/unit/graphs/test_runner.py`: graph runner tests.
- `tests/unit/integrations/`: LLM, tool, checkpoint, and observability integration tests.
- `tests/unit/integrations/test_checkpoint_summary.py`: checkpoint summary tests.
- `tests/unit/integrations/test_litellm_client.py`: LiteLLM client tests.
- `tests/unit/integrations/test_observed_llm_client.py`: observed LLM client tests.
- `tests/unit/integrations/test_observed_tool_registry.py`: observed tool registry tests.
- `tests/unit/integrations/test_policy_aware_tool_registry.py`: policy-aware tool registry tests.
- `tests/unit/integrations/test_safe_tools.py`: safe tool tests.
- `tests/unit/integrations/test_tool_policy.py`: tool policy tests.
- `tests/unit/integrations/test_tool_registry.py`: tool registry tests.
- `tests/unit/observability/`: observability context-binding tests.
- `tests/unit/observability/test_context_binding.py`: observability context binding tests.
- `tests/unit/plugins/`: plugin registry tests.
- `tests/unit/plugins/__init__.py`: plugin test package marker.
- `tests/unit/plugins/test_registry.py`: plugin registry tests.
- `tests/unit/plugins/test_registry_workflows.py`: plugin registry workflow tests.
- `tests/unit/runtime/`: runtime assembly, provider, store, tool, context, and secret tests.
- `tests/unit/runtime/__init__.py`: runtime test package marker.
- `tests/unit/runtime/test_factory_context.py`: factory context tests.
- `tests/unit/runtime/test_runtime_assembler_boundaries.py`: runtime assembler boundary tests.
- `tests/unit/runtime/test_runtime_assembler_event_sinks.py`: event sink assembly tests.
- `tests/unit/runtime/test_runtime_assembler_providers.py`: provider assembly tests.
- `tests/unit/runtime/test_runtime_assembler_stores.py`: store assembly tests.
- `tests/unit/runtime/test_runtime_assembler_tools.py`: tool assembly tests.
- `tests/unit/runtime/test_secret_resolver.py`: secret resolver tests.
- `tests/unit/ui/`: page-spec, registry, and UI redaction tests.
- `tests/unit/ui/.gitkeep`: keeps the UI unit-test directory in version control.
- `tests/unit/ui/test_pagespec_runs.py`: run page-spec tests.
- `tests/unit/ui/test_redaction.py`: UI redaction tests.
- `tests/unit/ui/test_registry.py`: UI registry tests.
- `tests/unit/workflows/`: workflow catalog, adapter, preparation, and requirement tests.
- `tests/unit/workflows/test_builtin_workflow_catalog.py`: built-in workflow catalog tests.
- `tests/unit/workflows/test_builtin_workflow_preparation.py`: built-in workflow preparation tests.
- `tests/unit/workflows/test_catalog.py`: workflow catalog tests.
- `tests/unit/workflows/test_workflow_adapter.py`: workflow adapter tests.
- `tests/unit/workflows/test_workflow_preparer.py`: workflow preparer tests.
- `tests/unit/workflows/test_workflow_requirements.py`: workflow requirement tests.
- `tests/unit/workflows/reference/`: reference workflow contribution tests.
- `tests/unit/workflows/reference/test_llm_echo_summary_contribution.py`: reference workflow contribution coverage.

## Local Only
- `.pytest_cache/`: pytest cache and run artifacts.
- `.ruff_cache/`: Ruff cache files.
- `artifacts/`: local generated artifacts and scratch output.
- `tmp/`: temporary working files.
- `venv/`: local Python virtual environment.
- `.git/`: git metadata and repository history.
