"""Token-bucket rate limiter."""
from __future__ import annotations

import time


_DEFAULT_RATE = 10.0   # tokens per second
_DEFAULT_BURST = 20.0  # maximum token bucket capacity


def compute_tokens(current: float, rate: float, capacity: float, last_refill: float) -> float:
    """Calculate the token count after refilling since last_refill."""
    elapsed = time.monotonic() - last_refill
    refilled = current + elapsed * rate
    return min(refilled, capacity)


def tokens_needed(weight: int = 1) -> int:
    """Return how many tokens a request of the given weight costs."""
    return max(1, weight)


class RateLimiter:
    """Token-bucket rate limiter. Thread-unsafe; wrap with a lock if needed."""

    def __init__(self, rate: float = _DEFAULT_RATE, burst: float = _DEFAULT_BURST) -> None:
        self._rate = rate        # tokens replenished per second
        self._capacity = burst   # bucket max size
        self._tokens = burst     # start full
        self._last_refill = time.monotonic()

    def allow(self, weight: int = 1) -> bool:
        """Consume weight tokens. Returns True if allowed, False if throttled."""
        self._refill()
        cost = tokens_needed(weight)
        if self._tokens >= cost:
            self._tokens -= cost
            return True
        return False

    def _refill(self) -> None:
        """Top up the bucket based on elapsed time."""
        now = time.monotonic()
        self._tokens = compute_tokens(self._tokens, self._rate, self._capacity, self._last_refill)
        self._last_refill = now

    def wait_time(self, weight: int = 1) -> float:
        """Return the seconds until weight tokens will be available (0 if already available)."""
        self._refill()
        deficit = tokens_needed(weight) - self._tokens
        if deficit <= 0:
            return 0.0
        return deficit / self._rate
