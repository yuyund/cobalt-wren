"""Package engine workflow preparation tests."""

from __future__ import annotations

import pytest

from langgraph_automation.api.engine import EnginePreparedWorkflow, create_engine
from langgraph_automation.api.errors import RuntimeAssemblyError, PluginResolutionError


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
    engine = create_engine(_reference_config())

    prepared = engine.prepare_workflow("reference.llm_echo_summary")

    assert isinstance(prepared, EnginePreparedWorkflow)
    assert prepared.kind == "reference.llm_echo_summary"
    assert prepared.graph is not None
    assert type(prepared).__name__ == "EnginePreparedWorkflow"


def test_prepare_workflow_unknown_kind_raises_resolution_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    engine = create_engine(_reference_config())

    with pytest.raises(PluginResolutionError) as excinfo:
        engine.prepare_workflow("does.not.exist")

    assert excinfo.value.component == "workflow_preparer"
    assert excinfo.value.code == "WORKFLOW_PREPARATION_WORKFLOW_NOT_FOUND"


def test_prepare_workflow_missing_provider_requirement_raises_runtime_assembly_error() -> None:
    engine = create_engine({"version": 1, "environment": "test"})

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        engine.prepare_workflow("reference.llm_echo_summary")

    assert excinfo.value.code == "WORKFLOW_REQUIREMENT_MISSING"
    assert excinfo.value.component == "workflow_requirements"
