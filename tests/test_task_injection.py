"""Tests for task parameter injection."""

import pytest

from purple_titanium.context import Context
from purple_titanium.decorators import task
from purple_titanium.types import Injectable


def test_task_with_injectable_parameter() -> None:
    """Test that a task can receive an injectable parameter from context."""
    
    @task()
    def my_task(x: Injectable[int]) -> int:
        return x * 2
    
    with Context(x=5):
        task_obj = my_task()
        assert task_obj.resolve() == 10


def test_missing_injectable_parameter() -> None:
    """Test that a missing injectable parameter raises an error."""
    
    @task()
    def my_task(x: Injectable[int]) -> int:
        return x * 2
    
    with pytest.raises(ValueError, match="Required injectable parameter 'x' not found in context"):
        my_task()


def test_mixed_parameters() -> None:
    """Test that a task can have both injectable and regular parameters."""
    
    @task()
    def my_task(x: Injectable[int], y: int) -> int:
        return x * y
    
    with Context(x=5):
        task_obj = my_task(y=3)
        assert task_obj.resolve() == 15


def test_optional_injectable_parameter() -> None:
    """Test that an optional injectable parameter works correctly."""
    
    @task()
    def my_task(x: Injectable[int] = 10) -> int:
        return x * 2
    
    # Test with default value
    task_obj = my_task()
    assert task_obj.resolve() == 20
    
    # Test with context value
    with Context(x=5):
        task_obj = my_task()
        assert task_obj.resolve() == 10 