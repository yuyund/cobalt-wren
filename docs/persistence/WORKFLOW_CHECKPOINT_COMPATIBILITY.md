---
type: guide
status: current
authority: explanatory
summary: External workflow ownership of versioned checkpoint schemas and migration behavior.
code_refs:
  - src/cobalt_wren/api/errors.py
  - packages/plain_python_workflow/src/plain_python_workflow/plugin.py
  - packages/plain_python_workflow/src/plain_python_workflow/workflow.py
test_refs:
  - tests/integration/api/test_plain_python_checkpoint_compatibility.py
verified:
  date: 2026-07-25
  commit: WORKTREE
  method:
    - code-and-test-review
---
# Workflow Checkpoint Compatibility

Checkpoint stores persist opaque bytes and serializer metadata; they do not interpret workflow state. The external workflow declares its current and supported state schema versions and owns migration before state use.

The external plain Python compatibility package writes schema version 1, supports versions 0 and 1, and migrates legacy version 0 field names into version 1. Unknown versions raise `WORKFLOW_CHECKPOINT_INCOMPATIBLE` rather than being parsed optimistically. The framework-neutral execution adapter preserves public `FrameworkError` categories, so callers receive the explicit compatibility code without exposing workflow-specific state.

Native examples do not claim checkpoint continuation or schema migration. Plain executable and checkpoint compatibility remain independently verified lower-level extension contracts.

## Control-Plane Persistence Direction

Future OSS integrations should persist three distinct forms of information: indexed canonical records required for operations and audit; bounded semantic attributes useful across integrations; and versioned integration-specific projections attached to canonical owners. The foundation does not interpret a framework projection beyond schema validation, safety classification, retention, and ownership.

Framework objects, compiled graphs, handles, pickles, private dumps, and unlimited event histories are not valid control-plane persistence formats. Helpers extract stable JSON-safe projections through public APIs. Canonical lifecycle events are append-only while current-state rows are materialized for efficient reads.

Checkpoint ownership must be explicit as foundation-managed, integration-managed, or externally managed. An integration-managed checkpoint may remain in the OSS backend while the control plane stores its safe reference, compatibility metadata, resumability, and action route. Artifact bodies likewise remain in an artifact backend; control-plane rows retain safe identity, classification, integrity, retention, and preview metadata.

## Integration Projection Records

Integration-specific execution detail is retained separately from checkpoint bodies. `IntegrationProjectionRecord` is append-only and may target a Run or ExecutionSpan while preserving an opaque integration ID and versioned schema ID. Payloads are redacted and bounded before persistence, carry classification and retention metadata, and expire according to their retention class.

The LangGraph integration records public debug-stream checkpoint references as `langgraph.checkpoint_ref.v1`. These records contain safe checkpoint identity, parent identity, next-node, task-count, and source information only. They do not change checkpoint ownership and do not make a non-resumable storage backend resumable.
