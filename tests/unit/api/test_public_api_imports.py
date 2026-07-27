"""Public API facade import coverage."""

from __future__ import annotations


def test_llm_api_exports() -> None:
    from cobalt_wren.api.llm import LLMClient, LLMRequest, LLMResult

    assert LLMClient is not None
    assert LLMRequest is not None
    assert LLMResult is not None


def test_llm_api_all() -> None:
    import cobalt_wren.api.llm as llm_api

    assert set(llm_api.__all__) == {'LLMClient', 'LLMRequest', 'LLMResult'}


def test_tool_api_exports() -> None:
    from cobalt_wren.api.tools import ToolPolicy, ToolPolicyContext, ToolPolicyDecision, ToolRegistry, ToolResult

    assert ToolRegistry is not None
    assert ToolResult is not None
    assert ToolPolicy is not None
    assert ToolPolicyContext is not None
    assert ToolPolicyDecision is not None


def test_tool_api_all() -> None:
    import cobalt_wren.api.tools as tools_api

    assert set(tools_api.__all__) == {'ToolRegistry', 'ToolResult', 'ToolPolicy', 'ToolPolicyContext', 'ToolPolicyDecision'}


def test_store_api_exports() -> None:
    from cobalt_wren.api.stores import (
        ArtifactReadResult,
        ArtifactStore,
        ArtifactWriteRequest,
        CheckpointReadResult,
        CheckpointStore,
        CheckpointWriteRequest,
        StoredArtifact,
        StoredCheckpoint,
    )

    assert ArtifactStore is not None
    assert ArtifactWriteRequest is not None
    assert StoredArtifact is not None
    assert ArtifactReadResult is not None
    assert CheckpointStore is not None
    assert CheckpointWriteRequest is not None
    assert StoredCheckpoint is not None
    assert CheckpointReadResult is not None


def test_store_api_does_not_export_concrete_backends() -> None:
    import cobalt_wren.api.stores as stores_api

    assert 'FilesystemArtifactStore' not in stores_api.__all__
    assert 'FilesystemCheckpointStore' not in stores_api.__all__
    assert not hasattr(stores_api, 'FilesystemArtifactStore')
    assert not hasattr(stores_api, 'FilesystemCheckpointStore')


def test_store_api_all() -> None:
    import cobalt_wren.api.stores as stores_api

    assert set(stores_api.__all__) == {
        'ArtifactStore',
        'ArtifactWriteRequest',
        'StoredArtifact',
        'ArtifactReadResult',
        'CheckpointStore',
        'CheckpointWriteRequest',
        'StoredCheckpoint',
        'CheckpointReadResult',
    }


def test_checkpoint_public_api_is_bounded_to_facades() -> None:
    import cobalt_wren as package_root
    import cobalt_wren.api as api_package
    import cobalt_wren.integrations.checkpoint as checkpoint_integration

    assert not hasattr(package_root, 'CheckpointStore')
    assert not hasattr(package_root, 'CheckpointWriteRequest')
    assert not hasattr(package_root, 'StoredCheckpoint')
    assert not hasattr(package_root, 'CheckpointReadResult')
    assert not hasattr(package_root, 'FilesystemCheckpointStore')
    assert not hasattr(api_package, 'CheckpointStore')
    assert not hasattr(api_package, 'CheckpointWriteRequest')
    assert not hasattr(api_package, 'StoredCheckpoint')
    assert not hasattr(api_package, 'CheckpointReadResult')
    assert not hasattr(api_package, 'FilesystemCheckpointStore')
    assert checkpoint_integration.FilesystemCheckpointStore is not None
    assert checkpoint_integration.MemoryCheckpointStore is not None
    assert checkpoint_integration.CheckpointStore is not None
    assert checkpoint_integration.CheckpointWriteRequest is not None
    assert checkpoint_integration.StoredCheckpoint is not None
    assert checkpoint_integration.CheckpointReadResult is not None


def test_event_api_exports() -> None:
    from cobalt_wren.api.events import EventSink

    assert EventSink is not None


def test_event_api_all() -> None:
    import cobalt_wren.api.events as events_api

    assert set(events_api.__all__) == {'EventSink'}


def test_artifact_emission_contract_is_not_public_api() -> None:
    import cobalt_wren as package_root
    import cobalt_wren.api as api_package
    import cobalt_wren.api.stores as stores_api
    import cobalt_wren.api.plugins as plugins_api

    assert not hasattr(package_root, 'ArtifactEmissionRequest')
    assert not hasattr(package_root, 'ArtifactIdentity')
    assert not hasattr(package_root, 'ArtifactSlot')
    assert not hasattr(package_root, 'ArtifactOccurrence')
    assert not hasattr(api_package, 'ArtifactEmissionRequest')
    assert not hasattr(api_package, 'ArtifactIdentity')
    assert not hasattr(api_package, 'ArtifactSlot')
    assert not hasattr(api_package, 'ArtifactOccurrence')
    assert not hasattr(stores_api, 'ArtifactEmissionRequest')
    assert not hasattr(stores_api, 'ArtifactIdentity')
    assert not hasattr(stores_api, 'ArtifactSlot')
    assert not hasattr(stores_api, 'ArtifactOccurrence')
    assert not hasattr(plugins_api, 'ArtifactEmissionRequest')
    assert not hasattr(plugins_api, 'ArtifactIdentity')
    assert not hasattr(plugins_api, 'ArtifactSlot')
    assert not hasattr(plugins_api, 'ArtifactOccurrence')
    assert 'ArtifactEmissionRequest' not in getattr(api_package, '__all__', [])
