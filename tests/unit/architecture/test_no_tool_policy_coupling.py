"""Architecture guard for tool policy boundaries."""

from __future__ import annotations

from pathlib import Path


def test_tool_policy_modules_do_not_depend_on_django_or_graphs() -> None:
    policy = Path('src/cobalt_wren/integrations/tools/policy.py').read_text()
    policy_registry = Path('src/cobalt_wren/integrations/tools/policy_registry.py').read_text()

    for text in [policy, policy_registry]:
        assert 'django.db' not in text
        assert 'django.models' not in text
        assert 'apps.web' not in text
        assert 'apps.automation' not in text
        assert 'EventSink' not in text
        assert 'graphs.' not in text


def test_observed_tool_registry_does_not_import_policy_internals() -> None:
    text = Path('src/cobalt_wren/integrations/tools/observed_registry.py').read_text()
    assert 'PolicyAwareToolRegistry' not in text
    assert 'AllowlistToolPolicy' not in text
