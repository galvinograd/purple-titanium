"""Decorators for the pipeline framework."""
from collections.abc import Callable
from functools import wraps
from typing import Any, Optional, TypeVar

from .events import Event, EventType
from .events import listen as register_listener
from .lazy_output import LazyOutput
from .task import Task
from .task_factory import TaskFactory
from .types import EventType

T = TypeVar('T')

def task(
    name: Optional[str] = None,
    task_version: Optional[int] = None,
    persist: bool = False,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to create a task from a function.
    
    Args:
        name: Optional name for the task. If not provided, uses the function name.
        version: Optional version number for the task. Used for cache invalidation.
        persist: Whether to persist task outputs. Requires a persistence backend
                to be configured in the context.
    
    Returns:
        A decorated function that creates and resolves a task when called.
    
    Raises:
        RuntimeError: If persist=True but no persistence backend is configured.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> LazyOutput[T]:
            """Create a task with the given arguments."""
            return TaskFactory.create(
                name=f'{func.__module__}.{func.__name__}',
                func=func, 
                args=args, 
                kwargs=kwargs, 
                task_version=task_version,
                persist=persist,
            ).output
        
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