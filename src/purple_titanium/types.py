"""Type definitions for purple-titanium."""

from enum import Enum, auto
from typing import Generic, TypeVar


class EventType(Enum):
    """Event types for task execution."""
    TASK_STARTED = auto()
    TASK_FINISHED = auto()
    TASK_FAILED = auto()
    TASK_DEP_FAILED = auto()


class TaskStatus(Enum):
    """Status of a task."""
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    DEP_FAILED = auto()


T = TypeVar('T')


class Injectable(Generic[T]):
    """Type hint for injectable parameters."""
    
    def __init__(self, type_: type[T]) -> None:
        """Initialize the injectable type."""
        self.type = type_
    
    def __class_getitem__(cls, item: type[T]) -> 'Injectable[T]':
        """Create an Injectable type with the given type parameter."""
        return cls(item)
    
    def __repr__(self) -> str:
        """Return a string representation of the injectable type."""
        return f"Injectable[{self.type.__name__}]" 