
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

from .task_mode import _task_context

if TYPE_CHECKING:
    from .core import Task

T = TypeVar('T')

@dataclass
class LazyOutput(Generic[T]):
    """A lazy output that will be computed when needed."""
    owner: 'Task'
    value: T | None = None
    _exists: bool = False

    def exists(self) -> bool:
        """Return whether this output has been computed."""
        return self._exists

    def resolve(self) -> T:
        """Resolve this output by executing its owner task."""
        if _task_context.in_task:
            raise RuntimeError("resolve() cannot be called inside a task")
        return self.owner.resolve()

    def __call__(self) -> T:
        """Allow LazyOutput to be called like a function."""
        return self.resolve()
