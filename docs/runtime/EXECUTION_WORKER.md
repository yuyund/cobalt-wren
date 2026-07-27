---
type: guide
status: current
authority: explanatory
summary: Database-backed process-isolated workflow execution jobs and worker lifecycle.
code_refs:
  - src/cobalt_wren/apps/automation/ui/registry.py
  - src/cobalt_wren/apps/automation/models/job.py
  - src/cobalt_wren/apps/automation/services/jobs.py
  - src/cobalt_wren/apps/automation/services/dispatch.py
  - src/cobalt_wren/apps/automation/migrations/0005_execution_job.py
  - src/cobalt_wren/cli/main.py
  - src/cobalt_wren/config/settings.py
test_refs:
  - tests/integration/django/test_execution_worker.py
verified:
  date: 2026-07-23
  commit: WORKTREE
  base_commit: 4251cb4
  method:
    - code-and-test-review
---
# Execution Worker

`COBALT_WREN_EXECUTION_MODE=worker` changes Run operation dispatch from inline execution to a database-backed execution job. The Web process enqueues an immutable operation payload; `cobalt-wren worker` claims queued jobs in a separate process, records worker identity and heartbeat, executes the existing Run service, and records terminal job outcome.

The queue enforces one active queued or claimed job per Run. Claimed jobs with stale heartbeats can be returned to the queue. Cancellation remains an immediate control-plane operation so an active cooperative execution can observe the cancellation token.

The default remains `inline` for local development and compatibility. Production deployments can run multiple worker processes against PostgreSQL; SQLite is retained for local single-worker validation.
