"""Secret resolution helpers for runtime assembly."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from langgraph_automation.api.errors import RuntimeAssemblyError
from langgraph_automation.config.models import SecretRef

__all__ = ["EnvSecretResolver", "SecretResolver"]


class SecretResolver(Protocol):
    def resolve(self, ref: SecretRef) -> str:
        """Resolve a secret reference into its runtime value."""


@dataclass(frozen=True, slots=True)
class EnvSecretResolver:
    environ: Mapping[str, str] | None = None

    def resolve(self, ref: SecretRef) -> str:
        source = getattr(ref, "source", None)
        if source != "env":
            raise self._error(
                "Runtime assembly failed: unsupported secret source.",
                code="RUNTIME_ASSEMBLY_UNSUPPORTED_SECRET_SOURCE",
                metadata={"secret_source": source},
            )

        name = getattr(ref, "name", "")
        environ = self.environ if self.environ is not None else os.environ
        if name not in environ:
            raise self._error(
                f"Runtime assembly failed: secret environment variable '{name}' is missing.",
                code="RUNTIME_ASSEMBLY_SECRET_MISSING",
                metadata={"secret_name": name},
            )
        return environ[name]

    @staticmethod
    def _error(safe_message: str, *, code: str, metadata: dict[str, object]) -> RuntimeAssemblyError:
        return RuntimeAssemblyError(safe_message, code=code, component="runtime_assembly", metadata=metadata)
