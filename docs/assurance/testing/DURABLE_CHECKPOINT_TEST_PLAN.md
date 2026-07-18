# Durable Checkpoint Test Plan

This document defines the acceptance plan for the versioned checkpoint protocol and the filesystem durable backend.

Status: implemented and approved for implementation.

## Baseline Contract Activation

- reuse `tests/contract/persistence/`
- keep the baseline suite black-box
- keep characterization tests separate
- keep the current checkpoint contract executable against `MemoryCheckpointStore`
- keep the durable filesystem backend executable against the same reusable contract suite

## Current Characterization

- current memory checkpoint store uses linear append-only versioned history
- current memory checkpoint store is EPHEMERAL
- current filesystem checkpoint store is PROCESS_DURABLE
- current checkpoint protocol exposes versioned history
- current checkpoint protocol exposes serializer identity / version
- checkpoint metadata fidelity is lossless and defensively isolated
- execution persistence orchestration remains out of scope for this backend plan

## Required Audit Tests

- exact protocol signature inspection
- exact field inventory inspection
- current append semantics characterization
- current missing behavior characterization
- current identity / namespace isolation characterization
- current state-body shape characterization
- current runtime wiring characterization
- current Django metadata boundary characterization

## Durable Acceptance Cases

- immutable checkpoint version write
- idempotent retry for same canonical checkpoint write
- deterministic conflict for same identity / different content
- specific-version read
- latest selection
- history listing
- parent / lineage preservation
- metadata fidelity
- serializer compatibility / version compatibility
- restart durability
- safe deletion scope through omission
- safe diagnostics
- concurrency and lost-update detection
- crash-window recovery

## Filesystem Backend Coverage

- filesystem backend is implemented
- baseline suite passes for memory and filesystem
- advanced durable contract suite passes for filesystem
- default checkpoint backend remains memory
- default backend remains memory
- filesystem runtime selection is explicit opt-in and typed
- runtime selection is covered by config / runtime assembly tests

## Failure-Mode Focus

- before body publication
- body before record
- record before head
- head before return
- same identity / same body retry
- same identity / different body retry
- two writers / same parent
- corrupt head
- head points to missing record
- record points to missing body
- unsupported serializer version

## Acceptance Criteria

- protocol sufficiency audit is explicitly `APPROVED_FOR_IMPLEMENTATION`
- current checkpoint store remains linear and versioned
- current memory backend keeps its current semantics
- filesystem backend is implemented and process durable
- durable checkpoint backend implementation is now complete
- checkpoint protocol evolution is complete
- checkpoint runtime selection is complete
- true resume remains separate from storage durability
- metadata orchestration remains deferred
- execution lifecycle orchestration remains a separate block

## Xfail Policy

- do not add permanent `xfail` markers for missing durable behavior
- keep current characterization tests executable
- add durable backend tests only after the W3 implementation exists
