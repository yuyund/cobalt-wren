# Native Contract Decisions

## Requirements

Native dependencies are explicit workflow metadata. The decorator accepts provider profile names, tool names, artifact-store need, and event-sink names. Runtime assembly remains the authority that determines whether these names resolve. Local validation translates missing requirements into author-facing issues and bounded config examples. Explicit declarations are authoritative. A best-effort source lint may warn when direct literal calls to `ctx.llm`, `ctx.tool`, or `ctx.artifact` appear inconsistent with declarations, but lint output never adds runtime dependencies or changes workflow metadata.

## Progress

Progress is a latest snapshot backed by append-only semantic events. `current` is non-negative and monotonic. `total`, once supplied, is positive and stable. Percentage is derived when total is known.

## Metrics

Metrics are append-only measurements with latest-value UI aggregation by metric name. Values are finite numbers. Names are bounded lowercase dotted identifiers. Each Run is limited to 100 distinct names; the live UI displays at most the latest 50 distinct names. Metadata passes through redaction and must remain low cardinality.

## Schema validation ownership

Input/output schema validation remains Native-owned for now because Native controls schema inference and can give precise author diagnostics without changing existing integrations. Moving validation into the generic adapter would be a cross-integration behavior change and requires a separate compatibility decision. Public `WorkflowDefinition` schemas remain framework-neutral metadata, so future common validation is possible without changing Native annotations.


## Requirement lint

`native-validate` reports undeclared direct helper usage in `warnings` while retaining `status: valid`. CI may opt into `--strict-requirements`, which converts those warnings into a validation failure. The lint analyzes only source that Python can retrieve and only direct calls with literal provider or tool names. It deliberately does not infer dynamic names, aliases, helper wrappers, branches, or runtime values. False negatives are acceptable because explicit declarations and runtime requirement checks remain authoritative; false-positive dependency injection is not allowed.
