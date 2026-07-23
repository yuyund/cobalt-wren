---
type: guide
status: current
authority: explanatory
summary: External Saga workflow validating parallel partial failure, individual retry, compensation, and reconciliation.
code_refs:
  - packages/saga_workflow
  - .github/workflows/ci.yml
test_refs:
  - tests/integration/api/test_saga_workflow.py
  - tests/integration/api/test_saga_distribution.py
verified:
  date: 2026-07-23
  commit: WORKTREE
  base_commit: 2ae60d8
  method:
    - code-and-test-review
---
# Saga Workflow

The external workflow fans out three operations in parallel, records branch-local success or failure, pauses on partial failure, retries only retryable branches, or compensates successful branches in reverse order. The platform remains unaware of branch topology and Saga semantics.
