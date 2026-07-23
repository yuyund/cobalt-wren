---
type: contract
status: current
authority: normative
summary: Versioning, deprecation, compatibility, and support policy for the public workflow platform API.
code_refs:
  - src/langgraph_automation/api/plugins.py
  - src/langgraph_automation/api/workflow.py
  - src/langgraph_automation/api/stores.py
  - src/langgraph_automation/api/errors.py
  - src/langgraph_automation/testing
  - src/langgraph_automation/scaffold/workflow_package.py
test_refs:
  - tests/unit/api/test_public_plugins_imports.py
  - tests/unit/api/test_plugin_api_version.py
  - tests/integration/consumer/test_clean_room_scaffold.py
verified:
  date: 2026-07-23
  commit: WORKTREE
  base_commit: 4251cb4
  method:
    - code-and-test-review
---
# Public API Release Policy

## Stable surface

The intended stable external surface consists of `langgraph_automation.api.workflow`, `.plugins`, `.stores`, `.events`, `.errors`, `.engine`, `langgraph_automation.testing`, the `langgraph_automation.plugins` entry-point group, the deployment JSON schema, and the command-line interface documented for external consumers. Django models, application services, renderer internals, and integration implementations remain implementation details unless separately documented.

## Versioning

Package releases follow semantic versioning after 1.0. Before 1.0, breaking changes require a minor version increment and a migration note. `PLUGIN_API_VERSION` is an integer compatibility boundary independent of the package version. Newly scaffolded plugins declare it in metadata. Missing declarations are interpreted as the current version during the pre-1.0 compatibility window; explicit incompatible versions fail discovery with `PLUGIN_API_VERSION_INCOMPATIBLE`.

## Deprecation

After 1.0, a public symbol or behavior is deprecated for at least one minor release before removal in the next major release. Deprecations use `DeprecationWarning`, documentation, and a migration example. Security fixes may remove unsafe behavior immediately.

## Compatibility matrix

| Platform | Plugin API | Python | Django | External workflows |
|---|---:|---:|---:|---|
| 0.x current | 1 | 3.12+ | 5.2 compatible | plain Python and LangGraph reference implementations |
| 1.x planned | 1 | declared per release | declared per release | any implementation satisfying public executable contracts |

External packages should run the Conformance Test Kit against their minimum and maximum supported platform versions and declare normal Python package dependencies for the platform range.
