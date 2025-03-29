"""Event system for the pipeline framework."""
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .types import EventType

if TYPE_CHECKING:
    from .task import Task

logger = logging.getLogger(__name__)

@dataclass
class Event:
    """An event that occurred during task execution."""
    type: EventType
    task: 'Task'  # Forward reference to avoid circular import
    data: Any | None = None


class EventEmitter:
    """A class that manages event listeners and emits events."""
    def __init__(self) -> None:
        self._listeners: dict[EventType, set[Callable[[Event], None]]] = {
            event_type: set() for event_type in EventType
        }

    def listen(self, event_type: EventType) -> Callable:
        """Decorator to register an event listener."""
        def decorator(func: Callable[[Event], None]) -> Callable:
            self._listeners[event_type].add(func)
            return func
        return decorator

    def emit(self, event: Event) -> None:
        """Emit an event to all registered listeners."""
        for listener in self._listeners[event.type]:
            try:
                listener(event)
            except Exception:
                # Log internal errors but don't raise them
                logger.exception(f"Error in event listener for {event.type}: {listener.__name__}")
                pass


# Global event emitter instance
emitter = EventEmitter()


def listen(event_type: EventType) -> Callable:
    """Decorator to register an event listener on the global emitter."""
    return emitter.listen(event_type)


def emit(event: Event) -> None:
    """Emit an event using the global emitter."""
    emitter.emit(event) 