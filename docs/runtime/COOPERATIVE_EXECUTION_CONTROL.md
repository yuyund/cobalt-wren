---
type: guide
status: current
authority: explanatory
summary: Framework-neutral cooperative cancellation and deadline propagation for external workflows.
code_refs:
  - src/langgraph_automation/api/errors.py
  - src/langgraph_automation/api/workflow.py
  - src/langgraph_automation/apps/automation/models/run.py
  - src/langgraph_automation/apps/automation/policies/runs.py
  - src/langgraph_automation/apps/automation/services/execution.py
  - src/langgraph_automation/apps/automation/services/execution_control.py
  - src/langgraph_automation/apps/automation/services/runs.py
  - src/langgraph_automation/apps/automation/migrations/0003_run_timed_out_status.py
test_refs:
  - tests/integration/django/test_execution_control.py
  - tests/unit/automation/test_run_policies.py
  - tests/unit/api/test_public_workflow_imports.py
verified:
  date: 2026-07-23
  commit: WORKTREE
  base_commit: cbced90
  method:
    - code-and-test-review
---
# Cooperative Execution Control

`WorkflowExecutionContext.control` is an optional framework-neutral token. External workflows call `check()` at node, tool, polling, or batch boundaries. It raises a public cancellation or timeout execution error. The token also exposes cancellation state and remaining deadline seconds.

The Django execution plane maintains a process-local registry for active Runs. `cancel_run()` signals an active token before persisting `cancelled`. A workflow that observes the token exits through the normal execution adapter and produces a cancelled result and lifecycle event. A declared positive `timeout_seconds` in prepared workflow metadata becomes a monotonic deadline and maps to the terminal `timed_out` Run status, which is retryable.

This is cooperative propagation, not unsafe thread termination. A workflow that never checks the token cannot be forcibly interrupted in-process; process isolation remains the future hard-stop boundary.
