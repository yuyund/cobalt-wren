"""Django app config for the automation control plane."""

from __future__ import annotations

from copy import deepcopy

from langgraph_automation.api.errors import ConfigError
from django.apps import AppConfig


class AutomationConfig(AppConfig):
    """App config for automation models, services, selectors, and UI specs."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "langgraph_automation.apps.automation"
    label = "automation"

    def ready(self) -> None:
        from langgraph_automation.apps.automation.services.runtime import (
            build_run_execution_services_from_mapping,
            load_deployment_package_config_from_settings,
        )

        deployment_package_config = load_deployment_package_config_from_settings()
        existing_config = getattr(self, "_run_execution_services_config", None)
        if existing_config is not None:
            if existing_config != deployment_package_config:
                raise ConfigError(
                    "Configuration is invalid: automation runtime services are already bound to different deployment settings.",
                    code="CONFIG_AUTOMATION_RUNTIME_ALREADY_BOUND",
                    component="automation_app",
                )
            return

        # Bind a single execution-services instance for the process lifetime.
        self.run_execution_services = build_run_execution_services_from_mapping(deployment_package_config)
        self._run_execution_services_config = deepcopy(deployment_package_config)
