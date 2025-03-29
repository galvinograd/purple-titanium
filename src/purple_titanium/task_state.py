"""Task state and parameters classes."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .lazy_output import LazyOutput
from .types import TaskStatus

if TYPE_CHECKING:
    from .task import Task


@dataclass
class TaskState:
    """Mutable state for a task."""
    status: TaskStatus = TaskStatus.PENDING
    exception: Exception | None = None
    output: LazyOutput | None = None
    signature: int = 0  # Task signature for caching and identification


@dataclass(frozen=True)
class TaskParameters:
    """Represents the parameters of a task."""
    values: dict[str, Any] = field(default_factory=dict)
    
    def get_dependencies(self) -> set['Task']:
        """Get all task dependencies from parameters."""
        dependencies = set()
        for value in self.values.values():
            if isinstance(value, LazyOutput):
                dependencies.add(value.owner)
        return dependencies

    @classmethod
    def empty(cls) -> 'TaskParameters':
        """Create an empty TaskParameters instance."""
        return cls() 