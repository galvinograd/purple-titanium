import threading
from contextlib import contextmanager
from typing import Iterator

# Thread-local storage for tracking task initialization and resolution
_task_context = threading.local()
_task_context.in_task = False
_task_context.resolving_deps = False

class _TaskContext:
    def __init__(self) -> None:
        self.in_task = False
        self.resolving_deps = False

_task_context = _TaskContext()

@contextmanager
def enter_exec_phase() -> Iterator[None]:
    """Context manager for task execution."""
    old_in_task = getattr(_task_context, 'in_task', False)
    _task_context.in_task = True
    try:
        yield
    finally:
        _task_context.in_task = old_in_task

@contextmanager
def enter_resolution_phase() -> Iterator[None]:
    """Context manager for dependency resolution."""
    old_resolving_deps = getattr(_task_context, 'resolving_deps', False)
    _task_context.resolving_deps = True
    try:
        yield
    finally:
        _task_context.resolving_deps = old_resolving_deps

