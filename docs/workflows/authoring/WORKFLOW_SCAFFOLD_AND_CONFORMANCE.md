---
type: guide
status: current
authority: explanatory
summary: Scaffold and conformance workflow for independently distributed workflow packages.
code_refs:
  - src/cobalt_wren/__main__.py
  - src/cobalt_wren/cli/__init__.py
  - src/cobalt_wren/scaffold/__init__.py
  - src/cobalt_wren/cli/main.py
  - src/cobalt_wren/scaffold/workflow_package.py
  - src/cobalt_wren/testing/workflow_contracts.py
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

`cobalt-wren init-workflow` generates an independent Python distribution with public API imports, plugin entry point, workflow definition, contract tests, and distribution test. The framework choices are `plain-python`, `native`, and `langgraph`. The generated plain-Python `--resumable` method demonstrates only the public resume capability and requires a checkpoint-store declaration; it does not implement durable checkpoint recovery, process restart continuation, or true workflow-state restoration.

`WorkflowContractSuite` validates declaration, framework-neutral presentation metadata, buildability, execution, JSON-safe output, and pause/resume after workflow re-preparation. Existing function-style testing helpers remain public and compatible.

The clean-room integration test generates a package outside the repository, builds platform and consumer wheels, installs them into a separate virtual environment, discovers the consumer through the installed entry point, and executes it without repository `PYTHONPATH` or editable installation.

The scaffold currently generates both workflow implementation and foundation-connection code. These responsibilities should remain conceptually distinct: OSS integration helpers may later replace most connection boilerplate, while any native authoring feature would simplify workflow implementation itself. A generated LangGraph graph is owned by the generated external distribution; it is not a foundation graph and is not automatically introspected by the control plane.

For `--framework langgraph`, the generated builder compiles the graph and returns `integrate_langgraph(...)`. This enables public debug/value stream projection into node spans without requiring generated workflow code to implement observability wrappers. The generated distribution still declares LangGraph directly because the target OSS remains the consumer package's execution dependency.

The generated LangGraph distribution pins the same supported target range as the central integration definition: `langgraph>=1.0,<2`. Native scaffold mode is implemented. LlamaIndex Workflows scaffold mode is not currently implemented; its absence must not be interpreted as lack of integration support.

## Native quick start

Generate an external Native distribution with `cobalt-wren init-workflow --framework native`. The generated workflow uses typed request/result definitions, `ctx.step`, progress, metrics, the ordinary plugin entry-point boundary, and the bundled Native integration. Native scaffold generation rejects resume because Native does not provide durable state restoration.

For an existing module, run `cobalt-wren native-run module:workflow --input '{"name":"Yudai"}'`. This path does not initialize Django. It creates a temporary explicit plugin, executes through the public engine facade, and prints output, inferred schemas, and step metadata. Failed steps preserve the primary exception type and include the Native step name and attempt in the author diagnostic.


## Native documentation

- `NATIVE_QUICK_START.md`
- `NATIVE_SELECTION_GUIDE.md`
- `NATIVE_TROUBLESHOOTING.md`
- `NATIVE_PRODUCTION_READINESS.md`
- `NATIVE_CONTRACT_DECISIONS.md`
