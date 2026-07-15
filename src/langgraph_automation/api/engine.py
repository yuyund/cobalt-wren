"""Public-facing provisional package engine facade.

The facade keeps package internals hidden from application and control-plane
callers while still allowing workflow preparation through a small entrypoint.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from langgraph_automation.api.errors import FrameworkError, RuntimeAssemblyError
from langgraph_automation.api.plugins import (
    Plugin,
    PluginContributions,
    PluginMetadata,
    ProviderContribution,
    ToolContribution,
)
from langgraph_automation.config.loader import load_package_config_from_mapping
from langgraph_automation.config.models import NormalizedPackageConfig, PluginsConfig, ProviderProfileConfig
from langgraph_automation.config.normalizer import normalize_package_config
from langgraph_automation.config.validator import ConfigValidator
from langgraph_automation.integrations.llm.litellm_client import LiteLLMClient
from langgraph_automation.integrations.tools.safe_tools import EchoTool
from langgraph_automation.plugins.registry import PluginRegistry
from langgraph_automation.runtime.assembly import RuntimeAssembler
from langgraph_automation.runtime.dependencies import RuntimeDependencies
from langgraph_automation.runtime.secrets import EnvSecretResolver
from langgraph_automation.workflows.catalog import create_builtin_workflow_registry
from langgraph_automation.workflows.prepare import WorkflowPreparer

__all__ = ["EnginePreparedWorkflow", "AutomationEngine", "create_engine"]

_ENGINE_COMPONENT = "api_engine"
_INTERNAL_RUNTIME_PLUGIN_NAME = "langgraph_automation.engine_runtime_defaults"
_INTERNAL_RUNTIME_PLUGIN_VERSION = "0.1.0"
_DEFAULT_PROVIDER_NAME = "litellm"
_DEFAULT_TOOL_NAME = "echo"


@dataclass(frozen=True, slots=True)
class EnginePreparedWorkflow:
    """Public-facing provisional workflow handle."""

    kind: str
    graph: object


class AutomationEngine:
    """Application-facing package engine with hidden internals."""

    __slots__ = ("_validated_config", "_dependencies", "_registry", "_preparer")

    def __init__(
        self,
        *,
        validated_config: NormalizedPackageConfig,
        dependencies: RuntimeDependencies,
        registry: PluginRegistry,
    ) -> None:
        self._validated_config = validated_config
        self._dependencies = dependencies
        self._registry = registry
        self._preparer = WorkflowPreparer(registry)

    def prepare_workflow(self, workflow_kind: str) -> EnginePreparedWorkflow:
        try:
            prepared = self._preparer.prepare(workflow_kind=workflow_kind, dependencies=self._dependencies)
        except FrameworkError:
            raise
        except Exception as exc:  # pragma: no cover - defensive boundary wrapping
            raise RuntimeAssemblyError(
                "Engine workflow preparation failed.",
                code="ENGINE_WORKFLOW_PREPARATION_FAILED",
                component=_ENGINE_COMPONENT,
                metadata={"workflow_kind": workflow_kind},
            ) from exc

        return EnginePreparedWorkflow(kind=prepared.kind, graph=prepared.graph)


def create_engine(
    config: Mapping[str, object],
    *,
    plugins: Sequence[Plugin] = (),
) -> AutomationEngine:
    try:
        registry = create_builtin_workflow_registry()
        runtime_defaults_plugin = _build_runtime_defaults_plugin()
        registry.register(runtime_defaults_plugin)
        for plugin in plugins:
            registry.register(plugin)

        normalized_config = normalize_package_config(load_package_config_from_mapping(config))
        normalized_config = _augment_enabled_plugins(
            normalized_config,
            runtime_plugin_name=runtime_defaults_plugin.metadata.name,
            explicit_plugin_names=tuple(plugin.metadata.name for plugin in plugins),
        )

        validated_config = ConfigValidator(registry).validate(normalized_config)
        dependencies = RuntimeAssembler(secret_resolver=EnvSecretResolver()).assemble(validated_config)
        return AutomationEngine(validated_config=validated_config, dependencies=dependencies, registry=registry)
    except FrameworkError:
        raise
    except Exception as exc:  # pragma: no cover - defensive boundary wrapping
        raise RuntimeAssemblyError(
            "Engine creation failed.",
            code="ENGINE_CREATE_FAILED",
            component=_ENGINE_COMPONENT,
        ) from exc


def _augment_enabled_plugins(
    config: NormalizedPackageConfig,
    *,
    runtime_plugin_name: str,
    explicit_plugin_names: tuple[str, ...],
) -> NormalizedPackageConfig:
    enabled = _merge_unique_plugins(
        config.plugins.enabled,
        (runtime_plugin_name, *explicit_plugin_names),
    )
    if enabled == config.plugins.enabled:
        return config
    return replace(config, plugins=PluginsConfig(enabled=enabled))


def _merge_unique_plugins(*plugin_groups: tuple[str, ...] | Sequence[str]) -> tuple[str, ...]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in plugin_groups:
        for plugin_name in group:
            if plugin_name in seen:
                continue
            seen.add(plugin_name)
            merged.append(plugin_name)
    return tuple(merged)


def _build_runtime_defaults_plugin() -> Plugin:
    return Plugin(
        metadata=PluginMetadata(
            name=_INTERNAL_RUNTIME_PLUGIN_NAME,
            version=_INTERNAL_RUNTIME_PLUGIN_VERSION,
            description="Internal runtime defaults for package engine facade.",
            plugin_types=("provider", "tool"),
            provides={
                "providers": (_DEFAULT_PROVIDER_NAME,),
                "tools": (_DEFAULT_TOOL_NAME,),
            },
            metadata={"visibility": "internal", "scope": "engine"},
        ),
        contributions=PluginContributions(
            providers=(
                ProviderContribution(
                    name=_DEFAULT_PROVIDER_NAME,
                    provider_type="llm",
                    description="Default LiteLLM provider used by the package engine.",
                    supported_parameters=("model", "base_url", "temperature", "max_tokens"),
                    create_client=_create_default_llm_client,
                ),
            ),
            tools=(
                ToolContribution(
                    name=_DEFAULT_TOOL_NAME,
                    description="Safe echo tool used by the reference workflow.",
                    capabilities=("echo",),
                    create_tool=_create_default_echo_tool,
                ),
            ),
        ),
    )


def _create_default_llm_client(*, config: ProviderProfileConfig, context: object) -> object:
    model = _resolve_model_name(config)
    api_key = _resolve_optional_secret(config, context, "api_key")
    base_url = _optional_str(config.parameters.get("base_url"))
    temperature = _optional_float(config.parameters.get("temperature"))
    max_tokens = _optional_int(config.parameters.get("max_tokens"))
    return LiteLLMClient(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _create_default_echo_tool(*, config: object, context: object) -> object:
    del config, context
    return EchoTool()


def _resolve_model_name(config: ProviderProfileConfig) -> str:
    model = config.model or _optional_str(config.parameters.get("model"))
    if not model:
        raise RuntimeAssemblyError(
            "Runtime assembly failed: provider model is required.",
            code="RUNTIME_ASSEMBLY_INVALID_CONFIG",
            component=_ENGINE_COMPONENT,
            metadata={"provider": config.provider},
        )
    return model


def _resolve_optional_secret(config: ProviderProfileConfig, context: object, secret_name: str) -> str | None:
    secret_ref = config.secrets.get(secret_name)
    if secret_ref is None:
        return None
    resolver = getattr(context, "secrets", None)
    if resolver is None:
        raise RuntimeAssemblyError(
            "Runtime assembly failed: secret resolver is unavailable.",
            code="RUNTIME_ASSEMBLY_SECRET_RESOLVER_MISSING",
            component=_ENGINE_COMPONENT,
            metadata={"provider": config.provider, "secret_name": secret_name},
        )
    return resolver.resolve(secret_ref)


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return str(value)


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None
