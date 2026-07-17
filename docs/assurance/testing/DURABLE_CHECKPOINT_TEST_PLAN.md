# Durable Checkpoint Test Plan

This document defines the acceptance plan for a future durable checkpoint backend.

Status: blocked by protocol.

The current `CheckpointStore` protocol is not sufficient to express versioned execution state, lineage, serializer compatibility, or specific-version history reads. The durable backend implementation remains deferred until the protocol is evolved.

## Baseline Contract Activation

- reuse `tests/contract/persistence/`
- keep the baseline suite black-box
- keep characterization tests separate
- keep the current checkpoint contract executable against `MemoryCheckpointStore`

## Current Characterization

- current memory checkpoint store uses latest-state replacement by `run_id`
- current memory checkpoint store is EPHEMERAL
- current checkpoint protocol does not expose versioned history
- current checkpoint protocol does not expose serializer identity/version

## Required Audit Tests

- exact protocol signature inspection
- exact field inventory inspection
- current overwrite semantics characterization
- current missing behavior characterization
- current delete scope characterization
- current state-body shape characterization
- current runtime wiring characterization
- current Django metadata boundary characterization

## Future Durable Acceptance Cases

- immutable checkpoint version write
- idempotent retry for same canonical checkpoint write
- deterministic conflict for same identity / different content
- specific-version read
- latest selection
- history listing
- parent / lineage preservation
- serializer compatibility / version compatibility
- restart durability
- safe deletion scope
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

- protocol sufficiency audit is explicitly `BLOCKED_BY_PROTOCOL`
- current checkpoint store remains latest-state only
- current memory backend keeps its current semantics
- checkpoint protocol evolution is deferred until the audit can be reopened
- no durable checkpoint backend implementation is attempted before protocol evolution
- true resume remains separate from storage durability
- runtime selection remains deferred
- metadata orchestration remains deferred

## Xfail Policy

- do not add permanent `xfail` markers for missing durable behavior
- keep current characterization tests executable
- add durable backend tests only after protocol evolution provides a sufficient contract
