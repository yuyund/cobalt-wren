"""PostgreSQL durable checkpoint store."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from importlib import import_module
import json
from typing import Any, cast

from cobalt_wren.api.errors import (
    CheckpointConflictError,
    CheckpointIntegrityError,
    CheckpointPersistenceError,
)

from .base import (
    CheckpointReadResult,
    CheckpointStore,
    CheckpointWriteRequest,
    StoredCheckpoint,
    canonicalize_checkpoint_metadata,
    normalize_checkpoint_namespace,
    normalize_checkpoint_run_id,
)

_COMPONENT = "checkpoint_store"


class PostgresCheckpointStore(CheckpointStore):
    def __init__(
        self,
        dsn: str,
        *,
        table_name: str = "langgraph_automation_checkpoints",
        connection_factory: object | None = None,
    ) -> None:
        if not dsn.strip():
            raise ValueError("dsn is required")
        if not table_name.replace("_", "").isalnum():
            raise ValueError("table_name is invalid")
        self.dsn = dsn
        self.table_name = table_name
        if connection_factory is None:
            try:
                psycopg = import_module("psycopg")
            except ImportError as exc:
                raise CheckpointPersistenceError(
                    "PostgreSQL checkpoint backend requires psycopg.",
                    code="CHECKPOINT_STORE_DEPENDENCY_MISSING",
                    component=_COMPONENT,
                ) from exc
            connection_factory = getattr(psycopg, "connect")
        self._connect = connection_factory
        self.ensure_schema()

    def _connection(self):
        return self._connect(self.dsn)

    def ensure_schema(self) -> None:
        sql = f"""CREATE TABLE IF NOT EXISTS {self.table_name} (
            run_id TEXT NOT NULL,
            namespace TEXT NOT NULL,
            checkpoint_id TEXT NOT NULL,
            parent_checkpoint_id TEXT NULL,
            revision BIGINT NOT NULL,
            serializer_name TEXT NOT NULL,
            serializer_version INTEGER NOT NULL,
            content_type TEXT NOT NULL,
            body BYTEA NOT NULL,
            size BIGINT NOT NULL,
            digest TEXT NOT NULL,
            metadata JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (run_id, namespace, checkpoint_id),
            UNIQUE (run_id, namespace, revision)
        )"""
        with self._connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)

    @staticmethod
    def _digest(body: bytes) -> str:
        return f"sha256:{sha256(body).hexdigest()}"

    @staticmethod
    def _descriptor(row: tuple[object, ...]) -> StoredCheckpoint:
        metadata_value = row[10]
        if isinstance(metadata_value, str):
            metadata_value = json.loads(metadata_value)
        metadata = cast(dict[str, Any], metadata_value)
        parent_value = row[3]
        parent = None if parent_value is None else str(parent_value)
        return StoredCheckpoint(
            run_id=str(row[0]),
            checkpoint_namespace=str(row[1]),
            checkpoint_id=str(row[2]),
            parent_checkpoint_id=parent,
            revision=int(cast(int | str, row[4])),
            serializer_name=str(row[5]),
            serializer_version=int(cast(int | str, row[6])),
            content_type=str(row[7]),
            size=int(cast(int | str, row[8])),
            digest=str(row[9]),
            metadata=deepcopy(metadata),
        )

    def save(self, request: CheckpointWriteRequest) -> StoredCheckpoint:
        run_id = str(normalize_checkpoint_run_id(request.run_id))
        namespace = normalize_checkpoint_namespace(request.checkpoint_namespace)
        with self._connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"SELECT run_id, namespace, checkpoint_id, parent_checkpoint_id, revision, serializer_name, serializer_version, content_type, size, digest, metadata, body FROM {self.table_name} WHERE run_id=%s AND namespace=%s AND checkpoint_id=%s FOR UPDATE",
                    (run_id, namespace, request.checkpoint_id),
                )
                existing = cursor.fetchone()
                if existing is not None:
                    descriptor = self._descriptor(existing[:11])
                    body = bytes(existing[11])
                    same = (
                        descriptor.parent_checkpoint_id == request.parent_checkpoint_id
                        and body == request.body
                        and descriptor.serializer_name == request.serializer_name
                        and descriptor.serializer_version == request.serializer_version
                        and descriptor.content_type == request.content_type
                        and canonicalize_checkpoint_metadata(descriptor.metadata)
                        == canonicalize_checkpoint_metadata(request.metadata)
                    )
                    if same:
                        return descriptor
                    raise CheckpointConflictError(
                        "Checkpoint identity conflicts with an existing immutable version.",
                        code="CHECKPOINT_STORE_CONFLICT",
                        component=_COMPONENT,
                    )
                cursor.execute(
                    f"SELECT checkpoint_id, revision FROM {self.table_name} WHERE run_id=%s AND namespace=%s ORDER BY revision DESC LIMIT 1 FOR UPDATE",
                    (run_id, namespace),
                )
                head = cursor.fetchone()
                if head is None:
                    if request.parent_checkpoint_id is not None:
                        raise CheckpointConflictError(
                            "Checkpoint write conflicts with the current stream head.",
                            code="CHECKPOINT_STORE_STALE_PARENT",
                            component=_COMPONENT,
                        )
                    revision = 1
                else:
                    if request.parent_checkpoint_id != head[0]:
                        raise CheckpointConflictError(
                            "Checkpoint write conflicts with the current stream head.",
                            code="CHECKPOINT_STORE_STALE_PARENT",
                            component=_COMPONENT,
                        )
                    revision = int(head[1]) + 1
                digest = self._digest(request.body)
                cursor.execute(
                    f"INSERT INTO {self.table_name} (run_id, namespace, checkpoint_id, parent_checkpoint_id, revision, serializer_name, serializer_version, content_type, body, size, digest, metadata) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        run_id,
                        namespace,
                        request.checkpoint_id,
                        request.parent_checkpoint_id,
                        revision,
                        request.serializer_name,
                        request.serializer_version,
                        request.content_type,
                        request.body,
                        len(request.body),
                        digest,
                        json.dumps(dict(request.metadata)),
                    ),
                )
                return StoredCheckpoint(
                    run_id=request.run_id,
                    checkpoint_namespace=namespace,
                    checkpoint_id=request.checkpoint_id,
                    parent_checkpoint_id=request.parent_checkpoint_id,
                    revision=revision,
                    serializer_name=request.serializer_name,
                    serializer_version=request.serializer_version,
                    content_type=request.content_type,
                    size=len(request.body),
                    digest=digest,
                    metadata=deepcopy(dict(request.metadata)),
                )

    def _load(
        self, run_id: int | str, namespace: str, where: str, params: tuple[object, ...]
    ) -> CheckpointReadResult | None:
        normalized_run = str(normalize_checkpoint_run_id(run_id))
        normalized_namespace = normalize_checkpoint_namespace(namespace)
        with self._connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"SELECT run_id, namespace, checkpoint_id, parent_checkpoint_id, revision, serializer_name, serializer_version, content_type, size, digest, metadata, body FROM {self.table_name} WHERE run_id=%s AND namespace=%s AND {where}",
                    (normalized_run, normalized_namespace, *params),
                )
                row = cursor.fetchone()
        if row is None:
            return None
        descriptor = self._descriptor(row[:11])
        body = bytes(row[11])
        if descriptor.size != len(body) or descriptor.digest != self._digest(body):
            raise CheckpointIntegrityError(
                "Checkpoint store detected an integrity failure.",
                code="CHECKPOINT_STORE_INTEGRITY_FAILURE",
                component=_COMPONENT,
            )
        return CheckpointReadResult(checkpoint=descriptor, body=body)

    def load_latest(
        self, run_id: int | str, *, checkpoint_namespace: str = ""
    ) -> CheckpointReadResult | None:
        return self._load(
            run_id, checkpoint_namespace, "TRUE ORDER BY revision DESC LIMIT 1", ()
        )

    def load_checkpoint(
        self, run_id: int | str, checkpoint_id: str, *, checkpoint_namespace: str = ""
    ) -> CheckpointReadResult | None:
        return self._load(
            run_id, checkpoint_namespace, "checkpoint_id=%s", (checkpoint_id,)
        )

    def list_for_run(
        self, run_id: int | str, *, checkpoint_namespace: str = ""
    ) -> list[StoredCheckpoint]:
        normalized_run = str(normalize_checkpoint_run_id(run_id))
        normalized_namespace = normalize_checkpoint_namespace(checkpoint_namespace)
        with self._connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"SELECT run_id, namespace, checkpoint_id, parent_checkpoint_id, revision, serializer_name, serializer_version, content_type, size, digest, metadata FROM {self.table_name} WHERE run_id=%s AND namespace=%s ORDER BY revision",
                    (normalized_run, normalized_namespace),
                )
                rows = cursor.fetchall()
        return [self._descriptor(row) for row in rows]
