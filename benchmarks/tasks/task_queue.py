"""Simple bounded FIFO task queue with priority support."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar("T")

_DEFAULT_MAXSIZE = 1000


@dataclass(order=True)
class QueueItem(Generic[T]):
    priority: int
    enqueued_at: float = field(compare=False)
    payload: T = field(compare=False)


def make_item(payload: T, priority: int = 0) -> QueueItem[T]:
    """Wrap payload in a QueueItem with the current timestamp."""
    return QueueItem(priority=priority, enqueued_at=time.monotonic(), payload=payload)


def drain(items: list[QueueItem[T]], predicate: object) -> list[QueueItem[T]]:
    """Remove and return all items matching predicate(item) == True."""
    matching = [it for it in items if predicate(it)]  # type: ignore[operator]
    for it in matching:
        items.remove(it)
    return matching


class TaskQueue(Generic[T]):
    """Bounded FIFO queue with optional priority ordering."""

    def __init__(self, maxsize: int = _DEFAULT_MAXSIZE) -> None:
        self._maxsize = maxsize
        self._items: list[QueueItem[T]] = []

    def enqueue(self, payload: T, priority: int = 0) -> bool:
        """Add a task. Returns False without enqueuing if the queue is full."""
        if len(self._items) >= self._maxsize:
            return False
        self._items.append(make_item(payload, priority))
        # Higher priority items float to the front
        self._items.sort(reverse=True)
        return True

    def dequeue(self) -> T | None:
        """Remove and return the highest-priority item, or None if empty."""
        if not self._items:
            return None
        return self._items.pop(0).payload

    def peek(self) -> T | None:
        """Return the next item without removing it."""
        return self._items[0].payload if self._items else None
