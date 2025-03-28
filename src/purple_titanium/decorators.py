"""Decorators for the pipeline framework."""
import inspect
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, get_type_hints

from .context import get_current_context
from .core import LazyOutput, Task
from .events import Event, EventType
from .events import listen as register_listener
from .types import Injectable

T = TypeVar('T')

def task(task_version: int | None = None) -> Callable[[Callable[..., T]], Callable[..., LazyOutput[T]]]:
    """Decorator to create a task from a function.
    
    This decorator wraps a function to create a task that can be executed as part of a pipeline.
    The decorated function can be called with arguments, and it will return a LazyOutput that
    can be resolved to get the actual result.
    
    Args:
        task_version: Optional version number for the task. When changed, it will create a new
                     signature for the task, useful for invalidating cached results.
    
    Example:
        @task()
        def add(a: int, b: int) -> int:
            return a + b
            
        result = add(1, 2)
        value = result.resolve()  # returns 3
        
        @task(task_version=2)
        def add_v2(a: int, b: int) -> int:
            return a + b  # Same logic, different version
    """
    def decorator(func: Callable[..., T]) -> Callable[..., LazyOutput[T]]:
        """Create a task from a function."""
        
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> LazyOutput[T]:
            """Create a task with the given arguments."""
            # Get the function's type hints
            type_hints = get_type_hints(func)
            
            # Get the function's signature
            sig = inspect.signature(func)
            
            # Get the current context
            ctx = get_current_context()
            
            # Check for injectable parameters
            for name, param in sig.parameters.items():
                if name not in kwargs and isinstance(type_hints.get(name), Injectable):
                    # Parameter is injectable
                    if hasattr(ctx, name):
                        # Context has the value, use it
                        kwargs[name] = getattr(ctx, name)
                    elif param.default is param.empty:
                        # No default value and not in context
                        raise ValueError(
                            f"Required injectable parameter '{name}' not found in context"
                        )
                    # Otherwise, use the default value
            
            # Create the task
            task_name = f"{func.__module__}.{func.__name__}"
            task = Task(task_name, func, args, kwargs, task_version=task_version)
            
            # Find dependencies in args and kwargs
            dependencies = set()
            for arg in args:
                if isinstance(arg, LazyOutput):
                    dependencies.add(arg.owner)
            for arg in kwargs.values():
                if isinstance(arg, LazyOutput):
                    dependencies.add(arg.owner)
            
            # Set dependencies
            task._state.dependencies = dependencies
            
            return task.output
        
        return wrapper
    return decorator

def listen(event_type: EventType) -> Callable[[Callable[[Event], Any]], Callable[[Event], Any]]:
    """Decorator to register an event listener.
    
    This decorator registers a function to be called when an event of the specified type is emitted.
    The decorated function should take an Event object as its argument.
    
    Example:
        @listen(EventType.TASK_STARTED)
        def on_task_started(event: Event):
            print(f"Task {event.task.name} started")
    """
    return register_listener(event_type) 