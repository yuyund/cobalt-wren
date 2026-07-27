"""S3-compatible durable artifact store."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from importlib import import_module
import json
from typing import Any

from cobalt_wren.api.errors import (
    ArtifactConflictError,
    ArtifactIntegrityError,
    ArtifactPersistenceError,
    ArtifactValidationError,
)

from .base import (
    ArtifactReadResult,
    ArtifactStore,
    ArtifactWriteRequest,
    StoredArtifact,
    normalize_artifact_run_id,
    normalize_artifact_storage_key,
)

_COMPONENT = "artifact_store"
_METADATA_KEY = "langgraph-automation-descriptor"


class S3ArtifactStore(ArtifactStore):
    def __init__(
        self,
        *,
        bucket: str,
        prefix: str = "",
        endpoint_url: str | None = None,
        region_name: str | None = None,
        client: object | None = None,
    ) -> None:
        if not bucket.strip():
            raise ValueError("bucket is required")
        self.bucket = bucket.strip()
        self.prefix = prefix.strip("/")
        if client is None:
            try:
                boto3 = import_module("boto3")
            except ImportError as exc:
                raise ArtifactPersistenceError(
                    "S3 artifact backend requires the 's3' optional dependency.",
                    code="ARTIFACT_STORE_DEPENDENCY_MISSING",
                    component=_COMPONENT,
                ) from exc
            client = boto3.client(
                "s3", endpoint_url=endpoint_url, region_name=region_name
            )
        self._client = client

    def _key(self, storage_key: str) -> str:
        normalized = normalize_artifact_storage_key(storage_key)
        return f"{self.prefix}/{normalized}" if self.prefix else normalized

    @staticmethod
    def _descriptor(request: ArtifactWriteRequest) -> StoredArtifact:
        digest = f"sha256:{sha256(request.body).hexdigest()}"
        return StoredArtifact(
            run_id=request.run_id,
            storage_key=request.storage_key,
            name=request.name,
            kind=request.kind,
            content_type=request.content_type,
            size=len(request.body),
            digest=digest,
            metadata=deepcopy(request.metadata),
        )

    @staticmethod
    def _serialize(artifact: StoredArtifact) -> str:
        return json.dumps(
            {
                "run_id": artifact.run_id,
                "storage_key": artifact.storage_key,
                "name": artifact.name,
                "kind": artifact.kind,
                "content_type": artifact.content_type,
                "size": artifact.size,
                "digest": artifact.digest,
                "metadata": dict(artifact.metadata),
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _deserialize(value: str) -> StoredArtifact:
        raw = json.loads(value)
        return StoredArtifact(
            run_id=raw["run_id"],
            storage_key=raw["storage_key"],
            name=raw["name"],
            kind=raw["kind"],
            content_type=raw["content_type"],
            size=raw["size"],
            digest=raw["digest"],
            metadata=raw.get("metadata", {}),
        )

    def put(self, request: ArtifactWriteRequest) -> StoredArtifact:
        if not isinstance(request, ArtifactWriteRequest):
            raise TypeError("request must be an ArtifactWriteRequest")
        try:
            key = self._key(request.storage_key)
        except ValueError as exc:
            raise ArtifactValidationError(
                "Artifact store rejected an invalid storage key.",
                code="ARTIFACT_STORE_INVALID_STORAGE_KEY",
                component=_COMPONENT,
            ) from exc
        candidate = self._descriptor(request)
        existing = self.get(request.storage_key)
        if existing is not None:
            if existing.artifact == candidate and existing.body == request.body:
                return existing.artifact
            raise ArtifactConflictError(
                "Artifact store rejected a conflicting write request.",
                code="ARTIFACT_STORE_CONFLICT",
                component=_COMPONENT,
                metadata={"storage_key": request.storage_key},
            )
        metadata = {_METADATA_KEY: self._serialize(candidate)}
        try:
            getattr(self._client, "put_object")(
                Bucket=self.bucket,
                Key=key,
                Body=request.body,
                ContentType=request.content_type or "application/octet-stream",
                Metadata=metadata,
                IfNoneMatch="*",
            )
        except Exception as exc:
            if "Precondition" in type(exc).__name__ or "412" in str(exc):
                raise ArtifactConflictError(
                    "Artifact store rejected a conflicting write request.",
                    code="ARTIFACT_STORE_CONFLICT",
                    component=_COMPONENT,
                ) from exc
            raise ArtifactPersistenceError(
                "Artifact store could not persist the artifact.",
                code="ARTIFACT_STORE_PERSISTENCE_FAILURE",
                component=_COMPONENT,
            ) from exc
        return candidate

    def get(self, storage_key: str) -> ArtifactReadResult | None:
        try:
            key = self._key(storage_key)
            response = getattr(self._client, "get_object")(Bucket=self.bucket, Key=key)
        except ValueError as exc:
            raise ArtifactValidationError(
                "Artifact store rejected an invalid storage key.",
                code="ARTIFACT_STORE_INVALID_STORAGE_KEY",
                component=_COMPONENT,
            ) from exc
        except Exception as exc:
            if "NoSuchKey" in type(exc).__name__ or "404" in str(exc):
                return None
            raise ArtifactPersistenceError(
                "Artifact store could not read the artifact.",
                code="ARTIFACT_STORE_PERSISTENCE_FAILURE",
                component=_COMPONENT,
            ) from exc
        metadata = response.get("Metadata", {})
        descriptor_raw = metadata.get(_METADATA_KEY)
        if not isinstance(descriptor_raw, str):
            raise ArtifactIntegrityError(
                "Artifact store detected an integrity failure.",
                code="ARTIFACT_STORE_INTEGRITY_FAILURE",
                component=_COMPONENT,
            )
        descriptor = self._deserialize(descriptor_raw)
        body_obj = response["Body"]
        body = body_obj.read() if hasattr(body_obj, "read") else bytes(body_obj)
        digest = f"sha256:{sha256(body).hexdigest()}"
        if descriptor.size != len(body) or descriptor.digest != digest:
            raise ArtifactIntegrityError(
                "Artifact store detected an integrity failure.",
                code="ARTIFACT_STORE_INTEGRITY_FAILURE",
                component=_COMPONENT,
            )
        return ArtifactReadResult(artifact=descriptor, body=body)

    def list_for_run(self, run_id: int | str) -> list[StoredArtifact]:
        normalized = normalize_artifact_run_id(run_id)
        prefix = f"{self.prefix}/" if self.prefix else ""
        token: str | None = None
        result: list[StoredArtifact] = []
        while True:
            kwargs: dict[str, Any] = {"Bucket": self.bucket, "Prefix": prefix}
            if token:
                kwargs["ContinuationToken"] = token
            response = getattr(self._client, "list_objects_v2")(**kwargs)
            for item in response.get("Contents", []):
                key = item["Key"]
                storage_key = key[len(prefix) :] if prefix else key
                found = self.get(storage_key)
                if found is not None and found.artifact.run_id == normalized:
                    result.append(found.artifact)
            if not response.get("IsTruncated"):
                break
            token = response.get("NextContinuationToken")
        result.sort(key=lambda item: item.storage_key)
        return result
