---
type: guide
status: current
authority: explanatory
summary: Framework-free external workflow and real cross-process durable resume validation.
code_refs:
  - packages/plain_python_workflow
  - src/langgraph_automation/api/workflow.py
  - src/langgraph_automation/apps/automation/services/runs.py
test_refs:
  - tests/integration/api/test_plain_python_workflow.py
  - tests/integration/api/test_plain_python_distribution.py
  - tests/integration/django/test_plain_python_process_resume.py
verified:
  date: 2026-07-23
  commit: WORKTREE
  base_commit: 13b8f2c
  method:
    - code-and-test-review
---
# Plain Python Workflow

This external distribution has no LangGraph dependency. It owns a versioned JSON state machine, pauses by returning the public `paused` result, persists opaque JSON through the public checkpoint store, and resumes through the optional public `resume()` capability.

A subprocess integration test starts the Run in one Python interpreter and resumes it in another using a shared SQLite control-plane database and filesystem artifact/checkpoint stores. This verifies that neither framework memory nor a prepared executable instance is required for durable resume.
