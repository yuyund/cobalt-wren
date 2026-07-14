"""Graph execution package.

This package intentionally avoids eager re-exports to prevent import cycles
between graph selection metadata, runtime wiring, and concrete graph builders.
It is the execution foundation layer, not an application workflow package.
"""

from __future__ import annotations

__all__: list[str] = []
