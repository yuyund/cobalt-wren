"""Tabler-specific presentation mappings kept inside the renderer."""
from __future__ import annotations
from django import template

register = template.Library()

_STATUS_CLASSES = {
    "running": "bg-blue-lt text-blue",
    "waiting": "bg-yellow-lt text-yellow",
    "queued": "bg-azure-lt text-azure",
    "claimed": "bg-blue-lt text-blue",
    "succeeded": "bg-green-lt text-green",
    "completed": "bg-green-lt text-green",
    "available": "bg-green-lt text-green",
    "ready": "bg-green-lt text-green",
    "loaded": "bg-green-lt text-green",
    "full": "bg-green-lt text-green",
    "partial": "bg-yellow-lt text-yellow",
    "not installed": "bg-secondary-lt text-secondary",
    "not checked": "bg-secondary-lt text-secondary",
    "none": "bg-secondary-lt text-secondary",
    "version incompatible": "bg-orange-lt text-orange",
    "load failed": "bg-red-lt text-red",
    "invalid": "bg-red-lt text-red",
    "definition mismatch": "bg-red-lt text-red",
    "failed": "bg-red-lt text-red",
    "timed out": "bg-orange-lt text-orange",
    "cancelled": "bg-secondary-lt text-secondary",
    "skipped": "bg-secondary-lt text-secondary",
    "pending": "bg-secondary-lt text-secondary",
}

@register.filter
def status_badge_class(value: object) -> str:
    normalized = str(value).strip().lower().replace("_", " ")
    return _STATUS_CLASSES.get(normalized, "bg-secondary-lt text-secondary")
