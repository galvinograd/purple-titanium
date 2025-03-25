"""Decorators for the pipeline framework."""
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from .core import LazyOutput, Task
from .events import Event, EventType
from .events import listen as register_listener

T = TypeVar('T')

def task() -> Callable[[Callable[..., T]], Callable[..., LazyOutput[T]]]:
    """Decorator to create a task from a function.
    
    This decorator wraps a function to create a task that can be executed as part of a pipeline.
    The decorated function can be called with arguments, and it will return a LazyOutput that
    can be resolved to get the actual result.
    
    Example:
        @task()
        def add(a: int, b: int) -> int:
            return a + b
            
        result = add(1, 2)
        value = result.resolve()  # returns 3
    """
    def decorator(func: Callable[..., T]) -> Callable[..., LazyOutput[T]]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> LazyOutput[T]:
            # Collect dependencies from args and kwargs
            dependencies = set()
            for arg in args:
                if isinstance(arg, LazyOutput):
                    dependencies.add(arg.owner)
            for arg in kwargs.values():
                if isinstance(arg, LazyOutput):
                    dependencies.add(arg.owner)
            
            # Create a task with the function and its arguments
            task = Task(
                name=func.__name__,
                func=func,
                args=args,
                kwargs=kwargs,
                dependencies=dependencies
            )
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