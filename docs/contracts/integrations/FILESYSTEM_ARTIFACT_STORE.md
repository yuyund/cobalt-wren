# Filesystem Artifact Store Contract

`FilesystemArtifactStore` is the first durable artifact backend.
It is process-durable, immutable, idempotent, conflict-aware, and integrity-verifying.

## Purpose

- provide durable artifact body storage for a single host and shared filesystem root
- preserve the separation between artifact body plane and control-plane metadata plane
- support restart-safe reads without introducing Django orchestration or runtime backend selection

## Storage Model

- body path is derived from `sha256(body)`
- record path is derived from `sha256(normalized_storage_key)`
- user-controlled storage keys are never concatenated directly into filesystem paths
- body publication uses hard-link no-overwrite publication
- manifest publication uses a deterministic JSON manifest

## Manifest Contract

- schema version is `1`
- manifest stores `run_id`, `storage_key`, `name`, `kind`, `content_type`, `size`, `digest`, and normalized `metadata`
- manifest never stores the raw body, absolute root path, temporary path, or credentials
- manifest encoding is deterministic JSON with sorted keys and bounded size
- duplicate JSON keys, unsupported schema versions, and noncanonical manifests are integrity failures

## Write Contract

- write flow is body-first, manifest-second
- same-request retry is idempotent
- same key plus different canonical request is a conflict
- same key plus corrupt existing body or manifest is an integrity failure
- same host and same root may be shared across multiple store instances

## Read Contract

- `get()` performs full body integrity verification
- `list_for_run()` scans manifests, verifies manifest integrity, checks body existence, symlink/non-regular status, and manifest/body size equality, then returns descriptors only
- `list_for_run()` does not read full body bytes or digest-verify artifact content
- missing manifest returns `None`
- dangling manifest or body corruption raises `ArtifactIntegrityError`

## Durability

- durability level is `PROCESS_DURABLE`
- restart or store recreation on the same host and root must preserve reads
- multi-host durability is deferred
- deployment durability is not claimed

## Errors

- validation failures are safe and redaction-aware
- filesystem I/O failures raise `ArtifactPersistenceError`
- corruption and integrity mismatches raise `ArtifactIntegrityError`
- same-key write conflicts raise `ArtifactConflictError`

## Deferred Work

- explicit artifact emission and orchestration
- runtime backend selection is deferred
- Django orchestration is deferred
- body/metadata orchestration is deferred
- reconciliation / garbage collection is deferred
- durable checkpoint storage is deferred
