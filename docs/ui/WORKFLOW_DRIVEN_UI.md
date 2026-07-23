---
type: guide
status: current
authority: explanatory
summary: Safe projection of external workflow metadata into dynamic resume forms and artifact body access.
code_refs:
  - src/langgraph_automation/api/engine.py
  - src/langgraph_automation/apps/automation/ui/workflow_projection.py
  - src/langgraph_automation/apps/automation/ui/actions.py
  - src/langgraph_automation/apps/automation/ui/builders.py
  - src/langgraph_automation/apps/automation/ui/specs.py
  - src/langgraph_automation/apps/automation/services/artifact_access.py
  - src/langgraph_automation/apps/automation/services/runtime.py
  - src/langgraph_automation/apps/web/views/artifacts.py
  - src/langgraph_automation/apps/web/views/dynamic_actions.py
  - src/langgraph_automation/apps/web/urls.py
  - src/langgraph_automation/apps/web/templates/dynamic
  - packages/human_approval_workflow
  - packages/saga_workflow
  - packages/plain_python_workflow
test_refs:
  - tests/integration/django/test_workflow_driven_ui.py
  - tests/integration/django/test_web_ui.py
  - tests/unit/apps/web/test_dynamic_ui_safety.py
  - tests/unit/architecture/test_no_direct_service_map_in_web_views.py
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
