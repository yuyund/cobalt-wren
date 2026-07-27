# Native Troubleshooting

## Input validation fails

Run `native-validate` with the same input. Issues use JSON paths, for example `$.count: expected integer, got str`. Correct the payload before inspecting step code.

## A provider, tool, or sink is missing

Declare dependencies on `@workflow` with `provider_profiles`, `tools`, `artifact_store`, and `event_sinks`. Run `native-validate --config deployment.json`; its `suggestions` field contains a bounded configuration example. Do not place secret values in configuration. Use environment-variable references.

## A step fails

The local diagnostic preserves the primary exception type and adds the step name and final attempt. Check retry eligibility, timeout, callable arguments, and whether a repeated call needs `occurrence_key`.

## Progress update is rejected

Progress is monotonic. Once `total` is reported it cannot change in that Run. `current` cannot exceed `total`.

## Metric recording is rejected

Metric names are lowercase dotted identifiers. Values must be finite numbers. A Run may report at most 100 distinct metric names; repeated updates to an existing name are allowed and the UI presents the latest value.


## `native-validate` reports an undeclared requirement warning

Add the provider profile, tool, or artifact-store declaration to `@workflow` after confirming the helper call is part of the workflow contract. Use `--strict-requirements` in CI to fail on detectable declaration drift. The lint is best effort and does not replace review or runtime requirement validation. Dynamic names and calls hidden behind wrappers are not inferred.
