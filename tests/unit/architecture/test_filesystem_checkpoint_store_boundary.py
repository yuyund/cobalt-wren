"""Architecture guards for the filesystem checkpoint backend."""

from __future__ import annotations

from pathlib import Path

from tests.support.import_scan import collect_import_targets


def test_filesystem_checkpoint_store_does_not_import_django_or_app_layers() -> None:
    targets = collect_import_targets(Path('src/cobalt_wren/integrations/checkpoint/filesystem_store.py'))
    offenders = [
        target
        for target in targets
        if target.startswith(
            (
                'django',
                'cobalt_wren.apps.automation',
                'cobalt_wren.graphs',
                'cobalt_wren.workflows',
                'cobalt_wren.runtime.assembly',
                'cobalt_wren.config',
                'cobalt_wren.integrations.artifact',
                'cobalt_wren.api.stores',
            )
        )
    ]
    assert offenders == []


def test_api_stores_does_not_export_filesystem_checkpoint_store() -> None:
    import cobalt_wren.api.stores as stores_api

    assert 'FilesystemCheckpointStore' not in stores_api.__all__
    assert not hasattr(stores_api, 'FilesystemCheckpointStore')
