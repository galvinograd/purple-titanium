"""Tests for context-aware task creation."""


from purple_titanium.context import Context, get_current_context
from purple_titanium.core import Task


def test_task_captures_context() -> None:
    """Test that tasks capture context at creation time."""
    def task_func() -> bool:
        return get_current_context().debug
    
    # Create task in debug context
    with Context(debug=True):
        task = Task("test", task_func)
        assert task.context.debug is True
    
    # Task should maintain its captured context even when executed outside
    assert task.resolve() is True


def test_task_inherits_parent_context() -> None:
    """Test that tasks inherit context from parent tasks."""
    def parent_task() -> int:
        return get_current_context().timeout
    
    def child_task() -> int:
        return get_current_context().timeout
    
    # Create parent task in timeout context
    with Context(timeout=30):
        parent = Task("parent", parent_task)
        # Create child task in extended context
        with Context(timeout=60):
            child = Task("child", child_task)
            child.dependencies.add(parent)
    
    # Child should use its own captured context
    assert child.resolve() == 60
    # Parent should use its own captured context
    assert parent.resolve() == 30


def test_task_context_isolation() -> None:
    """Test that tasks maintain context isolation."""
    def task_func() -> int:
        return get_current_context().value
    
    # Create tasks in different contexts
    with Context(value=1):
        task1 = Task("task1", task_func)
    with Context(value=2):
        task2 = Task("task2", task_func)
    
    # Each task should maintain its own context
    assert task1.resolve() == 1
    assert task2.resolve() == 2


def test_task_context_immutability() -> None:
    """Test that task context is immutable."""
    def task_func() -> int:
        return get_current_context().value
    
    # Create task in initial context
    with Context(value=1):
        task = Task("test", task_func)
    
    # Attempting to modify context should not affect the task
    with Context(value=2):
        assert task.resolve() == 1  # Should still use original context 