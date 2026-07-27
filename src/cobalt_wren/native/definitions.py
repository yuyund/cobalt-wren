"""Reusable Native step definitions."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from cobalt_wren.native.policies import RetryPolicy

R = TypeVar("R")


@dataclass(frozen=True, slots=True)
class NativeStepDefinition(Generic[R]):
    """Reusable callable plus its default Native execution policy."""

    name: str
    function: Callable[..., R] | Callable[..., Awaitable[R]]
    retry: RetryPolicy | None = None
    timeout_seconds: float | None = None


def step(
    name: str,
    function: Callable[..., R] | Callable[..., Awaitable[R]],
    *,
    retry: RetryPolicy | None = None,
    timeout_seconds: float | None = None,
) -> NativeStepDefinition[R]:
    return NativeStepDefinition(
        name=name,
        function=function,
        retry=retry,
        timeout_seconds=timeout_seconds,
    )


__all__ = ["NativeStepDefinition", "step"]
