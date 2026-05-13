"""INI-style configuration file parser with type coercion."""
from __future__ import annotations

import pathlib
from typing import Any


_COMMENT_PREFIXES = ("#", ";")


def parse_line(line: str) -> tuple[str, str] | None:
    """Parse a 'key = value' line. Returns None for blank/comment lines."""
    stripped = line.strip()
    if not stripped or stripped[0] in _COMMENT_PREFIXES:
        return None
    if "=" not in stripped:
        return None
    key, _, value = stripped.partition("=")
    return key.strip(), value.strip()


def load_file(path: str | pathlib.Path) -> dict[str, str]:
    """Read a config file and return a flat key→value mapping."""
    result: dict[str, str] = {}
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        pair = parse_line(line)
        if pair is not None:
            result[pair[0]] = pair[1]
    return result


class Config:
    """Typed config container backed by a flat string dict."""

    def __init__(self, data: dict[str, str]) -> None:
        self._data = data

    def get(self, key: str, default: str | None = None) -> str | None:
        """Return the raw string value for key, or default if not present."""
        return self._data.get(key, default)

    def get_int(self, key: str, default: int = 0) -> int:
        """Return key as int, falling back to default if missing or unparseable."""
        raw = self._data.get(key)
        if raw is None:
            return default
        try:
            return int(raw)
        except ValueError:
            return default

    def set(self, key: str, value: Any) -> None:
        """Store a value, coercing it to str."""
        self._data[key] = str(value)
