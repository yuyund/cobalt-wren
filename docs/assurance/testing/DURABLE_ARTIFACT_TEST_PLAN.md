# Durable Artifact Test Plan

This document defines the acceptance plan for the first durable artifact backend once protocol evolution enables it.

## Baseline Contract Activation

- reuse `tests/contract/persistence/`
- add the backend to the test-only registry
- keep the baseline suite black-box
- keep characterization tests separate

## Advanced Contract Activation

- immutable write
- idempotent write
- deterministic conflict
- integrity verification
- restart durability
- concurrency safety
- safe diagnostics

## Required Test Cases

- restart test: create with one store instance, recreate with the same root, then read back
- corruption test: manifest/body mismatch must fail safely
- missing body test: manifest exists but body is absent
- same-key/same-content test: idempotent success
- same-key/different-content test: deterministic conflict
- two-instance concurrency test: two store instances on the same root
- process concurrency test: concurrent writers on the same host
- safe error test: no root/path/body/secret leakage
- path/symlink test: no root escape, no symlink traversal
- backend registration test: concrete backend must be registered in the test registry
- runtime wiring test: runtime should be able to select the backend explicitly
- config validation test: root must be injected as trusted config

## Xfail Policy

- do not normalize missing durable behavior with permanent `xfail`
- keep the executable suite small and meaningful
- add tests only when the backend can actually pass them

## Acceptance Criteria

- durable backend is registered
- baseline suite passes
- advanced durable contract suite passes
- restart and concurrency tests pass
- safe diagnostics pass
- protocol sufficiency blocker is resolved before implementation work starts
- default backend remains memory until the filesystem backend is explicitly opted in

## Deferred Work

- implementation is deferred until the protocol evolves
- checkpoint durability is deferred
- body/metadata orchestration is deferred
- true resume is deferred
