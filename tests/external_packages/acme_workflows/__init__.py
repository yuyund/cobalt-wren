"""Example external workflow package using only the public plugin SPI."""

from tests.external_packages.acme_workflows.plugin import (
    EXTERNAL_PLUGIN_NAME,
    EXTERNAL_WORKFLOW_KIND,
    ExternalGraph,
    create_plugin,
)

__all__ = [
    "EXTERNAL_PLUGIN_NAME",
    "EXTERNAL_WORKFLOW_KIND",
    "ExternalGraph",
    "create_plugin",
]
