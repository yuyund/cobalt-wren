"""Architecture guards for the explicit artifact emission contract."""

from __future__ import annotations

from pathlib import Path

from tests.support.import_scan import collect_import_targets


def test_artifact_emission_module_does_not_import_concrete_stores_or_django() -> None:
    targets = collect_import_targets(Path('src/cobalt_wren/integrations/artifact/emission.py'))

    offenders = [
        target
        for target in targets
        if target.startswith(
            (
                'django',
                'cobalt_wren.apps.automation',
                'cobalt_wren.graphs',
                'cobalt_wren.runtime.assembly',
                'cobalt_wren.integrations.artifact.memory_store',
                'cobalt_wren.integrations.artifact.filesystem_store',
            )
        )
    ]
    assert offenders == []


def test_artifact_emission_module_stays_free_of_store_call_sites() -> None:
    text = Path('src/cobalt_wren/integrations/artifact/emission.py').read_text()

    for token in (
        'ArtifactStore(',
        'MemoryArtifactStore(',
        'FilesystemArtifactStore(',
        'build_artifact_store(',
        'build_checkpoint_store(',
        'transaction.atomic',
    ):
        assert token not in text


def test_artifact_emission_contract_is_not_publicly_reexported() -> None:
    import cobalt_wren as package_root
    import cobalt_wren.api as api_package
    import cobalt_wren.api.stores as stores_api
    import cobalt_wren.api.plugins as plugins_api

    for module in (package_root, api_package, stores_api, plugins_api):
        assert not hasattr(module, 'ArtifactEmissionRequest')
        assert not hasattr(module, 'ArtifactIdentity')
        assert not hasattr(module, 'ArtifactSlot')
        assert not hasattr(module, 'ArtifactOccurrence')
