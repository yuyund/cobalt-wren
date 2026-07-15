"""Secret resolver tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from langgraph_automation.api.errors import RuntimeAssemblyError
from langgraph_automation.config.models import SecretRef
from langgraph_automation.runtime.secrets import EnvSecretResolver


def test_env_secret_resolver_resolves_env_secret_ref() -> None:
    resolver = EnvSecretResolver(environ={"OPENAI_API_KEY": "test-key"})

    assert resolver.resolve(SecretRef(source="env", name="OPENAI_API_KEY")) == "test-key"


def test_env_secret_resolver_missing_env_var_raises_runtime_assembly_error() -> None:
    resolver = EnvSecretResolver(environ={})

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        resolver.resolve(SecretRef(source="env", name="OPENAI_API_KEY"))

    assert excinfo.value.code == "RUNTIME_ASSEMBLY_SECRET_MISSING"
    assert excinfo.value.component == "runtime_assembly"
    assert excinfo.value.metadata == {"secret_name": "OPENAI_API_KEY"}
    assert "test-key" not in excinfo.value.safe_message


def test_env_secret_resolver_unsupported_source_raises_runtime_assembly_error() -> None:
    resolver = EnvSecretResolver(environ={"OPENAI_API_KEY": "test-key"})
    ref = SimpleNamespace(source="file", name="OPENAI_API_KEY")

    with pytest.raises(RuntimeAssemblyError) as excinfo:
        resolver.resolve(ref)

    assert excinfo.value.code == "RUNTIME_ASSEMBLY_UNSUPPORTED_SECRET_SOURCE"
    assert excinfo.value.metadata == {"secret_source": "file"}
