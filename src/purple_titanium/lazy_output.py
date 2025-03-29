
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

from .persistence import OutputPersistence
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
    persistence: OutputPersistence | None = None

    def exists(self) -> bool:
        """Return whether this output has been computed."""
        if self.persistence is None:
            return self._exists
        return self.persistence.exists(self.owner.signature)

    def resolve(self) -> T:
        """Resolve this output by executing its owner task."""
        if _task_context.in_task:
            raise RuntimeError("resolve() cannot be called inside a task")
        
        if self.owner.persist and self.persistence is None:
            raise RuntimeError("resolve() requires persistence but no backend is configured")
        
        if self.owner.persist and self.persistence.exists(self.owner.signature):
            return self.persistence.load(self.owner.signature)
        
        result = self.owner.resolve()
        if self.owner.persist:
            self.persistence.save(
                key=self.owner.signature,
                data=result,
            )
        
        return result

    def __call__(self) -> T:
        """Allow LazyOutput to be called like a function."""
        return self.resolve()
