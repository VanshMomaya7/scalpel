"""LRU cache with per-entry TTL."""
from __future__ import annotations

import time
from collections import OrderedDict
from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")

_DEFAULT_CAPACITY = 256
_DEFAULT_TTL = 300.0  # seconds


def make_cache_key(*parts: str) -> str:
    """Join parts with ':' to form a namespaced cache key."""
    return ":".join(parts)


def is_expired(created_at: float, ttl: float) -> bool:
    """Return True if the entry is older than ttl seconds."""
    return (time.monotonic() - created_at) > ttl


class LRUCache(Generic[K, V]):
    """Least-recently-used cache with optional per-entry TTL."""

    def __init__(self, capacity: int = _DEFAULT_CAPACITY, ttl: float = _DEFAULT_TTL) -> None:
        self._capacity = capacity
        self._ttl = ttl
        # OrderedDict preserves insertion order; move_to_end() implements LRU
        self._store: OrderedDict[K, tuple[V, float]] = OrderedDict()

    def get(self, key: K) -> V | None:
        """Return the cached value or None if missing/expired."""
        entry = self._store.get(key)
        if entry is None:
            return None
        value, created_at = entry
        if is_expired(created_at, self._ttl):
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return value

    def set(self, key: K, value: V) -> None:
        """Insert or update key, evicting the LRU entry if at capacity."""
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = (value, time.monotonic())
        if len(self._store) > self._capacity:
            self._store.popitem(last=False)

    def evict(self, key: K) -> bool:
        """Explicitly remove a key. Returns True if it was present."""
        return self._store.pop(key, None) is not None
