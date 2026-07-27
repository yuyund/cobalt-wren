'''Formatting helpers for dynamic UI display values.'''

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal


def format_value(value: object) -> str:
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'Yes' if value else 'No'
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
    return str(value)
