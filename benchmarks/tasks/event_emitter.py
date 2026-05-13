"""Synchronous pub/sub event emitter."""
from __future__ import annotations

from typing import Any, Callable


Listener = Callable[..., None]

_MAX_LISTENERS_PER_EVENT = 50


def validate_event_name(name: str) -> None:
    """Raise ValueError if name is empty or contains whitespace."""
    if not name or any(c.isspace() for c in name):
        raise ValueError(f"invalid event name: {name!r}")


def call_listener(listener: Listener, *args: Any, **kwargs: Any) -> None:
    """Invoke listener, swallowing exceptions to avoid breaking other listeners."""
    try:
        listener(*args, **kwargs)
    except Exception:
        pass  # listeners must not crash the emitter


class EventEmitter:
    """Simple synchronous event bus. Not thread-safe."""

    def __init__(self) -> None:
        self._listeners: dict[str, list[Listener]] = {}

    def on(self, event: str, listener: Listener) -> None:
        """Register listener for event. Silently ignores duplicates."""
        validate_event_name(event)
        bucket = self._listeners.setdefault(event, [])
        if listener not in bucket:
            if len(bucket) >= _MAX_LISTENERS_PER_EVENT:
                raise RuntimeError(
                    f"too many listeners for event {event!r} (max {_MAX_LISTENERS_PER_EVENT})"
                )
            bucket.append(listener)

    def emit(self, event: str, *args: Any, **kwargs: Any) -> int:
        """Fire all listeners for event. Returns the count of listeners called."""
        listeners = self._listeners.get(event, [])
        for listener in list(listeners):
            call_listener(listener, *args, **kwargs)
        return len(listeners)

    def off(self, event: str, listener: Listener) -> bool:
        """Unregister listener from event. Returns True if it was registered."""
        bucket = self._listeners.get(event, [])
        try:
            bucket.remove(listener)
            return True
        except ValueError:
            return False
