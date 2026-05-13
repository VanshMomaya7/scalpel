"""Retry with exponential backoff and jitter."""
from __future__ import annotations

import random
import time
from typing import Callable, TypeVar

T = TypeVar("T")

_BASE_DELAY = 0.1   # seconds
_MAX_DELAY = 30.0   # seconds
_MAX_ATTEMPTS = 5


def backoff_delay(attempt: int, base: float = _BASE_DELAY, cap: float = _MAX_DELAY) -> float:
    """Return full-jitter exponential backoff delay for attempt number (0-indexed)."""
    ceiling = min(cap, base * (2**attempt))
    return random.uniform(0, ceiling)


def is_retryable(exc: BaseException) -> bool:
    """Return True for transient errors that should trigger a retry."""
    # Retry on connection errors and timeouts; not on value/type errors
    return isinstance(exc, (OSError, TimeoutError, ConnectionError))


class RetryHandler:
    """Wraps a callable with configurable retry logic."""

    def __init__(
        self,
        max_attempts: int = _MAX_ATTEMPTS,
        base_delay: float = _BASE_DELAY,
        retryable: Callable[[BaseException], bool] = is_retryable,
    ) -> None:
        self._max_attempts = max_attempts
        self._base_delay = base_delay
        self._retryable = retryable

    def run(self, fn: Callable[[], T]) -> T:
        """Call fn, retrying on retryable exceptions up to max_attempts times."""
        last_exc: BaseException | None = None
        for attempt in range(self._max_attempts):
            try:
                return fn()
            except BaseException as exc:
                if not self._retryable(exc) or attempt == self._max_attempts - 1:
                    raise
                last_exc = exc
                delay = backoff_delay(attempt, self._base_delay)
                time.sleep(delay)
        # unreachable, but satisfies type checker
        raise RuntimeError("retry loop exited without returning") from last_exc

    def should_retry(self, exc: BaseException, attempt: int) -> bool:
        """Return True if the exception and attempt count permit another try."""
        return self._retryable(exc) and attempt < self._max_attempts - 1
