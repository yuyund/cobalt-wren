'''Artifact store interfaces and normalized write results.'''

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(slots=True, frozen=True)
class ArtifactWriteResult:
    '''Normalized artifact metadata returned from artifact stores.'''

    storage_key: str
    name: str
    kind: str
    content_type: str = ''
    size: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ArtifactStore(Protocol):
    def put(self, artifact: ArtifactWriteResult) -> ArtifactWriteResult: ...
    def get(self, artifact_id: str) -> ArtifactWriteResult | None: ...
    def list_for_run(self, run_id: int) -> list[ArtifactWriteResult]: ...
