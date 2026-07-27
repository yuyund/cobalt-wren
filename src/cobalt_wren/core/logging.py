"""Logging configuration entrypoint."""

from __future__ import annotations

import logging


def configure_logging(level: int | str = logging.INFO) -> None:
    """Configure process logging for Django and graph execution."""

    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
