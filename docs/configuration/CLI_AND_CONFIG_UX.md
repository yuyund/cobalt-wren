---
type: guide
status: current
authority: explanatory
summary: Unified CLI and explicit deployment configuration file behavior.
code_refs:
  - src/cobalt_wren/cli/main.py
  - src/cobalt_wren/config/settings.py
  - src/cobalt_wren/apps/automation/services/runtime.py
  - pyproject.toml
test_refs:
  - tests/unit/cli/test_cli_commands.py
  - tests/unit/config/test_runtime_config_file.py
verified:
  date: 2026-07-23
  commit: WORKTREE
  base_commit: 4251cb4
  method:
    - code-and-test-review
---
# CLI And Configuration UX

The `cobalt-wren` executable provides workflow scaffolding, migrations, local server startup, plugin and workflow inspection, workflow validation, Run operations, artifact download, and deployment diagnosis.

A global `--config PATH` option sets the explicit deployment JSON file before Django startup. The file takes precedence over `COBALT_WREN`; invalid or unreadable files produce `CONFIG_FILE_INVALID`. Secrets remain environment references inside the package configuration rather than literal values.

`doctor` checks database connectivity, pending automation migrations, installed plugin discovery, and runtime engine assembly. It emits machine-readable JSON and returns a nonzero status when a check fails.
