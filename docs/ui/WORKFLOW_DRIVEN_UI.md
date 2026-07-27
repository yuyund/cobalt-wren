---
type: guide
status: current
authority: explanatory
summary: Safe projection of external workflow metadata into dynamic resume forms and artifact body access.
code_refs:
  - src/cobalt_wren/api/engine.py
  - src/cobalt_wren/apps/automation/ui/workflow_projection.py
  - src/cobalt_wren/apps/automation/ui/actions.py
  - src/cobalt_wren/apps/automation/ui/builders.py
  - src/cobalt_wren/apps/automation/ui/specs.py
  - src/cobalt_wren/apps/automation/services/artifact_access.py
  - src/cobalt_wren/apps/automation/services/runtime.py
  - src/cobalt_wren/apps/web/views/artifacts.py
  - src/cobalt_wren/apps/web/views/dynamic_actions.py
  - src/cobalt_wren/apps/web/urls.py
  - src/cobalt_wren/apps/web/templates/dynamic
  - src/cobalt_wren/apps/automation/ui/run_live.py
  - src/cobalt_wren/apps/web/templates/dynamic/components/value.html
  - src/cobalt_wren/apps/web/templates/dynamic/components/field_value.html
  - src/cobalt_wren/apps/automation/ui/values.py
  - src/cobalt_wren/config/settings.py
  - src/cobalt_wren/apps/automation/migrations/0006_diagnostic_payload.py
  - src/cobalt_wren/apps/automation/management/commands/purge_expired_diagnostics.py
  - src/cobalt_wren/apps/automation/management/__init__.py
  - src/cobalt_wren/apps/automation/management/commands/__init__.py
  - src/cobalt_wren/apps/web/templates/dynamic/diagnostic_detail.html
  - src/cobalt_wren/apps/web/views/diagnostics.py
  - src/cobalt_wren/apps/automation/ui/diagnostics.py
  - src/cobalt_wren/apps/automation/services/diagnostics.py
  - src/cobalt_wren/apps/automation/models/diagnostic.py
  - src/cobalt_wren/apps/web/templates/dynamic/components/detail_section.html
  - src/cobalt_wren/apps/web/templates/dynamic/components/detail_facts.html
  - src/cobalt_wren/apps/web/templates/dynamic/components/semantic_detail.html
  - src/cobalt_wren/apps/automation/ui/detail_presentations.py
  - src/cobalt_wren/apps/web/views/run_live.py
  - src/cobalt_wren/integrations/observability/django_event_sink.py
  - src/cobalt_wren/integrations/llm/observed_client.py
  - src/cobalt_wren/apps/web/static/cobalt_wren/components.css
  - src/cobalt_wren/apps/web/static/cobalt_wren/theme-tokens.css
  - src/cobalt_wren/apps/web/templatetags/ui_presentation.py
  - src/cobalt_wren/apps/web/presentation/__init__.py
  - src/cobalt_wren/apps/web/presentation/run_components.py
  - src/cobalt_wren/apps/web/static/cobalt_wren
  - src/cobalt_wren/apps/web/static/cobalt_wren/live-run.js
  - src/cobalt_wren/apps/web/templates/dynamic/components/llm_conversation.html
  - packages/human_approval_workflow
  - packages/saga_workflow
  - packages/plain_python_workflow
test_refs:
  - tests/integration/django/test_workflow_driven_ui.py
  - tests/integration/django/test_web_ui.py
  - tests/unit/apps/web/test_dynamic_ui_safety.py
  - tests/unit/architecture/test_no_direct_service_map_in_web_views.py
  - tests/integration/django/test_run_live_ui.py
  - tests/integration/django/test_run_live_asgi.py
  - tests/unit/architecture/test_run_live_projection_boundary.py
  - tests/unit/integrations/test_observed_llm_client.py
  - tests/unit/apps/web/test_run_live_stream.py
  - tests/unit/apps/web/test_run_presentation.py
  - tests/unit/apps/automation/test_ui_values.py
  - tests/unit/core/test_summary.py
  - tests/integration/django/test_event_sink.py
  - tests/unit/core/test_diagnostics.py
  - tests/integration/django/test_diagnostic_details.py
verified:
  date: 2026-07-23
  commit: WORKTREE
  base_commit: cbced90
  method:
    - code-and-test-review
---
# Workflow-Driven UI

A prepared workflow exposes only safe presentation values: public metadata, input/output JSON schemas, and the `extra` mapping. The executable remains opaque.

External workflows may declare `resume_actions`. Each action supplies a title, an optional danger marker, a constant workflow-owned payload, and an object JSON schema. The control plane supports a bounded subset of string, integer, number, boolean, enum, and textarea fields. Unknown schema constructs are ignored rather than executed or introspected.

For a waiting Run, the UI intersects declared actions with `allowed_actions` from the safe persisted output summary. It renders a CSRF-protected form, includes the current checkpoint ID, validates required and enum fields, merges user input with the workflow-owned constant payload, and calls the normal `resume_run()` service. Policies reject stale or duplicate terminal resumes.

Artifact metadata remains in Django while bodies remain in the deployment-owned ArtifactStore. Preview is limited to 256 KiB and to JSON, plain text, or Markdown. JSON and text previews are redacted. Downloads use attachment disposition and `nosniff`; body identity is checked against the control-plane Run.

The generic list and related-table builders link allowlisted first-column values to their registered detail pages. No Django model introspection or workflow-framework-specific type enters the renderer.

## Structured Field Values

Generic list, detail, and fragment templates delegate every field to the shared `field_value.html` renderer. Structured summary fields are projected into renderer-neutral `ValueSpec` trees before template rendering. JSON strings are parsed only for allowlisted summary field names; ordinary strings that resemble JSON remain text.

Mappings and lists render as responsive key-value or ordered structures, empty structures render a shared empty state, and large or nested structures remain bounded. Generic summary envelopes (`keys`, `types`, `sizes`, optional `preview`) are normalized before rendering: a non-empty preview becomes the primary display, while schema-only summaries become one compact row per retained key instead of exposing the envelope internals. A collapsed `Technical JSON` diagnostic appears once at the field boundary and contains only the already summarized and redacted projection, never the raw database `JSONField`. Model registrations and workflow metadata do not contain template paths, CSS classes, or renderer variants.

## Semantic Detail Pages

Execution Span, Run Event, Artifact, and Checkpoint details use a thin renderer-neutral `DetailPresentationSpec`. The projection selects primary facts, meaningful content sections, and optional technical fields from the existing generic `DetailPageSpec`; it does not read workflow objects or carry template names, CSS classes, or Tabler variants.

All four models share the same semantic detail templates. Empty sections are omitted, repeated summary wrappers are normalized, and bounded redacted scalar previews are preferred over schema-only type information. The generic detail renderer remains the fallback for models without a semantic layout. Adding or changing one semantic layout therefore affects the projection configuration rather than the parent detail template or unrelated models.

## Progressive Inspection

Structured fields use three disclosure levels. The normal detail page shows a bounded semantic preview; fields backed by useful retained or control-plane values expose an HTMX `Inspect details` action; `Technical JSON` remains the final machine-oriented representation of the same bounded, redacted value. Nested renderers do not own URLs, permissions, or audit behavior.

`ValueSpec` distinguishes available, partial, unavailable, redacted, and empty values. Historical `***TRUNCATED***` markers render as `Preview unavailable`, not as a recoverable value. Item and character limits retain `omitted_count` and `truncation_reason`, allowing the renderer to state how much was omitted. Semantic sections that contain only empty, redacted, or unavailable values are omitted unless an inspectable detail exists.

## Diagnostic Payload Contract

New observability records may retain a `DiagnosticPayload` snapshot for supported summary fields. Snapshots are redacted before persistence, bounded to 64 KiB, limited to eight levels and one hundred items at the initial pass, and expire after `COBALT_WREN_DIAGNOSTIC_RETENTION_DAYS` days (default seven). `purge_expired_diagnostics` removes expired records. Diagnostic persistence is secondary observability work and may not mask the primary execution result.

The diagnostic endpoint reuses the registered detail selector and the target model's `automation.view_*` permission. Successful and denied inspection attempts are appended to `OperationAuditLog`. Rendering is lazy and field-scoped. Existing control-plane JSON fields may be used only after redaction and bounding; values that are already summary envelopes are not treated as recoverable detail. Consequently, historical values replaced by truncation markers remain unavailable, while new snapshots can be inspected without exposing workflow internals or unrestricted raw payloads.

## OSS-Neutral Dynamic Composition

The target architecture does not divide a Run page into a low-information common UI and a separate rich framework UI. Canonical operational information and integration-provided sections are composed into one page around the same Run and execution-unit identities. The foundation renderer knows block schemas, permissions, safety, and layout; it does not know which OSS produced a section.

Integration contributions may supply bounded renderer-neutral facts, tables, timelines, trees, graphs, metrics, diffs, JSON inspection, banners, and action forms. Arbitrary templates, HTML, CSS, JavaScript, and executable renderer code are outside the integration contract. Framework-specific data that cannot be normalized remains available through versioned integration projections rather than being discarded.

The common UI earns its place through cross-framework correlation, unified actions, audit, policy, SLA and ownership context, business semantics, safe artifact/checkpoint access, and organization-wide search. Deep framework debugging may link to the OSS-native UI rather than duplicating every engine-specific tool. This section describes the intended extension architecture; the current implementation provides the safe generic projection and diagnostic foundation but not the complete integration contribution registry.

## Implemented Integration Projection Sections

Run and ExecutionSpan detail specs now include generic integration projection sections. The section contract contains renderer-safe data only: integration ID, schema ID, title, owner identity, creation time, classification, truncation state, and a structured payload value. The dynamic detail template renders the same component for every integration and contains no framework-name branch.

The first producer is the experimental LangGraph helper, which contributes task, interrupt, and checkpoint-reference schemas. These sections are composed with the existing canonical detail and related records rather than placed in a separate framework-only page. Expired projections are excluded from rendering.

## Implemented Integration Actions

Waiting Runs may now receive common action descriptors through `integration.actions.v1` projections. The dynamic action area composes these with existing canonical and workflow-defined actions. Input forms are generated from a bounded object schema supporting string, integer, number, boolean, enum, and textarea presentation.

Descriptor records are not trusted as executable commands. Submission rechecks Run policy, record expiry and ownership, descriptor availability, current workflow preparation, and resume capability. Successful and denied requests pass through the same operation audit and permission mechanisms as existing Run actions. Inline deployments resume immediately; worker deployments enqueue the same normalized payload as a Resume execution job.

## LlamaIndex Workflows Projection

The generic projection sections now have a second producer. LlamaIndex Workflows step and event records render through the same Run and ExecutionSpan detail composition used by LangGraph. The renderer does not contain LlamaIndex-specific templates or branches; schema identity, title, owner metadata, and bounded payload drive the presentation.

## Integration Summary Cards

Run and ExecutionSpan detail pages now aggregate active projection records by opaque integration ID before rendering individual records. The summary card reports projection count, distinct execution-unit owners, interaction owners, checkpoint references, schema IDs, bounded-record count, and a recognized canonical status when one is present. Each summary links to the corresponding projection group.

The aggregation is framework-neutral: it uses integration ID, schema ID, owner kind, external owner identity, truncation state, and an optional canonical `status` value. It does not contain LangGraph or LlamaIndex branches. Individual projection records are rendered as collapsible detail cards so that a Run with many task or event snapshots remains navigable.

## Current Integration State And Timeline

Projection records are now separated into current state, timeline, and technical detail. Current state contains only the latest snapshot for each stable integration subject. Timeline contains snapshot transitions and streamed events in semantic order. Reference and action records remain available through integration summaries and technical projections without being misrepresented as execution state.

The current-state and timeline specifications are renderer-neutral and use projection kind, subject kind, subject external identity, schema ID, optional canonical status, occurrence time, and sequence. Individual versioned records remain accessible through collapsed technical projection cards.
