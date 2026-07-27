"""Code-first protocol sufficiency inspection for ArtifactStore."""

from __future__ import annotations

import inspect
from typing import get_type_hints

from cobalt_wren.integrations.artifact.base import (
    ArtifactReadResult,
    ArtifactStore,
    ArtifactWriteRequest,
    StoredArtifact,
)


def test_artifact_store_protocol_is_body_aware() -> None:
    put_sig = inspect.signature(ArtifactStore.put)
    get_sig = inspect.signature(ArtifactStore.get)
    list_sig = inspect.signature(ArtifactStore.list_for_run)

    assert tuple(put_sig.parameters) == ('self', 'request')
    assert tuple(get_sig.parameters) == ('self', 'storage_key')
    assert tuple(list_sig.parameters) == ('self', 'run_id')

    put_hints = get_type_hints(ArtifactStore.put)
    get_hints = get_type_hints(ArtifactStore.get)
    list_hints = get_type_hints(ArtifactStore.list_for_run)

    assert put_hints['request'] is ArtifactWriteRequest
    assert put_hints['return'] is StoredArtifact
    assert get_hints['return'] == ArtifactReadResult | None
    assert list_hints['return'] == list[StoredArtifact]

    request_field_names = tuple(ArtifactWriteRequest.__dataclass_fields__)
    descriptor_field_names = tuple(StoredArtifact.__dataclass_fields__)
    read_field_names = tuple(ArtifactReadResult.__dataclass_fields__)

    assert request_field_names == ('run_id', 'storage_key', 'body', 'name', 'kind', 'content_type', 'metadata')
    assert descriptor_field_names == ('run_id', 'storage_key', 'name', 'kind', 'content_type', 'size', 'digest', 'metadata')
    assert read_field_names == ('artifact', 'body')
    assert ArtifactWriteRequest.__dataclass_fields__['body'].repr is False
    assert ArtifactWriteRequest.__dataclass_fields__['metadata'].repr is False
    assert ArtifactReadResult.__dataclass_fields__['body'].repr is False
    assert StoredArtifact.__dataclass_fields__['metadata'].repr is False
