"""Core task and output classes."""

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field, is_dataclass
from inspect import signature
from typing import Any, get_type_hints

from .annotations import Ignorable, Injectable
from .context import Context, get_current_context
from .events import Event, emit
from .lazy_output import LazyOutput
from .task_mode import _task_context, enter_exec_phase, enter_resolution_phase
from .types import EventType, TaskStatus


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


class TaskFactory:
    """Creates tasks with properly processed parameters."""
    
    @staticmethod
    def _process_parameters(
        func: Callable,
        args: tuple,
        kwargs: dict,
        context: Context
    ) -> TaskParameters:
        """Process args and kwargs into TaskParameters."""
        # Get type hints for parameter processing
        type_hints = get_type_hints(func, include_extras=True)
        func_sig = signature(func)
        
        # Pre-process injectable parameters
        processed_kwargs = kwargs.copy() if kwargs else {}
        for name, param in func_sig.parameters.items():
            if name not in processed_kwargs:
                hint = type_hints.get(name)
                if hint and hasattr(hint, "__metadata__"):
                    if any(isinstance(meta, Injectable) for meta in hint.__metadata__):
                        if hasattr(context, name):
                            processed_kwargs[name] = getattr(context, name)
                        elif param.default is param.empty:
                            raise ValueError(f"Required injectable parameter '{name}' not found in context")
                        else:
                            processed_kwargs[name] = param.default
        
        # Bind args and kwargs to parameter names
        bound_args = func_sig.bind(*args, **processed_kwargs)
        bound_args.apply_defaults()
        
        # Process parameters
        filtered_params = {}
        for name, value in bound_args.arguments.items():
            if name in type_hints:
                hint = type_hints[name]
                if hasattr(hint, "__metadata__"):
                    if not any(isinstance(meta, Ignorable) for meta in hint.__metadata__):
                        filtered_params[name] = value
                else:
                    filtered_params[name] = value
            else:
                filtered_params[name] = value
                
        return TaskParameters(values=filtered_params)

    @classmethod
    def create(
        cls,
        name: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        task_version: int = 1,
        context: Context = None
    ) -> 'Task':
        """Create a new task with processed parameters."""
        if getattr(_task_context, 'in_task', False):
            raise RuntimeError("task() cannot be called inside a task")
            
        context = context or get_current_context()
        kwargs = kwargs or {}
        
        parameters = cls._process_parameters(func, args, kwargs, context)
        
        return Task(
            name=name,
            func=func,
            parameters=parameters,
            context=context,
            task_version=task_version
        )


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


@dataclass(frozen=True)
class Task:
    """A task that can be executed."""
    name: str
    func: Callable
    parameters: TaskParameters = field(default_factory=TaskParameters.empty)
    context: Context = field(default_factory=get_current_context)
    task_version: int = 1
    _state: TaskState = field(default_factory=TaskState)

    def __post_init__(self) -> None:
        """Initialize the output after the task is created."""
        self._state.output = LazyOutput(owner=self)
        self._state.signature = self._calculate_signature()

    @classmethod
    def create(
        cls,
        name: str,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        task_version: int = 1
    ) -> 'Task':
        """Create a new task with the given parameters (for backward compatibility)."""
        return TaskFactory.create(
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            task_version=task_version
        )

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
