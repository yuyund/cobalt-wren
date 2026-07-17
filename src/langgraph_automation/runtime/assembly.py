"""Assemble runtime dependencies from validated package config."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from langgraph_automation.api.errors import RuntimeAssemblyError
from langgraph_automation.config.artifact_store import normalize_artifact_store_settings
from langgraph_automation.config.models import ValidatedPackageConfig

from .artifact_store import build_artifact_store
from .context import FactoryContext
from .dependencies import RuntimeDependencies
from .secrets import EnvSecretResolver, SecretResolver

__all__ = ["RuntimeAssembler", "assemble_runtime_dependencies"]

_COMPONENT = "runtime_assembly"


class RuntimeAssembler:
    def __init__(self, *, secret_resolver: SecretResolver | None = None) -> None:
        self._secret_resolver = secret_resolver or EnvSecretResolver()

    def assemble(self, config: ValidatedPackageConfig) -> RuntimeDependencies:
        if not isinstance(config, ValidatedPackageConfig):
            raise TypeError("config must be a ValidatedPackageConfig")

        context = FactoryContext(
            environment=config.normalized.environment,
            secrets=self._secret_resolver,
            limits=config.normalized.limits,
            observability=config.normalized.observability,
            safety=config.normalized.safety,
        )

        artifact_store = self._assemble_artifact_store(config)
        providers = self._assemble_providers(config, context)
        tools = self._assemble_tools(config, context)
        _, checkpoint_store = self._assemble_stores(config, context)
        event_sinks = self._assemble_event_sinks(config, context)

        return RuntimeDependencies(
            providers=providers,
            tools=tools,
            artifact_store=artifact_store,
            checkpoint_store=checkpoint_store,
            event_sinks=event_sinks,
        )

    def _assemble_providers(self, config: ValidatedPackageConfig, context: FactoryContext) -> dict[str, object]:
        assembled: dict[str, object] = {}
        for profile_name, profile in config.normalized.providers.items():
            contribution = config.effective_plugins.providers.get(profile.provider)
            if contribution is None:
                raise self._missing_contribution_error(
                    "provider",
                    contribution_name=profile.provider,
                    metadata={"provider": profile.provider, "profile": profile_name},
                )
            client = self._invoke_factory_hook(
                contribution.create_client,
                config=profile,
                context=context,
                safe_message="Runtime assembly failed: provider could not be initialized.",
                code="RUNTIME_ASSEMBLY_PROVIDER_FAILED",
                metadata={"provider": profile.provider, "profile": profile_name},
                contribution_scope="provider",
                contribution_name=profile.provider,
            )
            assembled[profile_name] = client
        return assembled

    def _assemble_artifact_store(self, config: ValidatedPackageConfig) -> object:
        settings = normalize_artifact_store_settings(config.normalized.stores.get("artifact"))
        return build_artifact_store(settings)

    def _assemble_tools(self, config: ValidatedPackageConfig, context: FactoryContext) -> dict[str, object]:
        assembled: dict[str, object] = {}
        allowlist = config.normalized.tools.allowlist
        configs = config.normalized.tools.configs
        for tool_name in allowlist:
            contribution = config.effective_plugins.tools.get(tool_name)
            if contribution is None:
                raise self._missing_contribution_error(
                    "tool",
                    contribution_name=tool_name,
                    metadata={"tool_name": tool_name},
                )
            tool_config = configs.get(tool_name, {})
            if tool_config is None:
                tool_config = {}
            if not isinstance(tool_config, Mapping):
                raise self._assembly_error(
                    "Runtime assembly failed: tool config must be a mapping.",
                    code="RUNTIME_ASSEMBLY_INVALID_CONFIG",
                    metadata={"tool_name": tool_name},
                )
            tool = self._invoke_factory_hook(
                contribution.create_tool,
                config=tool_config,
                context=context,
                safe_message="Runtime assembly failed: tool could not be initialized.",
                code="RUNTIME_ASSEMBLY_TOOL_FAILED",
                metadata={"tool_name": tool_name},
                contribution_scope="tool",
                contribution_name=tool_name,
            )
            assembled[tool_name] = tool
        return assembled

    def _assemble_stores(self, config: ValidatedPackageConfig, context: FactoryContext) -> tuple[object | None, object | None]:
        checkpoint_store: object | None = None
        for store_type, store_config in config.normalized.stores.items():
            if store_type == "artifact":
                continue
            if store_type != "checkpoint":
                raise self._assembly_error(
                    f"Runtime assembly failed: unsupported store type '{store_type}'.",
                    code="RUNTIME_ASSEMBLY_UNSUPPORTED_STORE_TYPE",
                    metadata={"store_type": store_type, "backend": store_config.backend},
                )
            contribution = config.effective_plugins.stores.get((store_type, store_config.backend))
            if contribution is None:
                raise self._missing_contribution_error(
                    "store",
                    contribution_name=f"{store_type}:{store_config.backend}",
                    metadata={"store_type": store_type, "backend": store_config.backend},
                )
            store = self._invoke_factory_hook(
                contribution.create_store,
                config=store_config,
                context=context,
                safe_message="Runtime assembly failed: store could not be initialized.",
                code="RUNTIME_ASSEMBLY_STORE_FAILED",
                metadata={"store_type": store_type, "backend": store_config.backend},
                contribution_scope="store",
                contribution_name=f"{store_type}:{store_config.backend}",
            )
            checkpoint_store = store
        return None, checkpoint_store

    def _assemble_event_sinks(self, config: ValidatedPackageConfig, context: FactoryContext) -> dict[str, object]:
        assembled: dict[str, object] = {}
        for sink_name, sink_config in config.normalized.event_sinks.items():
            contribution = config.effective_plugins.event_sinks.get(sink_config.backend)
            if contribution is None:
                raise self._missing_contribution_error(
                    "event_sink",
                    contribution_name=sink_config.backend,
                    metadata={"backend": sink_config.backend, "event_sink": sink_name},
                )
            sink = self._invoke_factory_hook(
                contribution.create_sink,
                config=sink_config,
                context=context,
                safe_message="Runtime assembly failed: event sink could not be initialized.",
                code="RUNTIME_ASSEMBLY_EVENT_SINK_FAILED",
                metadata={"backend": sink_config.backend, "event_sink": sink_name},
                contribution_scope="event_sink",
                contribution_name=sink_config.backend,
            )
            assembled[sink_name] = sink
        return assembled

    def _invoke_factory_hook(
        self,
        hook: Callable[..., object] | None,
        *,
        config: object,
        context: FactoryContext,
        safe_message: str,
        code: str,
        metadata: dict[str, object],
        contribution_scope: str,
        contribution_name: str,
    ) -> object:
        if hook is None:
            raise self._assembly_error(
                f"Runtime assembly failed: {contribution_scope} factory is not provided.",
                code="RUNTIME_ASSEMBLY_FACTORY_MISSING",
                metadata={
                    "contribution_scope": contribution_scope,
                    "contribution_name": contribution_name,
                    **metadata,
                },
            )
        try:
            result = hook(config=config, context=context)
        except RuntimeAssemblyError:
            raise
        except Exception as exc:
            raise self._assembly_error(
                safe_message,
                code=code,
                metadata={
                    "contribution_scope": contribution_scope,
                    "contribution_name": contribution_name,
                    **metadata,
                },
            ) from exc
        if result is None:
            raise self._assembly_error(
                f"Runtime assembly failed: {contribution_scope} factory returned no object.",
                code="RUNTIME_ASSEMBLY_INVALID_FACTORY_RESULT",
                metadata={
                    "contribution_scope": contribution_scope,
                    "contribution_name": contribution_name,
                    **metadata,
                },
            )
        return result

    def _missing_contribution_error(self, contribution_scope: str, *, contribution_name: str, metadata: dict[str, object]) -> RuntimeAssemblyError:
        return self._assembly_error(
            f"Runtime assembly failed: {contribution_scope} contribution '{contribution_name}' is not available.",
            code="RUNTIME_ASSEMBLY_MISSING_CONTRIBUTION",
            metadata={"contribution_scope": contribution_scope, "contribution_name": contribution_name, **metadata},
        )

    @staticmethod
    def _assembly_error(safe_message: str, *, code: str, metadata: dict[str, object]) -> RuntimeAssemblyError:
        return RuntimeAssemblyError(safe_message, code=code, component=_COMPONENT, metadata=metadata)


def assemble_runtime_dependencies(
    config: ValidatedPackageConfig,
    *,
    secret_resolver: SecretResolver | None = None,
) -> RuntimeDependencies:
    return RuntimeAssembler(secret_resolver=secret_resolver).assemble(config)
