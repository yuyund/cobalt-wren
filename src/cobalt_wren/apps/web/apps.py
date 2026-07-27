"""Django app config for the web UI."""

from __future__ import annotations

from django.apps import AppConfig


class WebConfig(AppConfig):
    """Web UI app config."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "cobalt_wren.apps.web"
