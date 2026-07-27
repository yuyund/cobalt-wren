"""Safe append-only operation auditing."""
from __future__ import annotations

from collections.abc import Mapping

from cobalt_wren.apps.automation.models.audit import OperationAuditLog
from cobalt_wren.apps.automation.models.run import Run
from cobalt_wren.core.result_safety import safe_run_output_payload


def actor_identifier(actor: object | None) -> str:
    if actor is None:
        return "system"
    getter = getattr(actor, "get_username", None)
    if callable(getter):
        value = str(getter()).strip()
        if value:
            return value[:255]
    value = str(getattr(actor, "pk", "") or "").strip()
    return value[:255] if value else "anonymous"


def record_operation(*, actor: object | None, action: str, target_type: str, target_id: object, outcome: str, run: Run | None = None, payload: Mapping[str, object] | None = None, message: str = "") -> OperationAuditLog:
    return OperationAuditLog.objects.create(
        actor_identifier=actor_identifier(actor),
        action=action[:100],
        target_type=target_type[:100],
        target_id=str(target_id)[:100],
        run=run,
        outcome=outcome[:32],
        payload_summary=safe_run_output_payload(dict(payload or {})),
        message=message[:500],
    )
