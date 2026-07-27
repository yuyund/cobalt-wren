# Changelog

All notable changes to Cobalt Wren are documented in this file.

The project follows Semantic Versioning after 1.0. Before 1.0, breaking
changes increment the minor version and include migration notes.

## [Unreleased]

### Added

- PyPI release metadata and artifact-validation automation.
- Architecture decisions for canonical, semantic, and integration-native observations.
- Manual TestPyPI Trusted Publishing workflow and release validation script.
- Consumer-owned installation policy for LLM and workflow framework distributions.
- Apache-2.0 project license and third-party attribution notice.
- Native workflow authoring, local execution, schema validation, telemetry,
  requirements declarations, scaffold generation, and clean-room tests.

### Changed

- Renamed the distribution, Python package, CLI, documentation, and plugin
  entry-point group to Cobalt Wren.

### Compatibility

- Existing Django app labels, database identities, workflow kinds,
  integration IDs, event kinds, checkpoint table defaults, and artifact
  metadata keys remain stable.
- Legacy `LANGGRAPH_AUTOMATION_*` environment variables remain fallback
  aliases when the corresponding `COBALT_WREN_*` variable is absent.

## [0.1.0rc2] - 2026-07-27

- Removed LiteLLM, LangGraph, and LlamaIndex Workflows from runtime and installation extras.
- Made provider and framework SDK installation the consuming application's responsibility.
- Generalized integration health installation guidance to package requirements.

## [0.1.0rc1] - 2026-07-27

First public release candidate for the 0.1.0 alpha release.
