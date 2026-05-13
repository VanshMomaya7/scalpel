"""Schema-based data validation and coercion."""
from __future__ import annotations

from typing import Any


class ValidationError(Exception):
    """Raised when a value fails schema validation."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


def coerce_int(value: Any) -> int:
    """Cast value to int, raising ValueError on failure."""
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"cannot coerce {value!r} to int") from exc


def coerce_bool(value: Any) -> bool:
    """Coerce common truthy strings and numeric values to bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        if value.lower() in {"true", "yes", "1"}:
            return True
        if value.lower() in {"false", "no", "0"}:
            return False
    raise ValueError(f"cannot coerce {value!r} to bool")


class Validator:
    """Validates a dict of fields against a schema definition."""

    def __init__(self, schema: dict[str, type]) -> None:
        # schema maps field name to expected Python type
        self._schema = schema

    def validate(self, data: dict[str, Any]) -> None:
        """Raise ValidationError for the first field that fails type check."""
        for field, expected_type in self._schema.items():
            if field not in data:
                raise ValidationError(field, "required field is missing")
            if not isinstance(data[field], expected_type):
                actual = type(data[field]).__name__
                raise ValidationError(
                    field,
                    f"expected {expected_type.__name__}, got {actual}",
                )

    def coerce(self, data: dict[str, Any]) -> dict[str, Any]:
        """Return a copy of data with values cast to their schema types."""
        result: dict[str, Any] = {}
        for field, expected_type in self._schema.items():
            raw = data.get(field)
            if raw is None:
                raise ValidationError(field, "required field is missing")
            try:
                result[field] = expected_type(raw)
            except (TypeError, ValueError) as exc:
                raise ValidationError(field, str(exc)) from exc
        return result
