---
type: contract
status: current
authority: normative
summary: Safety boundaries for persisted and user-visible execution data.
code_refs:
  - src/langgraph_automation/core/result_safety.py
  - src/langgraph_automation/core/redaction.py
  - src/langgraph_automation/integrations/observability
test_refs:
  - tests/unit/automation/test_run_execution_public_workflow.py
  - tests/unit/apps/web/test_dynamic_ui_safety.py
verified:
  date: 2026-07-23
  commit: WORKTREE
  base_commit: 8e2f19b9ed39bb3b5bf2ce07bbc31cbd58587e33
  method:
    - code-and-test-review
---
# System Safety Exposure Contract

## Purpose

This contract defines what may be persisted, displayed, and emitted across the control plane, dynamic UI, admin screens, and observability surfaces.

The rule is simple: unsafe data can exist transiently inside execution paths, but it must not be copied into user-facing output, event metadata, or persisted body fields outside the intended store boundary.

## Unsafe Data Taxonomy

- raw `Run.input_payload`
- raw LLM request
- raw LLM response
- raw `ToolResult.output`
- provider raw object
- full prompt/messages
- traceback
- exception `repr`
- `api_key`
- token
- password
- authorization header
- credential-bearing URL
- absolute local file path
- checkpoint body
- artifact body
- event metadata containing secret-like values

`Run.input_payload` may exist as a controlled raw input store, but it must not be copied into output, admin, UI, event, span, artifact, or checkpoint display surfaces.

## Safe Data Taxonomy

- `safe_run_output_payload()` result
- `safe_run_error_message()` result
- sanitized summary
- id / kind / status / timestamps
- length / count / truncated preview
- redacted value
- metadata only

Safe data may be shown, searched, or emitted as long as it remains bounded and redacted.

## Persistence Safety Contract

- `Run.output_payload` stores a safe summary only.
- `Run.error_message` stores a safe message only.
- `Run.input_payload` may store controlled raw input, but it must not be copied into output or observability payloads.
- `RunEvent.payload`, `ExecutionSpan.metadata`, `ExecutionSpan.input_summary`, and `ExecutionSpan.output_summary` must not store secrets or raw provider payloads.
- `Artifact.metadata` must remain metadata only.
- `CheckpointMetadata.state_summary` must remain a bounded summary only.
- body/content for artifacts and checkpoints belongs in the store layer, not in Django metadata rows.

## Admin Display Safety Contract

- admin list and detail pages must prefer summary fields over raw payload fields.
- admin display must not directly expose `input_payload`, raw provider objects, traceback text, or secret-like metadata.
- admin detail views may show safe summaries such as `definition_payload_summary`, `input_payload_summary`, `output_payload_summary`, `payload_summary`, `metadata_summary`, and `metrics_summary`.
- admin search and filters may use stable metadata fields only.

## Dynamic UI Display Safety Contract

- dynamic list/detail/form/fragment/action pages must render display-safe values only.
- visible fields should be an explicit allowlist.
- JSON payloads must be shown through bounded summaries, not raw dumps.
- raw object inspection, `__dict__`, and debug dumps are forbidden.
- action fragments must reuse the same safe field specs as list/detail pages.

## Observability Metadata Safety Contract

- event, span, artifact, and checkpoint metadata must be bounded, redacted, and summary-only.
- observability metadata must not contain raw prompts, raw tool output, raw LLM responses, traceback, or absolute local paths.
- provider raw objects may exist transiently inside adapters, but they must not be persisted as metadata.
- artifact and checkpoint body content belongs outside the database metadata rows.

## Error Message Safety Contract

- user-visible and control-plane-visible errors must use safe messages only.
- traceback text must be stripped or collapsed before persistence.
- exception `repr` must not leak secrets, credentials, or absolute paths.
- provider raw error bodies must not be surfaced directly.
- `safe_run_error_message()` is the required normalization path for persisted run failures.

## Artifact/Checkpoint Body-vs-Metadata Separation

- artifact bodies live in the artifact store, not in Django metadata rows.
- checkpoint bodies live in the checkpoint store, not in Django metadata rows.
- the database stores the indexing metadata required to find those bodies later.
- if a durable backend is not available, the body must remain deferred rather than copied into metadata.

## Allowed Display Data

- safe summaries
- bounded previews
- ids and foreign keys
- lifecycle state
- timestamps
- counts and sizes
- redacted labels
- explicit metadata-only fields

## Forbidden Display Data

- raw payload bodies
- raw provider objects
- full prompt/messages
- secret values
- credential-bearing URLs
- traceback text
- exception repr containing secret-like values
- absolute local file paths
- artifact body
- checkpoint body

## Deferred Work

- durable artifact/checkpoint backend is deferred
- api.runtime is deferred
- run_workflow is deferred
- application workflow is deferred
- company_agent is deferred
