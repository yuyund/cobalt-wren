"""Tests for the intentionally empty built-in workflow catalog."""

from __future__ import annotations

import pytest

from cobalt_wren.api.errors import PluginResolutionError
from cobalt_wren.plugins.registry import PluginRegistry
from cobalt_wren.workflows.catalog import (
    create_builtin_workflow_registry,
    get_builtin_workflow_plugins,
    register_builtin_workflows,
)


def test_builtin_workflow_catalog_is_empty_until_product_workflows_exist() -> None:
    assert get_builtin_workflow_plugins() == ()


def test_register_builtin_workflows_is_a_noop_for_empty_catalog() -> None:
    registry = PluginRegistry()

    register_builtin_workflows(registry)

    assert registry.list_plugins() == ()


def test_create_builtin_workflow_registry_contains_no_implicit_examples() -> None:
    registry = create_builtin_workflow_registry()

    assert registry.list_plugins() == ()
    with pytest.raises(PluginResolutionError):
        registry.get_workflow("examples.native.document-summary")
