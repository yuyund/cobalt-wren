# System Assurance Scope

This audit expands assurance from the package boundary to the whole system.

Code is the source of truth.
Tests are the source of truth.
Docs are only design intent.
The supplemental report is hypothesis only.

## Relationship To Package Assurance

Package assurance established the package-facing facade, workflow preparation, and package boundary hardening.
System assurance rechecks how that package surface is consumed by the Django control-plane, execution path, persistence path, UI, and observability path.

That means this audit does not replace the package audit baseline.
It widens the scope of evidence collection so the project can see where package-level guarantees stop and system-level guarantees still need work.

## System Layer Inventory

| Layer | Role | Classification | Primary evidence |
| --- | --- | --- | --- |
| `api` | Public and provisional facades for callers | Public-facing boundary | `src/langgraph_automation/api/engine.py`, `api/errors.py`, `api/plugins.py`, `api/workflow.py`, `tests/unit/api/*`, `tests/integration/api/*` |
| `config` | Load, normalize, secure, and validate declarative package config | Internal / provisional | `src/langgraph_automation/config/*`, `tests/unit/config/*`, `tests/unit/architecture/test_config_*` |
| `plugins` | Manual plugin registration and resolution | Internal registry behind public plugin vocabulary | `src/langgraph_automation/plugins/registry.py`, `tests/unit/plugins/*`, `tests/unit/architecture/test_plugin_public_boundary.py` |
| `runtime` | Assemble concrete runtime dependencies from validated config | Internal / provisional | `src/langgraph_automation/runtime/*`, `tests/unit/runtime/*`, `tests/unit/architecture/test_runtime_assembly_boundary.py` |
| `workflows` | Workflow contributions, preparation, catalog composition, built-in example workflows | Internal / provisional | `src/langgraph_automation/workflows/*`, `tests/unit/workflows/*`, `tests/unit/architecture/test_workflow_*` |
| `graphs` | Graph execution foundation and compiled graph runtime | Internal foundation | `src/langgraph_automation/graphs/*`, `tests/unit/graphs/*`, `tests/unit/architecture/test_no_django_orm_import_in_graphs.py` |
| `core` | Redaction, summary, safe result helpers, and core errors | Safety utility boundary | `src/langgraph_automation/core/*`, `tests/unit/core/*`, `tests/unit/automation/test_run_safety.py` |
| `integrations` | LLM, tool, artifact, checkpoint, observability adapters | External I/O boundary | `src/langgraph_automation/integrations/*`, `tests/unit/integrations/*`, `tests/integration/django/test_event_sink.py` |
| `apps/automation` | Django control-plane models, services, policies, selectors, admin, UI registry | Control-plane / persistence / orchestration / UI | `src/langgraph_automation/apps/automation/*`, `tests/unit/automation/*`, `tests/unit/apps/automation/*`, `tests/integration/django/test_web_ui.py` |
| `apps/web` | Dynamic UI rendering and request entrypoints | Presentation layer | `src/langgraph_automation/apps/web/*`, `tests/integration/django/test_web_ui.py`, `tests/unit/architecture/test_no_direct_service_map_in_web_views.py` |

## Apps/Automation Sub-Layers

| Sub-layer | Responsibility | Boundary status | Evidence |
| --- | --- | --- | --- |
| `models` | Persistent control-plane state for Workflow, Run, ExecutionSpan, RunEvent, Artifact, CheckpointMetadata | Django persistence | `src/langgraph_automation/apps/automation/models/*` |
| `services` | Run lifecycle, workflow preparation bridge, runtime assembly, execution dispatch | Transitional control-plane orchestration | `src/langgraph_automation/apps/automation/services/*`, `tests/unit/apps/automation/services/*` |
| `selectors` | Read-side query helpers | Safe read boundary | `src/langgraph_automation/apps/automation/selectors/*` |
| `policies` | Action visibility and lifecycle policy | Control-plane policy boundary | `src/langgraph_automation/apps/automation/policies/runs.py`, `tests/unit/automation/test_run_policies.py` |
| `ui` | Registry-driven specs, builders, redaction, and action dispatch | Presentation-adjacent policy layer | `src/langgraph_automation/apps/automation/ui/*`, `tests/unit/ui/*`, `tests/unit/architecture/test_no_obj_dict_in_ui_builders.py` |
| `admin` | Django admin exposure for control-plane models | Privileged presentation layer | `src/langgraph_automation/apps/automation/admin.py` |

## Assurance Axes

The system audit is organized around these axes:

- layer and dependency boundaries
- dataflow boundaries
- lifecycle boundaries
- safety and redaction boundaries
- error boundaries
- persistence boundaries
- UI exposure boundaries
- observability boundaries
- extension boundaries

## Deferred And Out Of Scope

The following are deferred or intentionally out of scope for this audit block:

- `run_workflow`
- `langgraph_automation.api.runtime`
- worker / queue / outbox
- true resume semantics
- external plugin discovery
- Python entry point discovery
- production application workflow implementation
- `company_agent`
- graph runner public API
