"""Task signature calculation and parameter hashing."""

import hashlib
from dataclasses import is_dataclass
from typing import Any, get_type_hints

from .annotations import Ignorable
from .lazy_output import LazyOutput
from .task_state import TaskParameters


class TaskSignature:
    """Handles task signature calculation and parameter hashing."""
    
    @staticmethod
    def _hash_parameters(parameters: TaskParameters) -> tuple:
        """Convert parameters into a hashable tuple."""
        return tuple(
            (name, TaskSignature._hash_value(value))
            for name, value in sorted(parameters.values.items())
        )

    @staticmethod
    def _hash_value(value: Any) -> Any:  # noqa: ANN401
        """Convert a value into a hashable form."""
        if isinstance(value, str):
            return value
        if isinstance(value, LazyOutput):
            return value.owner.signature
        if isinstance(value, (list | tuple)):
            return (type(value).__name__, len(value), tuple(TaskSignature._hash_value(item) for item in value))
        if isinstance(value, dict):
            return ('dict', tuple(
                (TaskSignature._hash_value(key), TaskSignature._hash_value(val))
                for key, val in sorted(value.items())
            ))
        if is_dataclass(value):
            type_hints = get_type_hints(type(value), include_extras=True)
            fields = {}
            for field_name, field_value in value.__dict__.items():
                if field_name in type_hints:
                    hint = type_hints[field_name]
                    if hasattr(hint, "__metadata__"):
                        if not any(isinstance(meta, Ignorable) for meta in hint.__metadata__):
                            fields[field_name] = TaskSignature._hash_value(field_value)
                    else:
                        fields[field_name] = TaskSignature._hash_value(field_value)
                else:
                    fields[field_name] = TaskSignature._hash_value(field_value)
            return ('dataclass', type(value).__name__, tuple(sorted(fields.items())))
        return (type(value).__name__, str(value))

    @staticmethod
    def calculate(name: str, version: int, parameters: TaskParameters) -> int:
        """Calculate a deterministic hash signature for a task."""
        components = (name, version, TaskSignature._hash_parameters(parameters))
        components_str = str(components).encode('utf-8')
        return int(hashlib.sha256(components_str).hexdigest(), 16) % (10**10) 