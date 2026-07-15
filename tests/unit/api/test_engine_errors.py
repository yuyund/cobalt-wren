"""Engine safe failure behavior tests."""

from __future__ import annotations

import pytest

from langgraph_automation.api.engine import create_engine
from langgraph_automation.api.errors import RuntimeAssemblyError


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


def test_create_engine_wraps_arbitrary_runtime_failures_without_leaking_raw_message(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args, **kwargs):
        raise ValueError("password=secret-value")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("langgraph_automation.api.engine.RuntimeAssembler.assemble", boom)

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        create_engine(_reference_config())

    assert excinfo.value.code == "ENGINE_CREATE_FAILED"
    assert "secret-value" not in excinfo.value.safe_message
    assert "secret-value" not in str(excinfo.value.metadata)


def test_prepare_workflow_wraps_arbitrary_failures_without_leaking_raw_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    engine = create_engine(_reference_config())

    def boom(*args, **kwargs):
        raise ValueError("password=secret-value")

    monkeypatch.setattr("langgraph_automation.api.engine.WorkflowPreparer.prepare", boom)

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        engine.prepare_workflow("reference.llm_echo_summary")

    assert excinfo.value.code == "ENGINE_WORKFLOW_PREPARATION_FAILED"
    assert "secret-value" not in excinfo.value.safe_message
    assert "secret-value" not in str(excinfo.value.metadata)
