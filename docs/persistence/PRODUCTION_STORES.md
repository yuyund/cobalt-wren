---
type: guide
status: current
authority: explanatory
summary: S3-compatible artifact storage and PostgreSQL checkpoint storage for shared production deployments.
code_refs:
  - src/cobalt_wren/integrations/artifact/s3_store.py
  - src/cobalt_wren/integrations/checkpoint/postgres_store.py
  - src/cobalt_wren/config/artifact_store.py
  - src/cobalt_wren/config/checkpoint_store.py
  - src/cobalt_wren/config/models.py
  - src/cobalt_wren/runtime/artifact_store.py
  - src/cobalt_wren/runtime/checkpoint_store.py
  - pyproject.toml
test_refs:
  - tests/contract/persistence/test_persistence_backend_registration.py
  - tests/support/persistence/backends.py
  - tests/unit/integrations/test_s3_artifact_store.py
  - tests/unit/config/test_production_store_config.py
verified:
  date: 2026-07-23
  commit: WORKTREE
  base_commit: 4251cb4
  method:
    - code-and-test-review
---
# Production Stores

The built-in production artifact backend is `s3`, compatible with AWS S3 and endpoint-configurable S3 implementations. Descriptor metadata, digest, size, idempotent immutable writes, body integrity verification, and Run listing retain the public ArtifactStore contract. Install the `s3` optional dependency.

The built-in shared checkpoint backend is `postgres`. It uses immutable `(run_id, namespace, checkpoint_id)` identities, monotonically increasing stream revisions, row locking for head comparison, stale-parent rejection, body digest verification, and JSONB metadata. The table is created idempotently at backend initialization. PostgreSQL credentials belong in deployment configuration supplied through protected environment or file handling.
