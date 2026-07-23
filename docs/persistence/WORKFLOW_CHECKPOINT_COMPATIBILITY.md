---
type: guide
status: current
authority: explanatory
summary: External workflow ownership of versioned checkpoint schemas and migration behavior.
code_refs:
  - src/langgraph_automation/api/errors.py
  - packages/plain_python_workflow/src/plain_python_workflow/plugin.py
  - packages/plain_python_workflow/src/plain_python_workflow/workflow.py
test_refs:
  - tests/integration/api/test_plain_python_checkpoint_compatibility.py
verified:
  date: 2026-07-23
  commit: WORKTREE
  base_commit: cbced90
  method:
    - code-and-test-review
---
# Workflow Checkpoint Compatibility

Checkpoint stores persist opaque bytes and serializer metadata; they do not interpret workflow state. The external workflow declares its current and supported state schema versions and owns migration before state use.

The plain Python reference workflow writes schema version 1, supports versions 0 and 1, and migrates the legacy version 0 field names into version 1. Unknown versions raise `WORKFLOW_CHECKPOINT_INCOMPATIBLE` rather than being parsed optimistically. The framework-neutral execution adapter preserves public FrameworkError categories, so callers receive the explicit compatibility code without exposing framework-specific state.
