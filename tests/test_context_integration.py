"""Integration tests for context system and task creation."""

from concurrent.futures import ThreadPoolExecutor

import pytest

import purple_titanium as pt


def test_task_context_inheritance() -> None:
    """Test that tasks inherit context from their creation point."""
    @pt.task()
    def get_context_value() -> int:
        return pt.get_current_context().value
    
    # Create task in value=1 context
    with pt.Context(value=1):
        task1 = get_context_value()
    
    # Create task in value=2 context
    with pt.Context(value=2):
        task2 = get_context_value()
    
    # Each task should maintain its own context
    assert task1.resolve() == 1
    assert task2.resolve() == 2


def test_task_context_isolation() -> None:
    """Test that tasks maintain context isolation in concurrent execution."""
    @pt.task()
    def get_context_value() -> int:
        return pt.get_current_context().value
    
    def worker(value: int) -> int:
        with pt.Context(value=value):
            task = get_context_value()
            return task.resolve()
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(worker, i) for i in range(3)]
        results = [future.result() for future in futures]
    
    # Each task should have its own context value
    assert results == [0, 1, 2]


def test_task_context_with_dependencies() -> None:
    """Test context inheritance in task dependencies."""
    @pt.task()
    def get_context_value() -> int:
        return pt.get_current_context().value
    
    @pt.task()
    def double(x: int) -> int:
        return x * 2
    
    # Create tasks in value=5 context
    with pt.Context(value=5):
        value_task = get_context_value()
        double_task = double(value_task)
    
    # Both tasks should use the same context
    assert double_task.resolve() == 10


def test_task_context_with_injectable() -> None:
    """Test context injection with Injectable parameters."""
    @pt.task()
    def process_data(data: int, multiplier: pt.Injected[int]) -> int:
        return data * multiplier
    
    # Create task in multiplier=3 context
    with pt.Context(multiplier=3):
        task_obj = process_data(5)
    
    # Task should use injected multiplier from context
    assert task_obj.resolve() == 15


def test_task_context_with_nested_dependencies() -> None:
    """Test context inheritance in nested task dependencies."""
    @pt.task()
    def get_context_value() -> int:
        return pt.get_current_context().value
    
    @pt.task()
    def add(a: int, b: int) -> int:
        return a + b
    
    @pt.task()
    def multiply(x: int, y: int) -> int:
        return x * y
    
    # Create tasks in value=2 context
    with pt.Context(value=2):
        value1 = get_context_value()
        value2 = get_context_value()
        sum_task = add(value1, value2)
        product_task = multiply(sum_task, value1)
    
    # All tasks should use the same context
    assert product_task.resolve() == 8  # (2 + 2) * 2


def test_task_context_with_error_handling() -> None:
    """Test context preservation during error handling."""
    @pt.task()
    def failing_task() -> int:
        raise ValueError("Task failed")
    
    @pt.task()
    def dependent_task(x: int) -> int:
        return x * 2
    
    # Create tasks in value=3 context
    with pt.Context(value=3):
        failing = failing_task()
        dependent = dependent_task(failing)
    
    # Context should be preserved even when task fails
    with pytest.raises(ValueError, match="Task failed"):
        dependent.resolve()


def test_task_context_with_thread_safety() -> None:
    """Test thread safety of task context inheritance."""
    @pt.task()
    def get_context_value() -> int:
        return pt.get_current_context().value
    
    def worker(value: int) -> int:
        with pt.Context(value=value):
            task = get_context_value()
            return task.resolve()
    
    # Create tasks in different threads with different contexts
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(worker, i) for i in range(3)]
        results = [future.result() for future in futures]
    
    # Each task should have its own context value
    assert sorted(results) == [0, 1, 2] 