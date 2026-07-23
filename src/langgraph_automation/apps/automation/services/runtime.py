"""Runtime factory for the Django control plane.

This module is the dependency assembly boundary for execution-plane services.
It composes concrete dependencies from trusted package settings, workflow
configuration, and run context, but it does not execute graphs or mutate Run
lifecycle state.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from importlib import metadata as importlib_metadata
from threading import Lock

from django.conf import settings as django_settings

from langgraph_automation.api.engine import AutomationEngine, EnginePreparedWorkflow, create_engine
from langgraph_automation.api.errors import ConfigError
from langgraph_automation.api.plugins import Plugin
from langgraph_automation.api.stores import ArtifactReadResult
from langgraph_automation.apps.automation.models.run import Run
from langgraph_automation.apps.automation.services.workflow_reference import WorkflowReference
from langgraph_automation.config.artifact_store import normalize_artifact_store_settings
from langgraph_automation.config.normalizer import load_normalized_package_config_from_mapping
from langgraph_automation.config.models import NormalizedPackageConfig
from langgraph_automation.integrations.observability.base import EventSink
from langgraph_automation.integrations.observability.django_event_sink import DjangoEventSink



@dataclass(frozen=True, slots=True)
class EngineGeneration:
    generation: int
    signature: str


@dataclass(slots=True)
class DeploymentEngineOwner:
    """Own a lazy, atomically replaceable deployment engine cache."""

    raw_config: Mapping[str, object]
    plugins: tuple[Plugin, ...] = ()
    discover_plugins: bool = True
    _engine: AutomationEngine | None = field(default=None, init=False, repr=False)
    _generation: int = field(default=0, init=False, repr=False)
    _signature: str = field(default="", init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)
    _reconfigure_lock: Lock = field(default_factory=Lock, init=False, repr=False)

    @property
    def generation(self) -> EngineGeneration:
        with self._lock:
            signature = self._signature or self._configuration_signature(
                self.raw_config, self.plugins, self.discover_plugins
            )
            return EngineGeneration(self._generation, signature)

    def get_engine(self) -> AutomationEngine:
        engine = self._engine
        if engine is not None:
            return engine
        with self._lock:
            if self._engine is None:
                signature = self._configuration_signature(
                    self.raw_config, self.plugins, self.discover_plugins
                )
                self._engine = create_engine(
                    self.raw_config,
                    plugins=self.plugins,
                    discover_plugins=self.discover_plugins,
                )
                self._generation = 1
                self._signature = signature
            return self._engine

    def prepare(self, reference: WorkflowReference) -> EnginePreparedWorkflow:
        self.get_engine()
        with self._lock:
            engine = self._engine
            generation = self._generation
            signature = self._signature
        if engine is None:  # pragma: no cover - protected by get_engine
            raise RuntimeError("deployment engine was not initialized")
        prepared = engine.prepare_workflow(reference.kind, config=reference.config)
        return replace(
            prepared,
            engine_generation=generation,
            engine_signature=signature,
        )

    def reconfigure(
        self,
        *,
        raw_config: Mapping[str, object],
        plugins: tuple[Plugin, ...] = (),
        discover_plugins: bool = True,
        force: bool = False,
    ) -> EngineGeneration:
        """Build a candidate and atomically swap it on success.

        Existing engines and prepared workflows remain valid while the candidate
        is built. A failed candidate build leaves the last-known-good state intact.
        """
        candidate_config = dict(raw_config)
        candidate_plugins = tuple(plugins)
        with self._reconfigure_lock:
            candidate_signature = self._configuration_signature(
                candidate_config, candidate_plugins, discover_plugins
            )
            with self._lock:
                if (
                    not force
                    and self._engine is not None
                    and candidate_signature == self._signature
                ):
                    return EngineGeneration(self._generation, self._signature)

            candidate = create_engine(
                candidate_config,
                plugins=candidate_plugins,
                discover_plugins=discover_plugins,
            )

            with self._lock:
                self.raw_config = candidate_config
                self.plugins = candidate_plugins
                self.discover_plugins = discover_plugins
                self._engine = candidate
                self._generation += 1
                self._signature = candidate_signature
                return EngineGeneration(self._generation, self._signature)

    @staticmethod
    def _configuration_signature(
        raw_config: Mapping[str, object],
        plugins: tuple[Plugin, ...],
        discover_plugins: bool,
    ) -> str:
        identity = (
            _freeze_signature_value(raw_config),
            tuple(
                (
                    plugin.metadata.name,
                    plugin.metadata.version,
                    tuple(plugin.metadata.plugin_types),
                    _freeze_signature_value(plugin.metadata.provides),
                )
                for plugin in plugins
            ),
            discover_plugins,
            _installed_plugin_entry_point_signature() if discover_plugins else (),
        )
        return hashlib.sha256(repr(identity).encode("utf-8")).hexdigest()


def _freeze_signature_value(value: object) -> object:
    if isinstance(value, Mapping):
        return tuple(
            (str(key), _freeze_signature_value(item))
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_signature_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return tuple(sorted((_freeze_signature_value(item) for item in value), key=repr))
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    return (type(value).__module__, type(value).__qualname__, repr(value))


def _installed_plugin_entry_point_signature() -> tuple[tuple[str, str, str, str], ...]:
    entries = importlib_metadata.entry_points().select(group="langgraph_automation.plugins")
    signature: list[tuple[str, str, str, str]] = []
    for entry in entries:
        distribution = getattr(entry, "dist", None)
        distribution_name = ""
        distribution_version = ""
        if distribution is not None:
            distribution_name = str(distribution.metadata.get("Name", ""))
            distribution_version = str(distribution.version or "")
        signature.append((entry.name, entry.value, distribution_name, distribution_version))
    return tuple(sorted(signature))


@dataclass(frozen=True, slots=True)
class RunExecutionServices:
    """Process-bound public workflow execution services."""

    engine_owner: DeploymentEngineOwner

    def prepare_workflow(self, reference: WorkflowReference) -> EnginePreparedWorkflow:
        return self.engine_owner.prepare(reference)

    def read_artifact(self, storage_key: str) -> ArtifactReadResult | None:
        return self.engine_owner.get_engine().read_artifact(storage_key)

    def reconfigure_engine(
        self,
        *,
        raw_config: Mapping[str, object],
        plugins: tuple[Plugin, ...] = (),
        discover_plugins: bool = True,
        force: bool = False,
    ) -> EngineGeneration:
        return self.engine_owner.reconfigure(
            raw_config=raw_config,
            plugins=plugins,
            discover_plugins=discover_plugins,
            force=force,
        )


def get_run_execution_services() -> RunExecutionServices:
    """Return the app-config bound run execution services instance."""

    from django.apps import apps as django_apps

    app_config = django_apps.get_app_config("automation")
    services = getattr(app_config, "run_execution_services", None)
    if services is None:
        raise RuntimeError("automation app runtime services have not been initialized")
    return services


def load_deployment_package_config_from_settings() -> Mapping[str, object]:
    """Return the deployment-owned package config mapping from Django settings."""

    config_file = str(getattr(django_settings, "LANGGRAPH_AUTOMATION_CONFIG_FILE", "") or "").strip()
    if config_file:
        from pathlib import Path
        path = Path(config_file).expanduser().resolve()
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigError(
                "Configuration file could not be loaded.",
                code="CONFIG_FILE_INVALID",
                component="automation_runtime",
                metadata={"path": str(path)},
            ) from exc
    else:
        config = getattr(django_settings, "LANGGRAPH_AUTOMATION", None)
    if config is None:
        return {"version": 1}
    if isinstance(config, str):
        try:
            config = json.loads(config)
        except json.JSONDecodeError as exc:
            raise ConfigError(
                "Configuration is invalid: LANGGRAPH_AUTOMATION must be valid JSON.",
                code="CONFIG_INVALID_MAPPING",
                component="automation_runtime",
            ) from exc
    if not isinstance(config, Mapping):
        raise ConfigError(
            "Configuration is invalid: LANGGRAPH_AUTOMATION must be a mapping.",
            code="CONFIG_INVALID_MAPPING",
            component="automation_runtime",
        )
    return config


def load_normalized_deployment_package_config_from_settings():
    """Return the normalized deployment-owned package config for startup binding."""

    return load_normalized_package_config_from_mapping(load_deployment_package_config_from_settings())


def deployment_package_config_signature(package_config: NormalizedPackageConfig) -> tuple[object, ...]:
    """Return the canonical startup-binding identity for a normalized package config."""

    artifact_store_settings = normalize_artifact_store_settings(package_config.stores.get("artifact"))
    return (
        package_config.version,
        package_config.environment,
        package_config.plugins,
        package_config.providers,
        package_config.tools,
        artifact_store_settings,
        package_config.checkpoint_store,
        package_config.event_sinks,
        package_config.limits,
        package_config.observability,
        package_config.safety,
        package_config.metadata,
    )


def build_event_sink(run: Run) -> EventSink:
    """Build the observability sink for a run.

    This is a concrete adapter wiring boundary only; it must not perform business
    logic or runtime execution.
    """

    return DjangoEventSink()


def build_run_execution_services(
    raw_config: Mapping[str, object],
    *,
    plugins: tuple[Plugin, ...] = (),
    discover_plugins: bool = True,
) -> RunExecutionServices:
    """Bind a lazy deployment engine owner without assembling runtime dependencies."""

    return RunExecutionServices(
        engine_owner=DeploymentEngineOwner(
            raw_config=dict(raw_config),
            plugins=plugins,
            discover_plugins=discover_plugins,
        )
    )


def build_run_execution_services_from_mapping(
    config: Mapping[str, object],
) -> RunExecutionServices:
    return build_run_execution_services(config)


def build_run_execution_services_from_settings() -> RunExecutionServices:
    return build_run_execution_services(load_deployment_package_config_from_settings())
