# Durable Checkpoint Test Plan

This document defines the acceptance plan for the versioned checkpoint protocol and the future durable backend.

Status: approved for implementation.

## Baseline Contract Activation

- reuse `tests/contract/persistence/`
- keep the baseline suite black-box
- keep characterization tests separate
- keep the current checkpoint contract executable against `MemoryCheckpointStore`

## Current Characterization

- current memory checkpoint store uses linear append-only versioned history
- current memory checkpoint store is EPHEMERAL
- current checkpoint protocol exposes versioned history
- current checkpoint protocol exposes serializer identity / version
- checkpoint metadata fidelity is lossless and defensively isolated

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
- durable checkpoint backend implementation remains a later step
- checkpoint protocol evolution is complete
- `FilesystemCheckpointStore` remains deferred until W3
- true resume remains separate from storage durability
- runtime selection remains deferred
- metadata orchestration remains deferred

## Xfail Policy

- do not add permanent `xfail` markers for missing durable behavior
- keep current characterization tests executable
- add durable backend tests only after the W3 implementation exists
