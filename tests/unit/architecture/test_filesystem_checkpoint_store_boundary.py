"""Architecture guards for the filesystem checkpoint backend."""

from __future__ import annotations

from pathlib import Path

from tests.support.import_scan import collect_import_targets


def test_filesystem_checkpoint_store_does_not_import_django_or_app_layers() -> None:
    targets = collect_import_targets(Path('src/langgraph_automation/integrations/checkpoint/filesystem_store.py'))
    offenders = [
        target
        for target in targets
        if target.startswith(
            (
                'django',
                'langgraph_automation.apps.automation',
                'langgraph_automation.graphs',
                'langgraph_automation.workflows',
                'langgraph_automation.runtime.assembly',
                'langgraph_automation.config',
                'langgraph_automation.integrations.artifact',
                'langgraph_automation.api.stores',
            )
        )
    ]
    assert offenders == []


def test_api_stores_does_not_export_filesystem_checkpoint_store() -> None:
    import langgraph_automation.api.stores as stores_api

    assert 'FilesystemCheckpointStore' not in stores_api.__all__
    assert not hasattr(stores_api, 'FilesystemCheckpointStore')
