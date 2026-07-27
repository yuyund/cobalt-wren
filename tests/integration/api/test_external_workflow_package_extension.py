"""External workflow package extension tests through the public engine facade."""

from __future__ import annotations

import pytest

from cobalt_wren.api.engine import EnginePreparedWorkflow, create_engine
from cobalt_wren.api.errors import RuntimeAssemblyError
from cobalt_wren.api.workflow import WorkflowRequirements
from tests.external_packages.acme_workflows import (
    EXTERNAL_WORKFLOW_KIND,
    ExternalGraph,
    create_plugin,
)


def _minimal_config() -> dict[str, object]:
    return {"version": 1, "environment": "test"}


def test_external_workflow_prepares_without_foundation_or_control_plane_registration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"build": 0, "provider": 0, "tool": 0}

    def record_build() -> None:
        calls["build"] += 1

    def forbid_provider(*args: object, **kwargs: object) -> object:
        del args, kwargs
        calls["provider"] += 1
        raise AssertionError("provider execution must not occur during workflow preparation")

    def forbid_tool(self: object, **kwargs: object) -> object:
        del self, kwargs
        calls["tool"] += 1
        raise AssertionError("tool execution must not occur during workflow preparation")

    monkeypatch.setattr("litellm.completion", forbid_provider)
    monkeypatch.setattr("cobalt_wren.integrations.tools.safe_tools.EchoTool.__call__", forbid_tool)

    plugin = create_plugin(on_build=record_build)
    engine = create_engine(_minimal_config(), plugins=(plugin,))

    prepared = engine.prepare_workflow(EXTERNAL_WORKFLOW_KIND)

    assert isinstance(prepared, EnginePreparedWorkflow)
    assert prepared.kind == EXTERNAL_WORKFLOW_KIND
    assert prepared.executable == ExternalGraph(workflow_kind=EXTERNAL_WORKFLOW_KIND)
    assert calls == {"build": 1, "provider": 0, "tool": 0}


def test_external_workflow_requirements_fail_before_external_build() -> None:
    build_calls = 0

    def record_build() -> None:
        nonlocal build_calls
        build_calls += 1

    plugin = create_plugin(
        on_build=record_build,
        requirements=WorkflowRequirements(provider_profiles=("external-profile",)),
    )
    engine = create_engine(_minimal_config(), plugins=(plugin,))

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        engine.prepare_workflow(EXTERNAL_WORKFLOW_KIND)

    assert excinfo.value.code == "WORKFLOW_REQUIREMENT_MISSING"
    assert excinfo.value.component == "workflow_requirements"
    assert excinfo.value.metadata == {
        "requirement_type": "provider_profile",
        "requirement_name": "external-profile",
        "workflow_stage": "requirements",
    }
    assert build_calls == 0


def test_external_workflow_receives_opaque_config_and_executes() -> None:
    engine = create_engine(_minimal_config(), plugins=(create_plugin(),))

    prepared = engine.prepare_workflow(EXTERNAL_WORKFLOW_KIND, config={"prefix": "custom"})
    result = prepared.execute({"request_id": "REQ-7"})

    assert result.output == {"status": "accepted", "message": "custom:REQ-7"}


def test_external_workflow_can_use_replaced_provider_and_tool_adapters() -> None:
    from cobalt_wren.api.plugins import (
        Plugin,
        PluginContributions,
        PluginMetadata,
        ProviderContribution,
        ToolContribution,
    )

    class ReplacementProvider:
        def complete(self, text: str) -> str:
            return f"provider:{text}"

    class ReplacementTool:
        def __call__(self, text: str) -> str:
            return f"tool:{text}"

    adapters = Plugin(
        metadata=PluginMetadata(
            name="acme.adapters", version="1.0.0", plugin_types=("provider", "tool")
        ),
        contributions=PluginContributions(
            providers=(
                ProviderContribution(
                    name="external-provider",
                    provider_type="llm",
                    create_client=lambda **_: ReplacementProvider(),
                ),
            ),
            tools=(
                ToolContribution(
                    name="external.tool", create_tool=lambda **_: ReplacementTool()
                ),
            ),
        ),
    )
    config = {
        "version": 1,
        "environment": "test",
        "providers": {
            "external-profile": {
                "provider": "external-provider",
                "model": "opaque-model",
            }
        },
        "tools": {"allowlist": ["external.tool"]},
    }
    workflow = create_plugin(
        requirements=WorkflowRequirements(
            provider_profiles=("external-profile",), tools=("external.tool",)
        )
    )

    prepared = create_engine(config, plugins=(adapters, workflow)).prepare_workflow(
        EXTERNAL_WORKFLOW_KIND
    )
    result = prepared.execute({"request_id": "REQ-8"})

    assert result.output["provider"] == "provider:REQ-8"
    assert result.output["tool"] == "tool:REQ-8"


def test_external_workflow_uses_artifact_checkpoint_and_event_sink_replacements(tmp_path) -> None:
    from cobalt_wren.api.plugins import EventSinkContribution, Plugin, PluginContributions, PluginMetadata
    from tests.support.recording_event_sink import RecordingEventSink

    sink = RecordingEventSink()
    sink_plugin = Plugin(
        metadata=PluginMetadata(name="acme.events", version="1.0.0", plugin_types=("event_sink",)),
        contributions=PluginContributions(
            event_sinks=(EventSinkContribution(backend_name="recording", create_sink=lambda **_: sink),)
        ),
    )
    workflow = create_plugin(
        requirements=WorkflowRequirements(
            artifact_store=True,
            checkpoint_store=True,
            event_sinks=("external-events",),
        )
    )
    config = {
        "version": 1,
        "environment": "test",
        "stores": {
            "artifact": {"backend": "filesystem", "config": {"root": str(tmp_path / "artifacts")}},
            "checkpoint": {"backend": "filesystem", "config": {"root": str(tmp_path / "checkpoints")}},
        },
        "event_sinks": {"external-events": {"backend": "recording"}},
    }

    result = create_engine(config, plugins=(sink_plugin, workflow)).prepare_workflow(
        EXTERNAL_WORKFLOW_KIND
    ).execute({"request_id": "REQ-10"})

    assert result.output["artifact_key"] == "reviews/REQ-10.txt"
    assert result.output["checkpoint_id"] == "reviewed"
    assert result.output["event_emitted"] is True
    assert sink.run_events[-1].kind == "acme.reviewed"
    assert (tmp_path / "artifacts").exists()
    assert (tmp_path / "checkpoints").exists()
