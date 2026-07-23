---
type: guide
status: current
authority: explanatory
summary: Scaffold and conformance workflow for independently distributed workflow packages.
code_refs:
  - src/langgraph_automation/__main__.py
  - src/langgraph_automation/cli/__init__.py
  - src/langgraph_automation/scaffold/__init__.py
  - src/langgraph_automation/cli/main.py
  - src/langgraph_automation/scaffold/workflow_package.py
  - src/langgraph_automation/testing/workflow_contracts.py
  - pyproject.toml
test_refs:
  - tests/integration/api/test_external_workflow_distribution.py
  - tests/unit/cli/test_workflow_scaffold.py
  - tests/unit/testing/test_workflow_contract_suite.py
  - tests/integration/consumer/test_clean_room_scaffold.py
verified:
  date: 2026-07-23
  commit: WORKTREE
  base_commit: 4251cb4
  method:
    - code-and-test-review
---
# Workflow Scaffold And Conformance

`langgraph-automation init-workflow` generates an independent Python distribution with public API imports, plugin entry point, workflow definition, contract tests, and distribution test. The initial framework choices are `plain-python` and `langgraph`; pause/resume scaffolds require a checkpoint store declaration.

`WorkflowContractSuite` validates declaration, framework-neutral presentation metadata, buildability, execution, JSON-safe output, and pause/resume after workflow re-preparation. Existing function-style testing helpers remain public and compatible.

The clean-room integration test generates a package outside the repository, builds platform and consumer wheels, installs them into a separate virtual environment, discovers the consumer through the installed entry point, and executes it without repository `PYTHONPATH` or editable installation.
