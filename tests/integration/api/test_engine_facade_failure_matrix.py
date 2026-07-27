"""Package engine facade failure matrix tests."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from cobalt_wren.api.engine import create_engine
from cobalt_wren.api.errors import ConfigError, PluginRegistrationError, PluginResolutionError, RuntimeAssemblyError
from cobalt_wren.api.plugins import EventSinkContribution, Plugin, PluginContributions, PluginMetadata, ProviderContribution, ToolContribution
from cobalt_wren.api.workflow import WorkflowContribution, WorkflowDefinition, WorkflowMetadata, WorkflowRequirements


def _minimal_config() -> dict[str, object]:
    return {
        "version": 1,
        "environment": "test",
    }


def _reference_config(*, include_tool: bool = True) -> dict[str, object]:
    config: dict[str, object] = {
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
    }
    if include_tool:
        config["tools"] = {"allowlist": ["echo"]}
    else:
        config["tools"] = {"allowlist": []}
    return config


def _workflow_plugin(
    *,
    plugin_name: str,
    workflow_kind: str,
    requirements: WorkflowRequirements,
    build: Callable[..., object],
) -> Plugin:
    return Plugin(
        metadata=PluginMetadata(name=plugin_name, version="0.1.0", plugin_types=("workflow",)),
        contributions=PluginContributions(
            workflows=(
                WorkflowContribution(
                    kind=workflow_kind,
                    definition=WorkflowDefinition(
                        kind=workflow_kind,
                        metadata=WorkflowMetadata(name=workflow_kind),
                        requirements=requirements,
                        build=build,
                    ),
                ),
            ),
        ),
    )


def _provider_plugin(*, plugin_name: str, provider_name: str, create_client: Callable[..., object]) -> Plugin:
    return Plugin(
        metadata=PluginMetadata(name=plugin_name, version="0.1.0", plugin_types=("provider",)),
        contributions=PluginContributions(
            providers=(
                ProviderContribution(
                    name=provider_name,
                    provider_type="llm",
                    create_client=create_client,
                ),
            ),
        ),
    )


def _tool_plugin(*, plugin_name: str, tool_name: str, create_tool: Callable[..., object]) -> Plugin:
    return Plugin(
        metadata=PluginMetadata(name=plugin_name, version="0.1.0", plugin_types=("tool",)),
        contributions=PluginContributions(
            tools=(
                ToolContribution(
                    name=tool_name,
                    create_tool=create_tool,
                ),
            ),
        ),
    )


def _event_sink_plugin(*, plugin_name: str, backend_name: str, create_sink: Callable[..., object]) -> Plugin:
    return Plugin(
        metadata=PluginMetadata(name=plugin_name, version="0.1.0", plugin_types=("event_sink",)),
        contributions=PluginContributions(
            event_sinks=(
                EventSinkContribution(
                    backend_name=backend_name,
                    create_sink=create_sink,
                ),
            ),
        ),
    )


@pytest.fixture(autouse=True)
def _forbid_runtime_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbid_completion(*args, **kwargs):
        raise AssertionError("provider network call should not happen during preparation")

    def forbid_tool_call(self, **kwargs):
        raise AssertionError("tool execution should not happen during preparation")

    monkeypatch.setattr("litellm.completion", forbid_completion)
    monkeypatch.setattr("cobalt_wren.integrations.tools.safe_tools.EchoTool.__call__", forbid_tool_call)


def test_unknown_workflow_kind_is_safe() -> None:
    engine = create_engine(_minimal_config())

    with pytest.raises(PluginResolutionError) as excinfo:
        engine.prepare_workflow("unknown.workflow")

    assert excinfo.value.code == "WORKFLOW_PREPARATION_WORKFLOW_NOT_FOUND"
    assert excinfo.value.component == "workflow_preparer"
    assert "Traceback" not in excinfo.value.safe_message


def test_missing_provider_requirement_is_safe() -> None:
    plugin = _workflow_plugin(
        plugin_name="tests.needs-provider",
        workflow_kind="test.needs-provider",
        requirements=WorkflowRequirements(provider_profiles=("default",)),
        build=lambda: object(),
    )
    engine = create_engine(_minimal_config(), plugins=(plugin,))

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        engine.prepare_workflow("test.needs-provider")

    assert excinfo.value.code == "WORKFLOW_REQUIREMENT_MISSING"
    assert excinfo.value.component == "workflow_requirements"
    assert excinfo.value.metadata["requirement_type"] == "provider_profile"
    assert excinfo.value.metadata["requirement_name"] == "default"


@pytest.mark.usefixtures("monkeypatch")
def test_missing_tool_requirement_is_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    plugin = _workflow_plugin(
        plugin_name="tests.needs-tool",
        workflow_kind="test.needs-tool",
        requirements=WorkflowRequirements(tools=("echo",)),
        build=lambda: object(),
    )
    engine = create_engine(
        _reference_config(include_tool=False),
        plugins=(plugin,),
    )

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        engine.prepare_workflow("test.needs-tool")

    assert excinfo.value.code == "WORKFLOW_REQUIREMENT_MISSING"
    assert excinfo.value.metadata["requirement_type"] == "tool"
    assert excinfo.value.metadata["requirement_name"] == "echo"


@pytest.mark.parametrize(
    ("workflow_kind", "requirements", "missing_type", "missing_name"),
    [
        ("integration.needs_event_sink", WorkflowRequirements(event_sinks=("stdout",)), "event_sink", "stdout"),
    ],
)
def test_other_missing_workflow_requirements_are_safe(
    workflow_kind: str,
    requirements: WorkflowRequirements,
    missing_type: str,
    missing_name: str,
) -> None:
    plugin = _workflow_plugin(
        plugin_name=f"{workflow_kind}.plugin",
        workflow_kind=workflow_kind,
        requirements=requirements,
        build=lambda: {"graph": workflow_kind},
    )
    engine = create_engine(_minimal_config(), plugins=(plugin,))

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        engine.prepare_workflow(workflow_kind)

    assert excinfo.value.code == "WORKFLOW_REQUIREMENT_MISSING"
    assert excinfo.value.metadata["requirement_type"] == missing_type
    assert excinfo.value.metadata["requirement_name"] == missing_name


@pytest.mark.usefixtures("monkeypatch")
def test_invalid_config_is_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ConfigError) as excinfo:
        create_engine({"version": 2})

    assert excinfo.value.code == "CONFIG_UNSUPPORTED_VERSION"
    assert "Traceback" not in excinfo.value.safe_message


@pytest.mark.usefixtures("monkeypatch")
def test_missing_secret_is_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        create_engine(_reference_config())

    assert excinfo.value.code == "RUNTIME_ASSEMBLY_SECRET_MISSING"
    assert excinfo.value.component == "runtime_assembly"
    assert excinfo.value.metadata["secret_name"] == "OPENAI_API_KEY"
    assert "secret-key" not in excinfo.value.safe_message


def test_duplicate_explicit_workflow_kind_conflict_is_safe() -> None:
    with pytest.raises(PluginRegistrationError) as excinfo:
        create_engine(
            _minimal_config(),
            plugins=(
                _workflow_plugin(
                    plugin_name="integration.plugin.a",
                    workflow_kind="integration.duplicate_workflow",
                    requirements=WorkflowRequirements(),
                    build=lambda: {"graph": "a"},
                ),
                _workflow_plugin(
                    plugin_name="integration.plugin.b",
                    workflow_kind="integration.duplicate_workflow",
                    requirements=WorkflowRequirements(),
                    build=lambda: {"graph": "b"},
                ),
            ),
        )

    assert excinfo.value.code == "PLUGIN_CONTRIBUTION_CONFLICT"
    assert excinfo.value.component == "plugin_registry"
    assert excinfo.value.metadata["contribution_scope"] == "workflow"
    assert excinfo.value.metadata["contribution_name"] == "integration.duplicate_workflow"


@pytest.mark.parametrize(
    ("workflow_kind", "build", "expected_code"),
    [
        ("integration.build_none", lambda: None, "WORKFLOW_BUILD_INVALID_RESULT"),
        ("integration.build_error", lambda: (_ for _ in ()).throw(ValueError("password=secret-value")), "WORKFLOW_BUILD_FAILED"),
    ],
)
def test_workflow_build_failures_are_safe(workflow_kind: str, build: Callable[..., object], expected_code: str) -> None:
    plugin = _workflow_plugin(
        plugin_name=f"{workflow_kind}.plugin",
        workflow_kind=workflow_kind,
        requirements=WorkflowRequirements(),
        build=build,
    )
    engine = create_engine(_minimal_config(), plugins=(plugin,))

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        engine.prepare_workflow(workflow_kind)

    assert excinfo.value.code == expected_code
    assert "password=secret-value" not in excinfo.value.safe_message
    assert "password=secret-value" not in str(excinfo.value.metadata)


@pytest.mark.parametrize(
    ("plugin_factory", "config", "expected_code"),
    [
        (
            lambda: _provider_plugin(
                plugin_name="integration.provider_failure",
                provider_name="boom",
                create_client=lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("password=secret-value")),
            ),
            {
                "version": 1,
                "environment": "test",
                "providers": {"default": {"provider": "boom", "model": "test-model"}},
            },
            "RUNTIME_ASSEMBLY_PROVIDER_FAILED",
        ),
        (
            lambda: _tool_plugin(
                plugin_name="integration.tool_failure",
                tool_name="boom.tool",
                create_tool=lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("password=secret-value")),
            ),
            {
                "version": 1,
                "environment": "test",
                "providers": {"default": {"provider": "litellm", "model": "gpt-4.1-mini", "secrets": {"api_key": {"source": "env", "name": "OPENAI_API_KEY"}}}},
                "tools": {"allowlist": ["boom.tool"]},
            },
            "RUNTIME_ASSEMBLY_TOOL_FAILED",
        ),
        (
            lambda: _event_sink_plugin(
                plugin_name="integration.event_sink_failure",
                backend_name="boom",
                create_sink=lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("password=secret-value")),
            ),
            {
                "version": 1,
                "environment": "test",
                "providers": {"default": {"provider": "litellm", "model": "gpt-4.1-mini", "secrets": {"api_key": {"source": "env", "name": "OPENAI_API_KEY"}}}},
                "event_sinks": {"stdout": {"backend": "boom"}},
            },
            "RUNTIME_ASSEMBLY_EVENT_SINK_FAILED",
        ),
    ],
)
def test_factory_failures_are_safe(
    monkeypatch: pytest.MonkeyPatch,
    plugin_factory: Callable[[], Plugin],
    config: dict[str, object],
    expected_code: str,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    with pytest.raises(RuntimeAssemblyError) as excinfo:
        create_engine(config, plugins=(plugin_factory(),))

    assert excinfo.value.code == expected_code
    assert "password=secret-value" not in excinfo.value.safe_message
    assert "password=secret-value" not in str(excinfo.value.metadata)
