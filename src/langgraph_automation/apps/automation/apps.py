"""Django app config for the automation control plane."""

from __future__ import annotations

from django.apps import AppConfig


class AutomationConfig(AppConfig):
    """App config for automation models, services, selectors, and UI specs."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "langgraph_automation.apps.automation"
    label = "automation"
