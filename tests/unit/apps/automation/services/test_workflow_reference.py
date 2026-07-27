"""Control-plane workflow reference schema tests."""
from __future__ import annotations

import pytest

from cobalt_wren.apps.automation.services.errors import WorkflowConfigurationError
from cobalt_wren.apps.automation.services.workflow_reference import parse_workflow_reference


def test_missing_workflow_section_selects_legacy_path() -> None:
    assert parse_workflow_reference({}) is None


def test_public_workflow_reference_parses_kind_and_config() -> None:
    reference = parse_workflow_reference(
        {"workflow": {"kind": " acme.review ", "config": {"mode": "strict"}}}
    )
    assert reference is not None
    assert reference.kind == "acme.review"
    assert reference.config == {"mode": "strict"}


@pytest.mark.parametrize(
    "payload",
    [
        {"workflow": "acme.review"},
        {"workflow": {}},
        {"workflow": {"kind": ""}},
        {"workflow": {"kind": "acme.review", "config": []}},
    ],
)
def test_invalid_reference_fails_as_workflow_configuration(payload) -> None:
    with pytest.raises(WorkflowConfigurationError):
        parse_workflow_reference(payload)
