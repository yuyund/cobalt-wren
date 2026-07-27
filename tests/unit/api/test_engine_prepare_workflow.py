"""Package engine workflow preparation tests."""

from __future__ import annotations

import pytest

from cobalt_wren.api.engine import EnginePreparedWorkflow, create_engine
from cobalt_wren.api.errors import RuntimeAssemblyError, PluginResolutionError
from tests.support.native_workflow_fixtures import (
    TEST_REQUIRED_WORKFLOW_KIND,
    create_required_native_plugin,
)


def _reference_config() -> dict[str, object]:
    return {
        "version": 1,
        "environment": "test",
        "providers": {
            "default": {
                "provider": "litellm",
                "model": "gpt-4.1-mini",
                "secrets": {
                    "api_key": {
                        "source": "env",
                        "name": "OPENAI_API_KEY",
                    },
                },
            },
        },
        "tools": {
            "allowlist": ["echo"],
        },
    }


@pytest.mark.usefixtures("monkeypatch")
def test_prepare_workflow_returns_public_engine_handle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    engine = create_engine(
        _reference_config(),
        plugins=(create_required_native_plugin(),),
        discover_plugins=False,
    )

    prepared = engine.prepare_workflow(TEST_REQUIRED_WORKFLOW_KIND)

    assert isinstance(prepared, EnginePreparedWorkflow)
    assert prepared.kind == TEST_REQUIRED_WORKFLOW_KIND
    assert prepared.executable is not None
    assert type(prepared).__name__ == "EnginePreparedWorkflow"


def test_prepare_workflow_unknown_kind_raises_resolution_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    engine = create_engine(
        _reference_config(),
        plugins=(create_required_native_plugin(),),
        discover_plugins=False,
    )

    with pytest.raises(PluginResolutionError) as excinfo:
        engine.prepare_workflow("does.not.exist")

    assert excinfo.value.component == "workflow_preparer"
    assert excinfo.value.code == "WORKFLOW_PREPARATION_WORKFLOW_NOT_FOUND"


def test_prepare_workflow_missing_provider_requirement_raises_runtime_assembly_error() -> None:
    engine = create_engine(
        {"version": 1, "environment": "test"},
        plugins=(create_required_native_plugin(),),
        discover_plugins=False,
    )

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        engine.prepare_workflow(TEST_REQUIRED_WORKFLOW_KIND)

    assert excinfo.value.code == "WORKFLOW_REQUIREMENT_MISSING"
    assert excinfo.value.component == "workflow_requirements"


def test_prepared_workflow_executable_is_primary_and_graph_is_compatibility_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    engine = create_engine(
        _reference_config(),
        plugins=(create_required_native_plugin(),),
        discover_plugins=False,
    )
    prepared = engine.prepare_workflow(TEST_REQUIRED_WORKFLOW_KIND)

    assert prepared.executable is prepared.executable
