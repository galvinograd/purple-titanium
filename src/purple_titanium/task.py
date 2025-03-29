"""Main Task class."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .context import Context, get_current_context
from .events import Event, EventType, emit
from .lazy_output import LazyOutput
from .task_executor import TaskExecutor
from .task_mode import _task_context
from .task_signature import TaskSignature
from .task_state import TaskParameters, TaskState
from .types import TaskStatus


@dataclass(frozen=True)
class Task:
    """A task that can be executed."""
    name: str
    func: Callable
    parameters: TaskParameters = field(default_factory=TaskParameters.empty)
    context: Context = field(default_factory=get_current_context)
    task_version: int = 1
    persist: bool = False
    _state: TaskState = field(default_factory=TaskState)

    def __post_init__(self) -> None:
        """Initialize the output after the task is created."""
        persistence = getattr(self.context, '_pt_persistence', None)
        self._state.output = LazyOutput(
            owner=self,
            persistence=persistence,
        )
        self._state.signature = self._calculate_signature()

    def _calculate_signature(self) -> int:
        """Calculate a deterministic hash signature for this task."""
        return TaskSignature.calculate(
            self.name,
            self.task_version,
            self.parameters
        )

    @property
    def signature(self) -> int:
        """Get the task's signature."""
        return self._state.signature

    def __hash__(self) -> int:
        """Return a hash based on the task's signature."""
        return self._state.signature

    def __eq__(self, other: object) -> bool:
        """Compare tasks based on their signature."""
        if not isinstance(other, Task):
            return False
        return self.signature == other.signature

    @property
    def status(self) -> TaskStatus:
        return self._state.status

    @property
    def exception(self) -> Exception | None:
        return self._state.exception

    @property
    def output(self) -> 'LazyOutput':
        return self._state.output

    @property
    def dependencies(self) -> set['Task']:
        return self.parameters.get_dependencies()

    def resolve(self) -> Any:  # noqa: ANN401
        """Resolve this task by executing it and its dependencies."""
        if self.status is TaskStatus.COMPLETED:
            return self.output.value

        if self.status is TaskStatus.FAILED:
            raise self.exception

        if self.status is TaskStatus.DEP_FAILED:
            raise RuntimeError(f"Task {self.name} failed due to dependency failure")

        try:
            is_root = not _task_context.resolving_deps

            self._state.status = TaskStatus.RUNNING
            if is_root:
                emit(Event(EventType.ROOT_STARTED, self))
            emit(Event(EventType.TASK_STARTED, self))

            resolved_params = TaskExecutor.resolve_dependencies(self, self.parameters)
            result = TaskExecutor.execute_task(self, resolved_params)

            self._state.status = TaskStatus.COMPLETED
            self.output.value = result
            self.output._exists = True
            emit(Event(EventType.TASK_FINISHED, self))
            if is_root:
                emit(Event(EventType.ROOT_FINISHED, self))

            return result

        except Exception as e:
            if self._state.status not in (TaskStatus.DEP_FAILED, TaskStatus.FAILED):
                self._state.status = TaskStatus.FAILED
                self._state.exception = e
                emit(Event(EventType.TASK_FAILED, self))
                if not _task_context.resolving_deps:
                    emit(Event(EventType.ROOT_FAILED, self))

            raise 