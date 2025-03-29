"""Task factory for creating tasks with processed parameters."""

from collections.abc import Callable
from inspect import signature
from typing import TYPE_CHECKING, get_type_hints

from .annotations import Ignorable, Injectable
from .context import Context, get_current_context
from .task_mode import _task_context
from .task_state import TaskParameters

if TYPE_CHECKING:
    from .task import Task


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
        persist: bool = False,
        context: Context = None
    ) -> 'Task':
        """Create a new task with processed parameters."""
        if getattr(_task_context, 'in_task', False):
            raise RuntimeError("task() cannot be called inside a task")
            
        context = context or get_current_context()
        kwargs = kwargs or {}
        
        parameters = cls._process_parameters(func, args, kwargs, context)
        
        from .task import Task  # Import here to avoid circular import
        return Task(
            name=name,
            func=func,
            parameters=parameters,
            context=context,
            task_version=task_version,
            persist=persist,
        ) 