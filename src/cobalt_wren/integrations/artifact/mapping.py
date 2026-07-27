"""Internal artifact emission to store-write mapping helpers."""

from __future__ import annotations

from cobalt_wren.integrations.artifact.base import ArtifactWriteRequest

from .emission import (
    ArtifactEmissionContext,
    ArtifactEmissionRequest,
    build_artifact_identity,
    build_artifact_storage_key,
)

__all__ = ['build_artifact_write_request']


def build_artifact_write_request(
    *,
    context: ArtifactEmissionContext,
    request: ArtifactEmissionRequest,
) -> ArtifactWriteRequest:
    """Map an explicit emission request to a deterministic store request."""

    identity = build_artifact_identity(context=context, request=request)
    return ArtifactWriteRequest(
        run_id=identity.run_id,
        storage_key=build_artifact_storage_key(identity),
        body=request.body,
        name=identity.slot.value,
        kind='artifact',
        content_type=request.content_type,
        metadata=dict(request.metadata),
    )
