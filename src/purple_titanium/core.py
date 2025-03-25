import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Generic, Optional, TypeVar

from .events import Event, emit
from .types import EventType, TaskStatus

T = TypeVar('T')

# Thread-local storage for tracking task initialization and resolution
_task_context = threading.local()
_task_context.in_task = False
_task_context.resolving_deps = False

class _TaskContext:
    def __init__(self) -> None:
        self.in_task = False

_task_context = _TaskContext()

@contextmanager
def task_context() -> Iterator[None]:
    """Context manager to track when we're inside a task execution."""
    prev = _task_context.in_task
    _task_context.in_task = True
    try:
        yield
    finally:
        _task_context.in_task = prev

@contextmanager
def _dependency_resolution_context() -> Iterator[None]:
    """Context manager for tracking dependency resolution."""
    old_resolving_deps = getattr(_task_context, 'resolving_deps', False)
    _task_context.resolving_deps = True
    try:
        yield
    finally:
        _task_context.resolving_deps = old_resolving_deps

@dataclass
class TaskState:
    """Mutable state for a task."""
    status: TaskStatus = TaskStatus.PENDING
    exception: Exception | None = None
    output: Optional['LazyOutput'] = None

@dataclass(frozen=True)
class Task:
    """A task that can be executed."""
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    dependencies: set['Task'] = field(default_factory=set)
    _state: TaskState = field(default_factory=TaskState)

    def __post_init__(self) -> None:
        """Initialize the output after the task is created."""
        if getattr(_task_context, 'in_task', False):
            raise RuntimeError("task() cannot be called inside a task")
        self._state.output = LazyOutput(owner=self)

    def __hash__(self) -> int:
        """Return a hash based on the task's name and function."""
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        """Compare tasks based on their name and function."""
        if not isinstance(other, Task):
            return False
        return self.name == other.name and self.func == other.func

    @property
    def status(self) -> TaskStatus:
        return self._state.status

    @property
    def exception(self) -> Exception | None:
        return self._state.exception

    @property
    def output(self) -> 'LazyOutput':
        return self._state.output

    
    def resolve(self) -> Any:  # noqa: ANN401
        """Resolve this task by executing it and its dependencies."""
        if self.status is TaskStatus.COMPLETED:
            return self.output.value

        if self.status is TaskStatus.FAILED:
            raise self.exception

        if self.status is TaskStatus.DEP_FAILED:
            raise RuntimeError(f"Task {self.name} failed due to dependency failure")

        try:
            # Update status and emit event
            self._state.status = TaskStatus.RUNNING
            emit(Event(EventType.TASK_STARTED, self))

            # Resolve dependencies first
            with _dependency_resolution_context():
                resolved_args = []
                resolved_kwargs = {}
                
                # Try to resolve each argument
                for arg in self.args:
                    try:
                        resolved_args.append(arg.resolve() if isinstance(arg, LazyOutput) else arg)
                    except Exception as e:
                        if not _task_context.in_task:
                            # Only propagate errors if we're not in a task
                            self._state.status = TaskStatus.DEP_FAILED
                            self._state.exception = e
                            emit(Event(EventType.TASK_DEP_FAILED, self))
                            raise
                        resolved_args.append(None)  # Allow the task to handle the error
                
                # Try to resolve each kwarg
                for key, value in self.kwargs.items():
                    try:
                        resolved_kwargs[key] = value.resolve() if isinstance(value, LazyOutput) else value
                    except Exception as e:
                        if not _task_context.in_task:
                            # Only propagate errors if we're not in a task
                            self._state.status = TaskStatus.DEP_FAILED
                            self._state.exception = e
                            emit(Event(EventType.TASK_DEP_FAILED, self))
                            raise
                        resolved_kwargs[key] = None  # Allow the task to handle the error

            # Execute the task function with task context
            with task_context():
                result = self.func(*resolved_args, **resolved_kwargs)

            # Update status and output
            self._state.status = TaskStatus.COMPLETED
            self.output.value = result
            self.output._exists = True
            emit(Event(EventType.TASK_FINISHED, self))

            return result

        except Exception as e:
            # Update status and emit event
            if self._state.status not in (TaskStatus.DEP_FAILED, TaskStatus.FAILED):
                self._state.status = TaskStatus.FAILED
                self._state.exception = e
                emit(Event(EventType.TASK_FAILED, self))

            raise 

@dataclass
class LazyOutput(Generic[T]):
    """A lazy output that will be computed when needed."""
    owner: Task
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