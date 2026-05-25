"""Field-level reducer registry for StateSchema.

Scans Annotated[type, reducer] annotations on StateSchema subclasses
and applies per-field reduce semantics during state transitions.
"""

from __future__ import annotations

from typing import Any, Dict, get_args, get_origin, get_type_hints, Annotated


def _is_reducer_annotation(obj: Any) -> bool:
    """Check if an Annotated argument is a reducer (callable with __call__)."""
    return callable(obj) and not isinstance(obj, type)


class FieldReducerRegistry:
    """Extracts and applies per-field reducers from StateSchema annotations."""

    def __init__(self, reducers: Dict[str, Any] | None = None, ephemeral_fields: set | None = None):
        self._reducers: Dict[str, Any] = reducers or {}
        self._ephemeral_fields: set = ephemeral_fields or set()

    @classmethod
    def from_schema(cls, schema_class: type) -> "FieldReducerRegistry":
        """Scan a StateSchema subclass for Annotated[type, reducer] fields."""
        reducers: Dict[str, Any] = {}
        ephemeral_fields: set = set()

        try:
            hints = get_type_hints(schema_class, include_extras=True)
        except Exception:
            hints = {}

        for field_name, hint in hints.items():
            if get_origin(hint) is Annotated:
                args = get_args(hint)
                for arg in args[1:]:
                    # Handle reducer classes (Append, Replace, Ephemeral) — instantiate first
                    if isinstance(arg, type):
                        if callable(getattr(arg, "__call__", None)):
                            instance = arg()
                            reducers[field_name] = instance
                            if hasattr(instance, "reset_value"):
                                ephemeral_fields.add(field_name)
                            break
                        continue
                    # Handle class instances (Append(), Replace(), Ephemeral())
                    if hasattr(arg, "reset_value"):
                        ephemeral_fields.add(field_name)
                        reducers[field_name] = arg
                        break
                    # Handle bare callable reducers (functions)
                    if _is_reducer_annotation(arg):
                        reducers[field_name] = arg
                        break

        return cls(reducers=reducers, ephemeral_fields=ephemeral_fields)

    def has_reducer(self, field_name: str) -> bool:
        return field_name in self._reducers

    def is_ephemeral(self, field_name: str) -> bool:
        return field_name in self._ephemeral_fields

    def apply(self, field_name: str, current: Any, update: Any) -> Any:
        """Apply reducer for a single field. Default: last-value-wins (Replace)."""
        if field_name in self._reducers:
            return self._reducers[field_name](current, update)
        return update

    def apply_all(self, current_state: Any, update_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Apply reducers for all fields in update_dict against current_state."""
        result = {}
        for key, update_value in update_dict.items():
            current_value = getattr(current_state, key, None)
            result[key] = self.apply(key, current_value, update_value)
        return result

    def reset_ephemeral(self, state: Any) -> None:
        """Reset ephemeral fields to their reset_value (default: None)."""
        for field_name in self._ephemeral_fields:
            if hasattr(state, field_name):
                reducer = self._reducers.get(field_name)
                reset_value = getattr(reducer, "reset_value", None) if reducer else None
                setattr(state, field_name, reset_value)
