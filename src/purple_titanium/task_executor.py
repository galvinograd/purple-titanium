"""Task execution and dependency resolution."""

from typing import TYPE_CHECKING, Any

from .events import Event, EventType, emit
from .lazy_output import LazyOutput
from .task_mode import _task_context, enter_exec_phase, enter_resolution_phase
from .task_state import TaskParameters
from .types import TaskStatus

if TYPE_CHECKING:
    from .task import Task


class TaskExecutor:
    """Handles task execution and dependency resolution."""
    
    @staticmethod
    def resolve_dependencies(task: 'Task', parameters: TaskParameters) -> dict[str, Any]:
        """Resolve task dependencies."""
        resolved_params = {}
        
        with enter_resolution_phase():
            for name, value in parameters.values.items():
                try:
                    resolved_params[name] = value.resolve() if isinstance(value, LazyOutput) else value
                except Exception as e:
                    if not _task_context.in_task:
                        task._state.status = TaskStatus.DEP_FAILED
                        task._state.exception = e
                        emit(Event(EventType.TASK_DEP_FAILED, task))
                        raise
                    resolved_params[name] = None
                    
        return resolved_params

    @staticmethod
    def execute_task(task: 'Task', resolved_params: dict[str, Any]) -> Any:  # noqa: ANN401
        """Execute the task function with the given parameters."""
        with enter_exec_phase(), task.context:
            return task.func(**resolved_params) 