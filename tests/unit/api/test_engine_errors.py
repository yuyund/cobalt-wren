"""Engine safe failure behavior tests."""

from __future__ import annotations

import pytest

from cobalt_wren.api.engine import create_engine
from cobalt_wren.api.errors import RuntimeAssemblyError
from tests.support.native_workflow_fixtures import (
    TEST_NATIVE_WORKFLOW_KIND,
    create_test_native_plugin,
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


def test_create_engine_wraps_arbitrary_runtime_failures_without_leaking_raw_message(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*args, **kwargs):
        raise ValueError("password=secret-value")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("cobalt_wren.api.engine.RuntimeAssembler.assemble", boom)

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        create_engine(_reference_config())

    assert excinfo.value.code == "ENGINE_CREATE_FAILED"
    assert "secret-value" not in excinfo.value.safe_message
    assert "secret-value" not in str(excinfo.value.metadata)


def test_prepare_workflow_wraps_arbitrary_failures_without_leaking_raw_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    engine = create_engine(
        _reference_config(),
        plugins=(create_test_native_plugin(),),
        discover_plugins=False,
    )

    def boom(*args, **kwargs):
        raise ValueError("password=secret-value")

    monkeypatch.setattr("cobalt_wren.api.engine.WorkflowPreparer.prepare", boom)

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        engine.prepare_workflow(TEST_NATIVE_WORKFLOW_KIND)

    assert excinfo.value.code == "ENGINE_WORKFLOW_PREPARATION_FAILED"
    assert "secret-value" not in excinfo.value.safe_message
    assert "secret-value" not in str(excinfo.value.metadata)
