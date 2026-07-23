---
type: guide
status: current
authority: explanatory
summary: Framework-neutral pause/resume contract validated with an external LangGraph human approval workflow.
code_refs:
  - src/langgraph_automation/api/workflow.py
  - src/langgraph_automation/api/engine.py
  - src/langgraph_automation/workflows/adapter.py
  - src/langgraph_automation/apps/automation/services/runs.py
  - src/langgraph_automation/apps/automation/services/execution.py
  - src/langgraph_automation/apps/automation/models/run.py
  - src/langgraph_automation/apps/automation/policies/runs.py
  - src/langgraph_automation/apps/automation/migrations/0002_run_waiting_status.py
  - packages/human_approval_workflow
  - .github/workflows/ci.yml
test_refs:
  - tests/integration/api/test_human_approval_workflow.py
  - tests/integration/api/test_human_approval_control_plane.py
  - tests/integration/api/test_human_approval_distribution.py
  - tests/unit/automation/test_run_policies.py
  - tests/unit/api/test_public_workflow_imports.py
verified:
  date: 2026-07-23
  commit: WORKTREE
  base_commit: abd98e2
  method:
    - code-and-test-review
---
# Human Approval Workflow

The public contract represents pause/resume without importing LangGraph types. A workflow may expose `execute()` only, or optionally expose `resume()`.

The external reference implementation uses LangGraph `interrupt()` and `Command(resume=...)`, but serializes its framework-owned state into opaque checkpoint bytes. The control plane only tracks `waiting`, prepares the workflow again, passes a `WorkflowResumeRequest`, and normalizes the resulting status.

The same adapter contract is tested with a plain Python class to ensure LangGraph is not required.
