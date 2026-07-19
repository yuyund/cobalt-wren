# Artifact Emission Contract

This document fixes the logical artifact emission contract before any persistence wiring is added.

Code is the source of truth.
Tests are the source of truth.

## Executive decision

Artifact persistence is explicit only.

explicit artifact emission only

- graph final state is not an artifact
- graph final result is not automatically persisted as an artifact
- node output is not automatically persisted as an artifact
- tool output is not automatically persisted as an artifact
- event payloads are not automatically converted into artifacts

## Scope

- explicit artifact emission terminology
- logical artifact identity
- deterministic slot / occurrence policy
- caller-owned serialization
- bounded metadata contract
- required artifact failure policy
- future orchestration boundary

## Non-goals

- `ArtifactStore.put()` execution wiring
- graph execution integration
- Django projection
- EventSink artifact events
- batch or async persistence
- reconciliation
- retention

## Core types

- `ArtifactEmissionContext`
- `ArtifactEmissionRequest`
- `ArtifactIdentity`
- `ArtifactSlot`
- `ArtifactOccurrence`
- `ArtifactEmitter`

## Artifact definition

An artifact is an explicit, immutable, serialized output emitted by workflow, plugin, or application code.

It is not:

- graph internal state
- final graph state
- automatic final result output
- checkpoint state
- raw event payload
- pending write
- unbounded Python object

## Identity contract

Logical identity is:

- `run_id`
- `slot`
- `occurrence`

run_id + slot + occurrence

Rules:

- the caller issues the slot and occurrence
- the execution context injects `run_id`
- same run / same logical artifact -> same identity
- new run / rerun -> different identity
- attempt identifiers are not part of the default identity

## Slot contract

Slots are stable machine identifiers.

- lowercase ASCII
- digits and hyphen only
- non-empty
- bounded length
- not a path
- not a filename

Examples:

- `final-report`
- `summary`
- `generated-image`
- `export-001`

## Occurrence contract

Occurrences are caller-issued discriminators for multi-valued slots.

- optional for single-valued slots
- required when the same slot is emitted more than once
- deterministic
- bounded
- not derived from timestamp or process-local counters

Examples:

- `0001`
- `revenue-chart`

## Serialization boundary

Serialization is caller-owned.

caller-owned serialization

- `ArtifactEmissionRequest.body` is bytes
- the producer serializes domain objects before emission
- the store remains bytes-only
- the store does not choose a serializer
- `ArtifactStore.put` is still not connected to production execution

artifactstore.put is still not connected to production execution

## Metadata contract

Metadata is bounded logical JSON.

bounded logical json

Allowed:

- null
- bool
- int
- finite float
- string
- list
- mapping with string keys
- bounded logical JSON

Forbidden:

- bytes
- arbitrary objects
- NaN / Infinity
- secrets
- backend/root configuration

## Failure policy

Explicit artifacts are required by default.

- persistence failure should fail the execution
- silent drop is forbidden
- fallback to memory is forbidden

## Future orchestration boundary

Planned internal flow:

1. workflow / plugin / application emits `ArtifactEmissionRequest`
2. internal orchestrator validates identity and request equivalence
3. orchestrator constructs `ArtifactWriteRequest`
4. `ArtifactStore.put()` is called by package-runtime-owned orchestration

X2 fixes the emission contract only.

## Compatibility with current store contract

Mapping:

- `run_id` -> execution context
- `slot` / `occurrence` -> logical identity
- `body` -> artifact body bytes
- `content_type` -> serialization declaration
- `metadata` -> bounded logical metadata
- storage key -> internal orchestration concern

The current store protocol remains unchanged.
