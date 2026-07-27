"""Package engine facade smoke tests."""

from __future__ import annotations

import pytest

from cobalt_wren.api.engine import AutomationEngine, EnginePreparedWorkflow, create_engine
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
def test_api_engine_headless_prepare_does_not_execute_provider_or_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"provider": 0, "tool": 0}

    def forbid_completion(*args, **kwargs):
        calls["provider"] += 1
        raise AssertionError("provider network call should not happen during preparation")

    def forbid_tool_call(self, **kwargs):
        calls["tool"] += 1
        raise AssertionError("tool execution should not happen during preparation")

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("litellm.completion", forbid_completion)
    monkeypatch.setattr("cobalt_wren.integrations.tools.safe_tools.EchoTool.__call__", forbid_tool_call)

    engine = create_engine(
        _reference_config(),
        plugins=(create_required_native_plugin(),),
        discover_plugins=False,
    )
    assert isinstance(engine, AutomationEngine)

    prepared = engine.prepare_workflow(TEST_REQUIRED_WORKFLOW_KIND)

    assert isinstance(prepared, EnginePreparedWorkflow)
    assert prepared.kind == TEST_REQUIRED_WORKFLOW_KIND
    assert prepared.executable is not None
    assert calls == {"provider": 0, "tool": 0}
