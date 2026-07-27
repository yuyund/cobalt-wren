---
type: guide
status: current
authority: explanatory
summary: Deployment-configurable UI authentication, operation permissions, and append-only audit records.
code_refs:
  - src/cobalt_wren/apps/automation/admin.py
  - src/cobalt_wren/apps/automation/models/__init__.py
  - src/cobalt_wren/apps/web/access.py
  - src/cobalt_wren/apps/web/views/dynamic_pages.py
  - src/cobalt_wren/apps/web/views/dynamic_actions.py
  - src/cobalt_wren/apps/web/views/artifacts.py
  - src/cobalt_wren/apps/automation/policies/runs.py
  - src/cobalt_wren/apps/automation/models/audit.py
  - src/cobalt_wren/apps/automation/services/audit.py
  - src/cobalt_wren/apps/automation/migrations/0004_operation_audit_and_run_permissions.py
  - src/cobalt_wren/config/settings.py
test_refs:
  - tests/integration/django/test_ui_authorization_audit.py
verified:
  date: 2026-07-23
  commit: WORKTREE
  base_commit: 4251cb4
  method:
    - code-and-test-review
---
# Authorization And Audit

Local development remains open by default. Setting `COBALT_WREN_REQUIRE_LOGIN=true` requires an authenticated Django user for UI access and checks standard view permissions plus explicit `start_run`, `resume_run`, `cancel_run`, and `retry_run` permissions.

Artifact body preview and download require `automation.view_artifact`. Operation attempts record actor identifier, action, target, outcome, safe payload summary, optional Run, and message. Denied and successful UI operations are both audited; raw request payloads are passed through the existing safe-output boundary before persistence.
