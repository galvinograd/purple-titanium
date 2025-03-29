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
class Task:
    """A task that can be executed."""
    name: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    _state: TaskState = field(default_factory=TaskState)
    context: Context = field(default_factory=get_current_context)
    task_version: int = 1

    def __post_init__(self) -> None:
        """Initialize the output after the task is created."""
        if getattr(_task_context, 'in_task', False):
            raise RuntimeError("task() cannot be called inside a task")
        self._state.output = LazyOutput(owner=self)
        # Calculate signature during initialization
        self._state.signature = self._calculate_signature()

    def _build_parameter_dict(self) -> dict[str, Any]:
        """Convert args and kwargs into a single parameter dictionary using parameter names."""
        func_sig = signature(self.func)
        bound_args = func_sig.bind(*self.args, **self.kwargs)
        bound_args.apply_defaults()
        
        # Get type hints to check for ignored parameters
        type_hints = get_type_hints(self.func, include_extras=True)
        
        # Filter out ignored parameters
        filtered_params = {}
        for name, value in bound_args.arguments.items():
            if name in type_hints:
                hint = type_hints[name]
                if hasattr(hint, "__metadata__"):
                    # Check if any metadata is Ignorable
                    if not any(isinstance(meta, Ignorable) for meta in hint.__metadata__):
                        filtered_params[name] = value
                else:
                    filtered_params[name] = value
            else:
                filtered_params[name] = value
            
        return filtered_params

    def _calculate_signature(self) -> int:
        """Calculate a deterministic hash signature for this task."""
        # Create a tuple of all components to hash
        components = (
            self.name,  # Task name
            self.task_version,  # Version
            self._hash_parameters(self._build_parameter_dict())  # Parameters
        )
        # Use sha256 for secure hashing
        components_str = str(components).encode('utf-8')
        return int(hashlib.sha256(components_str).hexdigest(), 16) % (10**10)

    def _hash_parameters(self, parameters: dict[str, Any]) -> tuple:
        """Convert parameters into a hashable tuple."""
        # Sort by parameter name for deterministic ordering
        return tuple(
            (name, self._hash_value(value))
            for name, value in sorted(parameters.items())
        )

    def _hash_value(self, value: Any) -> Any:  # noqa: ANN401
        """Convert a value into a hashable form."""
        if isinstance(value, str):
            return value
        if isinstance(value, LazyOutput):
            # For nested tasks, use their signature
            return value.owner.signature
        if isinstance(value, (list | tuple)):
            # Convert sequence to tuple of hashed items
            return (type(value).__name__, len(value), tuple(self._hash_value(item) for item in value))
        if isinstance(value, dict):
            # Convert dict to tuple of sorted key-value pairs
            return ('dict', tuple(
                (self._hash_value(key), self._hash_value(val))
                for key, val in sorted(value.items())
            ))
        if is_dataclass(value):
            # For dataclasses, get their type hints and filter out ignored fields
            type_hints = get_type_hints(type(value), include_extras=True)
            fields = {}
            for field_name, field_value in value.__dict__.items():
                if field_name in type_hints:
                    hint = type_hints[field_name]
                    if hasattr(hint, "__metadata__"):
                        if not any(isinstance(meta, Ignorable) for meta in hint.__metadata__):
                            fields[field_name] = self._hash_value(field_value)
                    else:
                        fields[field_name] = self._hash_value(field_value)
                else:
                    fields[field_name] = self._hash_value(field_value)
            return ('dataclass', type(value).__name__, tuple(sorted(fields.items())))
        # For basic types, use their string representation
        return (type(value).__name__, str(value))

    @property
    def signature(self) -> int:
        """Get the task's signature."""
        return self._state.signature

    def __hash__(self) -> int:
        """Return a hash based on the task's name and function."""
        return self._state.signature

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

    @property
    def dependencies(self) -> set['Task']:
        # Find dependencies in args and kwargs
        dependencies = set()
        for arg in self.args:
            if isinstance(arg, LazyOutput):
                dependencies.add(arg.owner)
        for arg in self.kwargs.values():
            if isinstance(arg, LazyOutput):
                dependencies.add(arg.owner)
        return dependencies

    @classmethod
    def create(
        cls, 
        name: str,
        func: Callable, 
        args: tuple = (), 
        kwargs: dict = None, 
        task_version: int = 1
    ) -> 'Task':
        """Create a new task with the given parameters."""
        type_hints = get_type_hints(func, include_extras=True)
        
        kwargs = kwargs or {}
        
        # Get the function's signature
        sig = signature(func)
        
        # Get the current context
        ctx = get_current_context()
        
        # Check for injectable parameters
        for p_name, p_val in sig.parameters.items():
            if p_name in kwargs:
                continue
            
            hint = type_hints.get(p_name)
            
            if not hasattr(hint, "__metadata__"):
                continue
                
            if not any(isinstance(meta, Injectable) for meta in hint.__metadata__):
                continue
            
            # Parameter is injectable
            if hasattr(ctx, p_name):
                # Context has the value, use it
                kwargs[p_name] = getattr(ctx, p_name)
            elif p_val.default is p_val.empty:
                # No default value and not in context
                raise ValueError(
                    f"Required injectable parameter '{p_name}' not found in context"
                )
            # Otherwise, use the default value

        return cls(
            name=name, 
            func=func, 
            args=args, 
            kwargs=kwargs or {}, 
            task_version=task_version
        )

    def resolve(self) -> Any:  # noqa: ANN401
        """Resolve this task by executing it and its dependencies."""
        if self.status is TaskStatus.COMPLETED:
            return self.output.value

        if self.status is TaskStatus.FAILED:
            raise self.exception

        if self.status is TaskStatus.DEP_FAILED:
            raise RuntimeError(f"Task {self.name} failed due to dependency failure")

        try:
            # Check if this is a root task (not being resolved as a dependency)
            is_root = not _task_context.resolving_deps

            # Update status and emit events
            self._state.status = TaskStatus.RUNNING
            if is_root:
                emit(Event(EventType.ROOT_STARTED, self))
            emit(Event(EventType.TASK_STARTED, self))

            # Resolve dependencies first
            resolved_args = []
            resolved_kwargs = {}
            
            with enter_resolution_phase():
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

            # Execute the task function with the task's captured context
            with enter_exec_phase(), self.context:
                result = self.func(*resolved_args, **resolved_kwargs)

            # Update status and output
            self._state.status = TaskStatus.COMPLETED
            self.output.value = result
            self.output._exists = True
            emit(Event(EventType.TASK_FINISHED, self))
            if is_root:
                emit(Event(EventType.ROOT_FINISHED, self))

            return result

        except Exception as e:
            # Update status and emit events
            if self._state.status not in (TaskStatus.DEP_FAILED, TaskStatus.FAILED):
                self._state.status = TaskStatus.FAILED
                self._state.exception = e
                emit(Event(EventType.TASK_FAILED, self))
                if not _task_context.resolving_deps:
                    emit(Event(EventType.ROOT_FAILED, self))

            raise

            raise
