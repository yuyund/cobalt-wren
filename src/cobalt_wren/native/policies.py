"""Public execution policies for Native Authoring."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Explicit step retry policy.

    Retrying does not imply that a callable is idempotent. Authors must opt in
    only when repeating the side effects is safe for their application.
    """

    max_attempts: int = 1
    retry_on: tuple[type[Exception], ...] = (Exception,)
    initial_delay_seconds: float = 0.0
    backoff_multiplier: float = 2.0
    max_delay_seconds: float = 60.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if not self.retry_on:
            raise ValueError("retry_on must not be empty")
        if any(
            not isinstance(item, type) or not issubclass(item, Exception)
            for item in self.retry_on
        ):
            raise TypeError("retry_on must contain Exception types")
        if self.initial_delay_seconds < 0:
            raise ValueError("initial_delay_seconds must not be negative")
        if self.backoff_multiplier < 1:
            raise ValueError("backoff_multiplier must be at least 1")
        if self.max_delay_seconds < 0:
            raise ValueError("max_delay_seconds must not be negative")

    def should_retry(self, error: Exception, *, attempt: int) -> bool:
        return attempt < self.max_attempts and isinstance(error, self.retry_on)

    def delay_after(self, attempt: int) -> float:
        if self.initial_delay_seconds == 0:
            return 0.0
        delay = self.initial_delay_seconds * (self.backoff_multiplier ** (attempt - 1))
        return min(delay, self.max_delay_seconds)


NO_RETRY = RetryPolicy()

__all__ = ["NO_RETRY", "RetryPolicy"]
