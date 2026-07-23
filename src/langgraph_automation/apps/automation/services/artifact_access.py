"""Safe control-plane access to artifact bodies."""
from __future__ import annotations

from dataclasses import dataclass
import json

from langgraph_automation.apps.automation.models.artifact import Artifact
from langgraph_automation.apps.automation.services import runtime as runtime_module
from langgraph_automation.apps.automation.ui.redaction import redact_payload
from langgraph_automation.core.redaction import redact_text

_MAX_PREVIEW_BYTES = 256 * 1024
_PREVIEW_TYPES = {"application/json", "text/plain", "text/markdown"}


@dataclass(frozen=True, slots=True)
class ArtifactBody:
    artifact: Artifact
    body: bytes
    content_type: str


def load_artifact_body(artifact_id: int) -> ArtifactBody:
    artifact = Artifact.objects.select_related("run").filter(pk=artifact_id).first()
    if artifact is None:
        raise LookupError("Artifact not found")
    result = runtime_module.get_run_execution_services().read_artifact(artifact.storage_key)
    if result is None:
        raise LookupError("Artifact body not found")
    if str(result.artifact.run_id) != str(artifact.run_id):
        raise ValueError("Artifact body identity does not match control-plane metadata")
    return ArtifactBody(artifact=artifact, body=result.body, content_type=artifact.content_type or result.artifact.content_type or "application/octet-stream")


def preview_artifact_body(artifact_id: int) -> tuple[Artifact, str, str]:
    loaded = load_artifact_body(artifact_id)
    if loaded.content_type not in _PREVIEW_TYPES:
        raise ValueError("Artifact content type is not previewable")
    if len(loaded.body) > _MAX_PREVIEW_BYTES:
        raise ValueError("Artifact is too large to preview")
    text = loaded.body.decode("utf-8")
    if loaded.content_type == "application/json":
        payload = json.loads(text)
        text = json.dumps(redact_payload(payload), ensure_ascii=False, indent=2, sort_keys=True)
    else:
        text = redact_text(text)
    return loaded.artifact, text, loaded.content_type
