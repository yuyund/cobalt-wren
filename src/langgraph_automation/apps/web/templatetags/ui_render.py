'''Template helpers for rendering dynamic UI specs.'''

from __future__ import annotations

from django import template

register = template.Library()


@register.filter
def display_value(value: object) -> str:
    return '' if value is None else str(value)
