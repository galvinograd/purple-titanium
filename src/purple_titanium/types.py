"""Type definitions for purple-titanium."""

from enum import Enum, auto


class TaskStatus(Enum):
    """Status of a task."""
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    DEP_FAILED = auto()

class EventType(Enum):
    """Types of events that can occur during task execution."""
    TASK_STARTED = auto()
    TASK_FINISHED = auto()
    TASK_FAILED = auto()
    TASK_DEP_FAILED = auto()
    ROOT_STARTED = auto()
    ROOT_FINISHED = auto()
    ROOT_FAILED = auto()
