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
                    if isinstance(value, LazyOutput):
                        resolved_params[name] = value.resolve()
                    elif isinstance(value, dict):
                        resolved_params[name] = {k: v.resolve() if isinstance(v, LazyOutput) else v for k, v in value.items()}
                    elif isinstance(value, list):
                        resolved_params[name] = [v.resolve() if isinstance(v, LazyOutput) else v for v in value]
                    elif isinstance(value, tuple):
                        resolved_params[name] = tuple(v.resolve() if isinstance(v, LazyOutput) else v for v in value)
                    else:
                        resolved_params[name] = value
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