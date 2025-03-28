"""Tests for context-aware task creation."""

import purple_titanium as pt


def test_task_captures_context() -> None:
    """Test that tasks capture context at creation time."""
    def task_func() -> bool:
        return pt.get_current_context().debug
    
    # Create task in debug context
    with pt.Context(debug=True):
        task = pt.Task("test", task_func)
        assert task.context.debug is True
    
    # Task should maintain its captured context even when executed outside
    assert task.resolve() is True


def test_task_inherits_parent_context() -> None:
    """Test that tasks inherit context from parent tasks."""
    def parent_task() -> int:
        return pt.get_current_context().timeout
    
    def child_task() -> int:
        return pt.get_current_context().timeout
    
    # Create parent task in timeout context
    with pt.Context(timeout=30):
        parent = pt.Task("parent", parent_task)
        # Create child task in extended context
        with pt.Context(timeout=60):
            child = pt.Task("child", child_task)
            child.dependencies.add(parent)
    
    # Child should use its own captured context
    assert child.resolve() == 60
    # Parent should use its own captured context
    assert parent.resolve() == 30


def test_task_context_isolation() -> None:
    """Test that tasks maintain context isolation."""
    def task_func() -> int:
        return pt.get_current_context().value
    
    # Create tasks in different contexts
    with pt.Context(value=1):
        task1 = pt.Task("task1", task_func)
    with pt.Context(value=2):
        task2 = pt.Task("task2", task_func)
    
    # Each task should maintain its own context
    assert task1.resolve() == 1
    assert task2.resolve() == 2


def test_task_context_immutability() -> None:
    """Test that task context is immutable."""
    def task_func() -> int:
        return pt.get_current_context().value
    
    # Create task in initial context
    with pt.Context(value=1):
        task = pt.Task("test", task_func)
    
    # Attempting to modify context should not affect the task
    with pt.Context(value=2):
        assert task.resolve() == 1  # Should still use original context 