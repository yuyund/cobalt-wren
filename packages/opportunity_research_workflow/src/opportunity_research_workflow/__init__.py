"""Opportunity research workflow distribution."""

from .plugin import PLUGIN_NAME, WORKFLOW_KIND, create_plugin
from .search import SearXNGSearchTool

__all__ = ["PLUGIN_NAME", "WORKFLOW_KIND", "SearXNGSearchTool", "create_plugin"]
