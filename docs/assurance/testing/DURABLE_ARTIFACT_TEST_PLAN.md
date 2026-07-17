# Durable Artifact Test Plan

This document defines the acceptance plan for the first durable artifact backend.

The protocol sufficiency blocker is resolved.
The filesystem backend is implemented and must be verified against the contract suite.

## Baseline Contract Activation

- reuse `tests/contract/persistence/`
- keep the baseline suite black-box
- keep characterization tests separate
- keep the body-aware artifact contract executable against `MemoryArtifactStore` and `FilesystemArtifactStore`

## Advanced Contract Activation

- immutable write
- idempotent write
- deterministic conflict
- conflict detection
- integrity verification
- restart durability
- concurrency safety
- safe diagnostics

## Required Test Cases

- restart test: create with one store instance, recreate with the same root, then read back
- body round-trip: write bytes, read descriptor + body back
- corruption test: manifest/body mismatch must fail safely
- missing body test: manifest exists but body is absent
- same-key/same-content test: idempotent success
- same-key/different-content test: deterministic conflict
- same-key/different-run test: deterministic conflict
- same-key/different-content-type test: deterministic conflict
- same-key/different-metadata test: deterministic conflict
- defensive copy test: caller mutation does not affect stored state
- deterministic list ordering test: `list_for_run()` does not depend on insertion order
- size correctness
- digest correctness
- repr safety
- safe error test: no root/path/body/secret leakage
- path/symlink test: no root escape, no symlink traversal
- two-instance concurrency test: two store instances on the same root
- process concurrency test: concurrent writers on the same host
- backend registration test: concrete backend must be registered in the test registry
- runtime wiring test: runtime should continue to default to memory
- config validation test: root must be injected as trusted config

## Xfail Policy

- do not normalize missing durable behavior with permanent `xfail`
- keep the executable suite small and meaningful
- add tests only when the backend can actually pass them

## Acceptance Criteria

- durable backend is registered
- baseline suite passes for memory and filesystem
- advanced durable contract suite passes for filesystem
- restart and concurrency tests pass
- safe diagnostics pass
- protocol sufficiency is approved for implementation
- default backend remains memory

## Deferred Work

- checkpoint durability is deferred
- body/metadata orchestration is deferred
- true resume is deferred
