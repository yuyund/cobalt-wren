---
type: guide
status: current
authority: explanatory
summary: Minimal readability baseline for the registry-driven control-plane UI.
code_refs:
  - src/langgraph_automation/apps/web/templates/base.html
  - src/langgraph_automation/apps/web/templates/dynamic/list.html
  - src/langgraph_automation/apps/web/templates/dynamic/detail.html
  - src/langgraph_automation/apps/web/templates/dynamic/artifact_preview.html
test_refs:
  - tests/integration/django/test_ui_shell.py
verified:
  date: 2026-07-23
  commit: WORKTREE
  base_commit: cbced90
  method:
    - code-and-test-review
---
# UI Readability Baseline

The dynamic renderer remains dependency-free and specification-driven. The baseline adds persistent navigation, a bounded responsive content shell, scrollable tables, readable detail fields, structured action forms, status pills, and safe artifact preview styling. It does not add model introspection, workflow-specific templates, or a frontend framework.
