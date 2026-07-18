# Persistence Contract Test Harness

This document defines the reusable black-box contract test harness for ArtifactStore and CheckpointStore implementations.

## Purpose

- Validate the current protocol surface with code-first evidence.
- Keep baseline contract tests reusable across current and future backends.
- Separate current characterization behavior from the shared contract.
- Provide a deterministic onboarding path for future durable backends.

## Black-Box Contract Policy

- Test only public/provisional store methods.
- Treat concrete backends as opaque implementations.
- Do not inspect private dicts, private counters, or internal layout.
- Do not derive guarantees from current overwrite behavior unless the test is explicitly labeled as characterization.

## Baseline Contract

- ArtifactStore: body round-trip, missing behavior, run isolation, defensive copy, deterministic list ordering, idempotent write, conflict detection, safe reference rejection, diagnostic non-exposure.
- CheckpointStore: genesis append, versioned round-trip, missing behavior, run isolation, namespace isolation, defensive copy, idempotent retry, conflict detection, specific-version read, ordered history listing, diagnostic non-exposure.
- The checkpoint baseline is a characterization of versioned append-only history, not destructive latest-state replacement.
- Baseline tests live under `tests/contract/persistence/`.

## Characterization Tests

- `tests/unit/artifact/test_memory_store.py` documents current artifact overwrite behavior.
- `tests/unit/integrations/test_checkpoint_summary.py` documents current checkpoint latest-state replacement behavior.
- These tests describe the current memory backend only and do not define the shared baseline contract.

## Test-Only Backend Registry

- `tests/support/persistence/backends.py` registers the current concrete backends.
- The registry is compared against concrete implementation discovery to catch onboarding drift.
- The current registry contains `MemoryArtifactStore`, `FilesystemArtifactStore`, `MemoryCheckpointStore`, and `FilesystemCheckpointStore`.

## Test-Only Capability Model

- `tests/support/persistence/capabilities.py` defines test-only durability and contract capability enums.
- The capability model stays in tests and does not become production API.
- The current memory backends are classified as `EPHEMERAL`.
- The current filesystem backends are classified as `PROCESS_DURABLE`.

## Durability Levels

- `EPHEMERAL`: process lifetime only.
- `PROCESS_DURABLE`: survives restart in the same environment.
- `DEPLOYMENT_DURABLE`: shared across replacement instances.

## Artifact Baseline Cases

- body round-trip
- missing behavior
- run isolation
- defensive copy
- deterministic list ordering
- idempotent write
- conflict detection
- safe reference rejection
- diagnostic non-exposure
- size correctness
- digest correctness
- repr safety

## Checkpoint Baseline Cases

- genesis append
- round-trip
- missing behavior
- run isolation
- defensive copy
- namespace isolation
- idempotent retry
- conflict detection
- specific-version read
- latest selection
- history listing
- diagnostic non-exposure

## Fault Injection Model

- `tests/support/persistence/faults.py` provides deterministic BEFORE and AFTER failure injection.
- Occurrence control supports first call, Nth call, and every call.
- Fault records intentionally avoid raw body, secret, and traceback content.

## Registration Guard

- `tests/contract/persistence/test_persistence_backend_registration.py` compares the explicit registry to discovered concrete implementations.
- A new concrete backend must be registered before it can pass the guard.

## Runtime Wiring Regression

- `tests/unit/runtime/test_persistence_runtime_wiring.py` checks that the current runtime wires the in-memory backends.
- The regression remains a characterization of the current default wiring, not a permanent type contract.

## Runner Boundary Regression

- `tests/unit/architecture/test_persistence_contract_boundary.py` ensures `graphs.runner` does not import concrete persistence backends or Django models.
- The runner stays on protocol and runtime abstractions only.

## Advanced Durable Contract Catalog

- immutable write
- idempotent write
- conflict detection
- integrity verification
- restart durability
- concurrency
- versioned history

Checkpoint durable contract requirements are now implemented for the filesystem backend and remain part of the shared harness.
Runtime selection and orchestration remain future work.

## Xfail Policy

- Do not normalize missing durable behavior with permanent `xfail` tests.
- Keep the baseline suite executable.
- Keep advanced durable semantics in docs and later blocks until they can be implemented and verified.

## Future Backend Onboarding Procedure

1. Implement the concrete backend.
2. Add a test backend registry entry.
3. Classify durability level.
4. Run the baseline contract suite.
5. Declare the required advanced capability profile.
6. Add backend-specific fault tests.
7. Add restart test coverage when the durability level requires it.
8. Add safety regression coverage for diagnostics and exposure boundaries.

## Required Onboarding Profiles

### Durable Artifact Backend Target Profile

- BASELINE
- DEFENSIVE_COPY
- SAFE_REFERENCE
- IMMUTABLE_WRITE
- IDEMPOTENT_WRITE
- CONFLICT_DETECTION
- INTEGRITY_VERIFICATION
- RESTART_DURABILITY

### Durable Checkpoint Backend Target Profile

- BASELINE
- DEFENSIVE_COPY
- RUN_ISOLATION
- IDEMPOTENT_WRITE
- CONFLICT_DETECTION
- SPECIFIC_VERSION_READ
- LATEST_SELECTION
- HISTORY_LISTING
- LINEAGE
- SERIALIZER_DESCRIPTOR
- INTEGRITY_VERIFICATION
- RESTART_DURABILITY
- THREAD_CONCURRENT_APPEND

Any capability that the current protocol cannot express remains a gap until the interface evolves.

## Deferred Work

- durable ArtifactStore implementation is deferred for deployment-level durability
- checkpoint runtime selection is deferred
- production capability model is not added
- body/metadata orchestration is deferred
- true resume is deferred
- application workflow is deferred
- company_agent is deferred
