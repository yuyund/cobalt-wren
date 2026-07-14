# langgraph-automation

`langgraph-automation` is a Django control plane with a LangGraph execution plane for automation.

## Project Overview

The project is centered on LangGraph-based automation execution.

Django is responsible for:

- DB schema
- migrations
- admin
- CRUD
- dynamic Web UI
- auth / session / CSRF
- Run / Workflow / Event / Span / Artifact / Checkpoint metadata
- policy / service / selector boundaries

LangGraph is responsible for:

- graph state
- nodes
- routing
- builder
- runner
- runtime context
- LLM / tool / artifact / checkpoint execution

Django Model is the center of the control plane, not the center of the LangGraph execution plane.

## Current Source of Truth Models

- `Workflow`
- `Run`
- `RunEvent`
- `ExecutionSpan`
- `Artifact`
- `CheckpointMetadata`

## Architecture

### Django control plane

- DB schema
- migrations
- admin
- CRUD
- dynamic Web UI
- auth / session / CSRF
- Run lifecycle orchestration
- metadata persistence
- policy / service / selector layers

### LangGraph execution plane

- graph state
- nodes
- routing
- builder
- runner
- runtime context
- LLM / tool / artifact / checkpoint execution

### Integrations

- LLM
- tools
- artifact store
- checkpoint store
- observability

### Preferred dependency direction

- `apps/web/views` -> `apps/automation/ui` -> `apps/automation/selectors` -> `apps/automation/policies` -> `apps/automation/services`
- `apps/automation/services` -> `apps/automation/models` -> `apps/automation/policies` -> `apps/automation/services/runtime.py` -> `graphs/runner` -> `integrations`
- `graphs/runner` / `graphs/nodes` -> `graphs/runtime` -> `integrations` interfaces
- `integrations` -> external libraries / backend implementations

## Source of Truth

- `Run`: execution unit truth
- `Workflow`: automation definition truth
- `RunEvent`: append-only timeline / audit log truth
- `ExecutionSpan`: execution step summary / trace tree truth
- `Artifact`: artifact metadata truth
- `ArtifactStore`: artifact body truth
- `CheckpointMetadata`: checkpoint metadata / index / safe summary truth
- `CheckpointStore`: checkpoint body truth
- `Policy`: action eligibility truth
- `Service`: run lifecycle update truth
- `GraphRunner`: LangGraph execution entrypoint
- `GraphRuntime`: dependency bundle for the execution plane
- `EventSink`: observability write boundary
- `SpanRef`: opaque span handle passed through the execution plane
- `UI Registry`: Web UI allowlist
- `PageSpec`: UI presentation derivative

## Rules

- Django models stay in the control plane.
- Graph execution logic stays out of Django models.
- Graph nodes must not query the Django ORM directly.
- `graphs/runner.py` must not update `Run.status` directly.
- Web views must not call LLMs, tools, or checkpoint backends directly.
- Dynamic UI should be driven by registry and page-spec objects, not by model introspection in templates.
- `PageSpec` is derived data and must not be stored in the database.
- `CheckpointMetadata` must never store checkpoint bodies.
- `Artifact.storage_key` must be an opaque relative key, not a raw filesystem path.
- `Artifact` must not expose real file paths directly.
- `ExecutionSpan` is summary data only; do not store full prompts, full responses, or raw checkpoint bodies there.

## Observability

- `RunEvent` is the timeline / audit log.
- `ExecutionSpan` is the execution step summary / trace tree.
- `EventSink` is the observability write boundary.
- `span_started` / `span_completed` / `span_failed` are the primary EventSink APIs.
- `node_*` / `llm_*` / `tool_*` are thin convenience methods that must not split the write path.
- `semantic_event` is the node-level semantic event entrypoint.
- Semantic events use the `semantic.<name>` event type prefix.

Current EventSink failure policy:

- `span_started` failure is not suppressed.
- `span_completed` failure after successful primary execution is not suppressed yet.
- `span_failed` failure after a primary exception is suppressed and logged so the primary failure is preserved.
- `span_failed` failure after a failed `ToolResult` is suppressed and logged so the failed `ToolResult` is preserved.
- graph failure handling suppresses observability failures so `ExecutionResult(status='failed')` is preserved.

Future TODO:

- ResilientEventSink
- fallback sink
- async observability
- DB retry / outbox
- worker-safe observability

## Checkpoints

- `CheckpointStore` stores checkpoint bodies.
- `CheckpointMetadata` stores checkpoint metadata, index, and a bounded safe summary.
- `state_summary` must be redacted and bounded.
- `state_summary` must not contain the full checkpoint state.

## Summary / Redaction

- `core/redaction.py` is the source of truth for secret, path, and nested payload redaction.
- `core/summary.py` is the source of truth for bounded summaries, previews, and hashes.
- UI, checkpoint, observability, and future integration wrappers must reuse the core helpers.
- Raw prompts, raw responses, raw stdout, raw stderr, raw graph state, and raw filesystem paths must not be stored directly in the database.

## Run Result Safety and Resume Semantics

- `Run.output_payload` stores a bounded, redacted summary only.
- `Run.error_message` stores a bounded, redacted error summary only.
- `services/runs.py` is the final write-time safety boundary for `Run` persistence.
- `ExecutionResult` is an execution candidate returned by the runner; services normalize it before persisting to `Run`.
- `retry_run` means re-execution from the current run input, not checkpoint continuation.
- `resume_run` and `resume_graph_once` are unsupported until true checkpoint resume semantics exist.
- The current UI should not present checkpoint resume as a working flow.

## Runtime Composition

`apps/automation/services/runtime.py` is the dependency assembly boundary for the execution plane.

It composes concrete dependencies only:

- `build_event_sink()` -> `DjangoEventSink`
- `build_llm_client()` -> `LiteLLMClient -> ObservedLLMClient` when enabled, otherwise `None`
- `build_tool_registry()` -> `InMemoryToolRegistry -> PolicyAwareToolRegistry -> ObservedToolRegistry`
- `build_artifact_store()` -> `MemoryArtifactStore`
- `build_checkpoint_store()` -> `MemoryCheckpointStore`

`build_tool_registry()` currently registers a single safe toy tool:

- `echo` -> safe bounded preview echo tool

It must not:

- execute graphs
- update `Run` lifecycle state
- contain workflow business logic
- call LLMs or tools directly

Future wrapper order:

- LLM: `ConcreteLLMClient -> ObservedLLMClient`
- Tool: `ConcreteToolRegistry -> PolicyAwareToolRegistry -> ObservedToolRegistry`
- Artifact: `ConcreteArtifactStore -> ObservedArtifactStore?` future
- Checkpoint: `ConcreteCheckpointStore -> ObservedCheckpointStore?` future

## Configuration Boundary

- `settings` / environment variables hold secrets and deployment-level config.
- `Workflow.definition_payload` holds workflow-level config such as model choice, allowed tools, and graph behavior.
- `Workflow.definition_payload.graph.kind` selects the workflow graph. The current supported value is `llm_echo_summary`.
- `Workflow.definition_payload.llm` is the minimal LLM schema.
- `Workflow.definition_payload.tools.allowed` is the minimal tool allowlist schema.
- Missing or empty `tools.allowed` means deny all.
- `Run.input_payload` holds one-shot execution input.
- `Run.input_payload` must not grant tool permissions.
- `Run.input_payload` must not provide LLM credentials.
- `Run.input_payload` must not provide `model`, `api_key`, `base_url`, `tools.allowed`, or `graph.kind`.
- `Run.output_payload` holds safe summary only.
- `RunEvent.payload`, `ExecutionSpan.metadata`, `ExecutionSpan.input_summary`, and `ExecutionSpan.output_summary` must not store secrets or raw provider payloads.
- runtime factory reads settings, `Workflow`, and `Run` context to assemble dependencies.

Workflow minimal config:

```json
{
  "graph": {
    "kind": "llm_echo_summary"
  },
  "llm": {
    "enabled": true,
    "model": "test-model",
    "temperature": 0.2,
    "max_tokens": 512
  },
  "tools": {
    "allowed": ["echo"]
  }
}
```

Secret policy:

- secrets must not be stored in `Workflow.definition_payload`
- secrets must not be stored in `Run.input_payload`
- secrets must not be stored in `Run.output_payload`
- secrets must not be stored in `RunEvent.payload`
- secrets must not be stored in `ExecutionSpan.metadata`
- secrets must not be stored in `ExecutionSpan.input_summary`
- secrets must not be stored in `ExecutionSpan.output_summary`

## Minimal LLM Workflow

- default graph: `llm_echo_summary`
- input schema: `{"text": "..."}` or `{"prompt": "..."}`
- execution flow: `Run.input_payload` -> EchoTool node -> LLM summary node -> final output candidate -> `services/runs.py` -> `safe_run_output_payload()` -> `Run.output_payload`
- `GraphRuntime.require_llm_client()` and `GraphRuntime.require_tool_registry()` are the only dependency access points inside nodes.
- nodes do not import Django ORM models, provider adapters, or concrete tool classes.
- `ObservedLLMClient` records LLM spans and `ObservedToolRegistry` records tool spans.
- full prompt, full response, and raw tool output are not persisted.
- `LLMResult.raw` is not persisted.

## Artifact Store Semantics

- `MemoryArtifactStore` is the current in-memory artifact store used by the runtime factory.
- It stores normalized artifact metadata in process memory only.
- It does not persist artifact bodies.
- `ARTIFACT_ROOT` is reserved for a future filesystem-backed `LocalFileArtifactStore`.
- `LocalFileArtifactStore` is not implemented yet.
- `S3ArtifactStore` is not implemented yet.

## Dynamic UI

- `UI Registry` is the allowlist of public models, fields, actions, and related sections.
- `PageSpec` is the derived render model for generic templates.
- `TableSpec` and `RelatedSectionSpec` carry related data for list/detail rendering.
- Templates do not introspect Django model `_meta` directly.
- `apps/web` should stay thin and render `PageSpec` objects.

## Current Graph

- The production graph is the minimal `llm_echo_summary` LangGraph flow.
- `graphs/builders.py` builds and compiles the graph.
- `graphs/runner.py` invokes the compiled graph.
- `graphs/instrumentation.py` manages node span lifecycle.
- `graphs/nodes` contains execution logic only; nodes do not emit lifecycle events directly.

## Runtime Dependency Policy

- `GraphRuntime` is the dependency bundle passed into graph nodes.
- `LLMClient` and `ToolRegistry` are optional runtime dependencies.
- nodes that need them must call `require_llm_client()` / `require_tool_registry()`.
- missing dependencies fail fast with `MissingRuntimeDependencyError`.
- placeholder clients are not injected when a dependency is absent.
- `ObservedLLMClient` exists as the decorator layer for real LLM adapters, and the runtime factory currently wires it around `LiteLLMClient` when LLM is enabled.
- `ObservedToolRegistry` exists as the decorator layer for real tool registries, and the runtime factory currently wires it around the safe echo tool stack.

## Tool Policy Foundation

Tool execution permission is a separate policy layer from concrete tool execution and observability.

Wrapper order:

- `ConcreteToolRegistry`
- `PolicyAwareToolRegistry`
- `ObservedToolRegistry`

Responsibilities:

- `ConcreteToolRegistry` owns tool registration, lookup, and execution.
- `PolicyAwareToolRegistry` owns authorization and deny-result generation. It does not know about EventSink, Django, or graph execution.
- `ObservedToolRegistry` owns span recording for allowed, denied, failed, and exceptional tool outcomes. It does not know policy internals.

Policy deny behavior:

- policy deny is represented as a failed `ToolResult`
- policy deny does not raise by default
- policy evaluation exceptions are propagated
- deny metadata must not contain raw kwargs or secrets

Policy configuration vs execution metadata:

- `AllowlistToolPolicy` owns `allowed_tools`
- `ToolPolicyContext` carries execution metadata only (`run_id`, `workflow_id`, `thread_id`)

Workflow tool allowlist schema:

```json
{
  "tools": {
    "allowed": ["echo"]
  }
}
```

Configuration boundary:

- `Workflow.definition_payload` may define allowed tools
- the runtime factory should parse workflow config and build pure policy data
- policy objects receive pure data only
- `Run.input_payload` must not grant tool permissions

Current built-in safe tool:

- `echo` -> safe bounded preview echo tool
- no shell / file / network access
- output is redacted and bounded

Future TODO:

- strict `Workflow` validation for `tools.allowed`
- add shell/file/network policy types
- add filesystem path policy
- add network domain policy
- add more safe toy tools
- connect additional concrete tool registries later

## Dependencies

Core runtime:

- Django
- LangGraph

Runtime integrations:

- psycopg
- django-environ

Development:

- pytest
- pytest-django
- ruff
- mypy

Not used in the current design:

- FastAPI
- Uvicorn
- SQLAlchemy
- Alembic
- Celery
- Redis
- OpenTelemetry
- Prometheus
- Streamlit
- Gradio
- Chainlit

## Repository Layout

```text
langgraph-automation/
|-- README.md
|-- manage.py
|-- pyproject.toml
|-- src/
|   \-- langgraph_automation/
|       |-- config/
|       |-- core/
|       |-- apps/
|       |   |-- automation/
|       |   \-- web/
|       |-- graphs/
|       |-- integrations/
|       \-- entrypoints/
\-- tests/
```