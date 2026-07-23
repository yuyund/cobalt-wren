---
type: guide
status: current
authority: explanatory
summary: Reproducible local UI demo data generated through real control-plane execution paths.
code_refs:
  - scripts/seed_ui_demo.py
  - src/langgraph_automation/integrations/observability/base.py
  - src/langgraph_automation/integrations/observability/django_event_sink.py
  - packages/human_approval_workflow/src/human_approval_workflow/workflow.py
  - packages/saga_workflow/src/saga_workflow/workflow.py
test_refs:
  - tests/integration/django/test_ui_demo_seed.py
  - tests/integration/django/test_event_sink.py
  - tests/integration/api/test_human_approval_control_plane.py
  - tests/integration/api/test_saga_workflow.py
  - tests/support/recording_event_sink.py
verified:
  date: 2026-07-23
  commit: WORKTREE
  base_commit: 11a28a0
  method:
    - code-and-test-review
---
# UI Demo Data

Run `venv/bin/python scripts/seed_ui_demo.py` from the repository root. The script applies pending migrations, replaces only records whose names start with `[demo]`, and recreates its filesystem artifact and checkpoint bodies under `/tmp/langgraph-automation-ui-demo`.

The script does not insert fabricated span, event, artifact, or checkpoint rows. It creates Workflow and Run inputs, then uses `start_run()`, `resume_run()`, and `cancel_run()` with the external Human Approval and Saga plugins. Observability metadata is projected through `DjangoEventSink`, while bodies are written through the configured filesystem stores.

The generated states include pending, waiting, succeeded, failed, and cancelled runs; approval and revision pauses; Saga success, retryable partial failure, and compensation; graph spans and run events; artifact metadata with content type and size; and checkpoint metadata with namespace.

Re-running the script is deterministic at the demo namespace boundary: prior `[demo]` database records and `/tmp/langgraph-automation-ui-demo` bodies are removed, while non-demo records are retained.
