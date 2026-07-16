"""Code-first protocol sufficiency inspection for ArtifactStore."""

from __future__ import annotations

import inspect
from typing import get_type_hints

from langgraph_automation.integrations.artifact.base import ArtifactStore, ArtifactWriteResult


def test_artifact_store_protocol_is_metadata_only() -> None:
    put_sig = inspect.signature(ArtifactStore.put)
    get_sig = inspect.signature(ArtifactStore.get)
    list_sig = inspect.signature(ArtifactStore.list_for_run)

    assert tuple(put_sig.parameters) == ('self', 'artifact')
    assert tuple(get_sig.parameters) == ('self', 'artifact_id')
    assert tuple(list_sig.parameters) == ('self', 'run_id')

    put_hints = get_type_hints(ArtifactStore.put)
    get_hints = get_type_hints(ArtifactStore.get)
    list_hints = get_type_hints(ArtifactStore.list_for_run)

    assert put_hints['artifact'] is ArtifactWriteResult
    assert put_hints['return'] is ArtifactWriteResult
    assert get_hints['return'] == ArtifactWriteResult | None
    assert list_hints['return'] == list[ArtifactWriteResult]

    field_names = tuple(ArtifactWriteResult.__dataclass_fields__)
    assert field_names == ('storage_key', 'name', 'kind', 'content_type', 'size', 'metadata')
    assert 'body' not in field_names
    assert 'content' not in field_names

