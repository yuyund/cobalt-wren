"""Django app config for the automation control plane."""

from __future__ import annotations

from django.apps import AppConfig


class AutomationConfig(AppConfig):
    """App config for automation models, services, selectors, and UI specs."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "langgraph_automation.apps.automation"
    label = "automation"

    def ready(self) -> None:
        from langgraph_automation.apps.automation.services.runtime import build_run_execution_services_from_mapping

        # Bind a single execution-services instance for the process lifetime.
        self.run_execution_services = build_run_execution_services_from_mapping({"version": 1})
