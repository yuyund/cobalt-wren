---
type: architecture
status: current
authority: normative
summary: Framework-neutral Run UI rendered through a registry-driven Tabler component layer and updated by asynchronous SSE.
code_refs:
  - src/cobalt_wren/apps/automation/ui/run_live.py
  - src/cobalt_wren/apps/web/presentation/__init__.py
  - src/cobalt_wren/apps/web/presentation/run_components.py
  - src/cobalt_wren/apps/web/templatetags/ui_presentation.py
  - src/cobalt_wren/apps/web/views/run_live.py
  - src/cobalt_wren/apps/web/views/dynamic_pages.py
  - src/cobalt_wren/apps/web/urls.py
  - src/cobalt_wren/apps/web/templates/base.html
  - src/cobalt_wren/apps/web/templates/dynamic/run_live.html
  - src/cobalt_wren/apps/web/templates/dynamic/components
  - src/cobalt_wren/apps/web/templates/dynamic/detail.html
  - src/cobalt_wren/apps/web/templates/dynamic/list.html
  - src/cobalt_wren/apps/web/templates/dynamic/artifact_preview.html
  - src/cobalt_wren/apps/web/static/cobalt_wren/theme-tokens.css
  - src/cobalt_wren/apps/web/static/cobalt_wren/components.css
  - src/cobalt_wren/apps/web/static/cobalt_wren/live-run.js
  - src/cobalt_wren/core/summary.py
  - src/cobalt_wren/config/settings.py
  - src/cobalt_wren/apps/automation/migrations/0006_diagnostic_payload.py
  - src/cobalt_wren/apps/automation/management/commands/purge_expired_diagnostics.py
  - src/cobalt_wren/apps/web/templates/dynamic/diagnostic_detail.html
  - src/cobalt_wren/apps/web/views/diagnostics.py
  - src/cobalt_wren/apps/automation/ui/diagnostics.py
  - src/cobalt_wren/apps/automation/services/diagnostics.py
  - src/cobalt_wren/apps/automation/models/diagnostic.py
  - src/cobalt_wren/integrations/llm/observed_client.py
  - src/cobalt_wren/integrations/observability/django_event_sink.py
  - pyproject.toml
test_refs:
  - tests/integration/django/test_run_live_ui.py
  - tests/integration/django/test_run_live_asgi.py
  - tests/integration/django/test_ui_shell.py
  - tests/integration/django/test_web_ui.py
  - tests/integration/django/test_workflow_driven_ui.py
  - tests/integration/django/test_event_sink.py
  - tests/unit/core/test_diagnostics.py
  - tests/integration/django/test_diagnostic_details.py
  - tests/unit/apps/web/test_dynamic_ui_safety.py
  - tests/unit/apps/web/test_run_presentation.py
  - tests/unit/apps/web/test_run_live_stream.py
  - tests/unit/integrations/test_observed_llm_client.py
  - tests/unit/architecture/test_run_live_projection_boundary.py
verified:
  date: 2026-07-24
  commit: WORKTREE
  base_commit: cd3a01e
  method:
    - code-and-test-review
---
# Live Run UI

## Boundary

The live UI reads stable control-plane records only: `Run`, `ExecutionSpan`, `RunEvent`, and `ExecutionJob`. It does not import LangGraph, prepare workflow executables, inspect external workflow package objects, or add presentation metadata to the public workflow contract. LangGraph workflows, plain-Python workflows, and externally distributed Python workflows use the same renderer when they emit the existing framework-neutral records.

Backend differences are projected into bounded display values. Worker mode can expose `ExecutionJob.heartbeat_at`; inline mode renders `Not reported`. Current activity is selected from a running span, a waiting Run state, a queued job, `Run.last_span_name`, or the Run status in that order.

## Component Registry

`apps.web.presentation.run_components` owns the ordered renderer registry:

1. `run.current_state`
2. `run.failure_diagnostic`
3. `run.llm_conversation`
4. `run.node_output`
5. `run.timeline`

`dynamic/run_live.html` iterates this registry and does not name individual component templates. Adding a semantic Run component requires a projection, a renderer template, and one registry entry; the parent Run template does not change. Template paths and Tabler classes remain inside `apps.web` and never enter workflow metadata or the public workflow API.

Status values are mapped to Tabler badge classes by `ui_presentation.status_badge_class`. Models and UI specs expose semantic status text only. Replacing Tabler therefore affects renderer mappings and templates rather than backend or workflow contracts.

## Theme Boundary

Tabler Core supplies the Bootstrap-based grid, cards, tables, forms, badges, spacing, responsive containers, and typography. Project-specific styling is split into:

- `theme-tokens.css`: CSS custom properties for density, spacing, readable width, conversation width, and timeline indentation.
- `components.css`: control-plane-specific timeline, conversation, node-output, artifact, and long-value rules expressed through those tokens.

Visual tuning should change tokens first. Component CSS is reserved for structures Tabler does not provide. Generic page templates do not contain workflow-specific styles.

## Asynchronous Fragment Contract

`/ui/runs/<id>/live/` renders the reusable HTML fragment. Under ASGI, `/ui/runs/<id>/stream/` returns an asynchronous `StreamingHttpResponse` backed by an async generator. Under WSGI, the stream endpoint returns `503 SSE requires ASGI` immediately; `live-run.js` then uses the existing HTMX fragment fallback instead of holding a synchronous worker open.

The generator loads the synchronous Django projection through a thread-sensitive `sync_to_async` boundary. It sends a `fragment` event only when the projection revision changes, emits an SSE heartbeat comment while unchanged, stops immediately for terminal Runs, and exits cleanly when request cancellation propagates after client disconnect. The response disables proxy buffering and caching.

`live-run.js` opens `EventSource`, replaces the complete fragment, and closes on a terminal payload. It contains no workflow state or component rendering logic. Browsers without EventSource use HTMX polling against the same fragment endpoint.

## LLM Conversation Summary

`ObservedLLMClient` records bounded, redacted message previews as internal observability metadata. `DjangoEventSink` preserves a dedicated bounded `message_previews` field without relaxing the generic observability depth, item-count, character, or secret-redaction limits. This is an internal observability summary schema, not a public workflow contract.

The LLM component renders system/user roles when available, falls back to the combined prompt preview for older spans, displays a bounded response preview, provider, model, retry attempt, token counts, duration, and a link to the underlying span. Interactions use native `<details>` disclosure rather than custom JavaScript.

Raw prompts, raw responses, token streams, arbitrary provider objects, and workflow state are not stored or displayed by this feature.

## Node Output

The `run.node_output` component displays the latest bounded `ExecutionSpan.output_summary` from a node span. It preserves `#run-node-output[data-extension-point="node-final-output"]` for future expansion while avoiding raw output payloads and framework-specific state.

## Quality Contract

Tests cover component order, registry-driven rendering, renderer-only status mapping, separated theme tokens, asynchronous fragment suppression, heartbeat emission, cancellation, terminal closure, authorization, role-summary persistence, secret redaction, empty states, 100-span timelines, responsive structural classes, static discovery, wheel inclusion, and framework-dependency boundaries.

## Failure Diagnostics

Terminal failed or timed-out Runs project a `RunFailureDiagnosticSpec` from existing control-plane records. The component identifies the failed activity, span type, attempt, last successful activity, bounded input at failure, and the related failure event. It uses the shared structured value renderer and never reads workflow internals or raw payload storage. Successful Runs omit the component. Raw JSON remains a technical fallback for unknown fields, not the primary diagnostic path.

## Progressive Diagnostic Access

Run input and output summaries remain concise on the initial page. When the underlying bounded control-plane payload or an active retained diagnostic snapshot is available, the shared field renderer exposes `Inspect details` and loads a field-scoped fragment on demand. Inspection is permission checked and audit logged. Historical summaries whose values were irreversibly replaced by truncation markers display `Preview unavailable`; the UI does not imply that those values can be recovered.
