"""Deployment-configurable UI access policy."""

from __future__ import annotations

from django.conf import settings
from django.http import HttpRequest


def require_login_enabled() -> bool:
    return bool(getattr(settings, "COBALT_WREN_REQUIRE_LOGIN", False))


def actor_allowed(request: HttpRequest, permission: str | None = None) -> bool:
    if not require_login_enabled():
        return True
    actor = getattr(request, "user", None)
    if actor is None or not bool(getattr(actor, "is_authenticated", False)):
        return False
    if permission is None:
        return True
    has_perm = getattr(actor, "has_perm", None)
    return bool(callable(has_perm) and has_perm(permission))


def run_action_permission(action_name: str) -> str:
    operation = (
        "resume"
        if action_name.startswith(("resume-", "integration-"))
        else action_name
    )
    return f"automation.{operation}_run"
