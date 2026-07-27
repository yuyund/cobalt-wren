"""Factory context tests."""

from __future__ import annotations

from dataclasses import fields

from cobalt_wren.config.models import LimitsConfig, SafetyConfig
from cobalt_wren.runtime.context import FactoryContext
from cobalt_wren.runtime.secrets import EnvSecretResolver


def test_factory_context_contains_expected_fields_only() -> None:
    context = FactoryContext(
        environment="test",
        secrets=EnvSecretResolver(environ={"OPENAI_API_KEY": "test-key"}),
        limits=LimitsConfig(values={"max_steps": 3}),
        observability={"capture": {"input_summary": True}},
        safety=SafetyConfig(),
    )

    assert context.environment == "test"
    assert isinstance(context.secrets, EnvSecretResolver)
    assert context.limits == LimitsConfig(values={"max_steps": 3})
    assert context.observability == {"capture": {"input_summary": True}}
    assert context.safety == SafetyConfig()

    field_names = {field.name for field in fields(FactoryContext)}
    assert field_names == {"environment", "secrets", "limits", "observability", "safety"}
    assert not hasattr(context, "raw_config")
    assert not hasattr(context, "registry")
    assert not hasattr(context, "run")
